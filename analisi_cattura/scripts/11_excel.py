"""Excel deliverable: output/capture_delay_cost_analysis.xlsx

Every editable parameter lives in 'Assumptions & Parameters' (named cells); Summary,
Annualisation and the breakdown sheets use live Excel formulas on top of the data values.
"""
# ----------------------------------------------------------------- PARAMETERS
import os

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

from common import (ALL_THRESHOLDS_H, ANALYSIS_START, EXPORT_END, EXTRA_THRESHOLDS_H, OUT_DIR, THRESHOLDS_H,
                    WORK_DIR, connect)

XLSX = os.path.join(OUT_DIR, "capture_delay_cost_analysis.xlsx")
# The committed workbook masks payment / modification identifiers in 'Examples' (no transactional ids in git).
# An unmasked copy for internal use is written to the git-ignored data/work folder.
XLSX_UNMASKED = os.path.join(WORK_DIR, "capture_delay_cost_analysis_unmasked.xlsx")
DEFAULTS = dict(Rate=0.03, CC_Contacts=0.0, CC_Cost=0.0, Uplift1=0.25, Uplift2=0.50, Basis="A")
ACTUAL_LABEL = "Actual Jan–Oct 2025"
FORECAST_LABEL = "Nov–Dec"
REGIONS = ["EU", "UK", "CH"]
EXAMPLES = [  # (payment_id, threshold, label)
    ("SFDLEU00145624#1", 24, "1. Full refund (Mastercard, EUR, IC++)"),
    ("SFDLEU00103070#1", 24, "2. Partial refund (Mastercard, EUR) = partial capture"),
    ("SFDLUK00018872#1", 24, "3. Multiple refunds within S (Visa, GBP)"),
    ("SFDLEU00137929#1", 24, "4. Non-EUR (Klarna, PLN)"),
    ("SFDLEU00234759#1", 24, "5. Credit on refund (Amex commission returned; no interchange credits exist in the data)"),
]
# ----------------------------------------------------------------------------

P = lambda *a: os.path.join(OUT_DIR, *a)
HFILL = PatternFill("solid", fgColor="1F3A5F")
SUBFILL = PatternFill("solid", fgColor="DCE6F1")
INFILL = PatternFill("solid", fgColor="FFF2CC")
TOTFILL = PatternFill("solid", fgColor="F2F2F2")
HFONT = Font(bold=True, color="FFFFFF")
BOLD = Font(bold=True)
TITLE = Font(bold=True, size=14, color="1F3A5F")
NOTE = Font(italic=True, color="595959", size=9)
THIN = Border(bottom=Side(style="thin", color="BFBFBF"))
EUR = '€#,##0;[Red]-€#,##0'
EUR2 = '€#,##0.00;[Red]-€#,##0.00'
PCT = '0.00%'
PCT3 = '0.000%'
INT = '#,##0'
BPS = '0.00" bps"'


def title(ws, text, sub=None):
    ws["A1"] = text
    ws["A1"].font = TITLE
    if sub:
        ws["A2"] = sub
        ws["A2"].font = NOTE


def header(ws, row, col, labels, fill=HFILL, font=HFONT, wrap=True):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=lab)
        c.fill, c.font = fill, font
        c.alignment = Alignment(wrap_text=wrap, vertical="center", horizontal="center")


def widths(ws, w):
    for i, x in enumerate(w, start=1):
        ws.column_dimensions[L(i)].width = x


def put_df(ws, df, row, col=1, fmts=None, hdr=True):
    if hdr:
        header(ws, row, col, list(df.columns))
        row += 1
    for r in df.itertuples(index=False):
        for j, v in enumerate(r):
            if isinstance(v, float) and pd.isna(v):
                v = None
            c = ws.cell(row=row, column=col + j, value=v.item() if hasattr(v, "item") else v)
            if fmts and df.columns[j] in fmts:
                c.number_format = fmts[df.columns[j]]
        row += 1
    return row


def name(wb, nm, ref):
    wb.defined_names[nm] = DefinedName(nm, attr_text=ref)


# =============================================================================================
def build(mask=True):
    con = connect()
    W = lambda n: os.path.join(WORK_DIR, n)
    wb = Workbook()
    wb.remove(wb.active)
    sheets = {n: wb.create_sheet(n) for n in [
        "Summary", "By Market", "By Merchant Account", "By Payment Method", "Fee Breakdown", "Monthly Trend",
        "Annualisation", "Assumptions & Parameters", "Perimeter", "Examples", "Checks & Behaviour"]}

    by_period = pd.read_csv(P("phase7_trend", "by_period.csv"))
    act = by_period[by_period.period == "Actual"].set_index("threshold_h")
    bt = by_period[by_period.period.str.startswith("Forecast")].set_index("threshold_h")
    base = pd.read_csv(P("phase7_trend", "annualisation_base.csv"))
    full = pd.read_csv(P("phase6_opportunity", "net_cost_by_threshold.csv"))
    full = full[full.period == "full_data"].set_index("threshold_h")
    gmv_full = float(full["captured_eur"].iloc[0])

    # ------------------------------------------------------------------ Assumptions & Parameters
    ws = sheets["Assumptions & Parameters"]
    title(ws, "Assumptions & Parameters", "Yellow cells are inputs. All other sheets reference these named cells (live formulas).")
    header(ws, 4, 1, ["Parameter", "Name", "Value", "Unit / note"])
    params = [
        ("Opportunity-cost rate (annual)", "Rate", DEFAULTS["Rate"], "Annual rate applied to the delayed cash-in", PCT),
        ("Customer-care contacts per avoidable refund", "CC_Contacts", DEFAULTS["CC_Contacts"], "Contacts avoided per refund turned into a cancel (default 0, to be filled)", '0.00'),
        ("Cost per customer-care contact (EUR)", "CC_Cost", DEFAULTS["CC_Cost"], "EUR per contact (default 0, to be filled)", EUR2),
        ("Nov–Dec cancellation uplift - sensitivity 1", "Uplift1", DEFAULTS["Uplift1"], "Black Friday / Christmas", PCT),
        ("Nov–Dec cancellation uplift - sensitivity 2", "Uplift2", DEFAULTS["Uplift2"], "Black Friday / Christmas", PCT),
        ("Annualisation basis (A or B)", "Basis", DEFAULTS["Basis"], "A = Jan–Oct actual % of GMV per market (spec). B = SFCC immediate auto-capture run-rate (go-forward)", None),
        ("Go-forward annual in-perimeter GMV (EUR)", "GMV_Forward", round(gmv_full, 2), "Default = 2025 full-year in-perimeter GMV. Replace with 2026/2027 plan", EUR),
    ]
    for i, (lab, nm, val, note, fmt) in enumerate(params):
        r = 5 + i
        ws.cell(row=r, column=1, value=lab)
        ws.cell(row=r, column=2, value=nm)
        c = ws.cell(row=r, column=3, value=val)
        c.fill = INFILL
        if fmt:
            c.number_format = fmt
        ws.cell(row=r, column=4, value=note)
        name(wb, nm, f"'Assumptions & Parameters'!$C${r}")
    dv = DataValidation(type="list", formula1='"A,B"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add("C10")
    r = 13
    info = [("Main thresholds S (hours)", ", ".join(map(str, THRESHOLDS_H))),
            ("Supplementary short-delay thresholds (hours)", ", ".join(map(str, EXTRA_THRESHOLDS_H))),
            ("Export analysed", f"Adyen Interactive payment accounting, {ANALYSIS_START[:10]} – {EXPORT_END[:10]} (CET)"),
            ("Actual period (Summary '10 months')", ACTUAL_LABEL + " (authorisation month)"),
            ("Months estimated", FORECAST_LABEL + " (budget-based; 2025 actual shown as back-test)"),
            ("Tail exclusion", "Payments authorised in the last 3 days of the export are out of perimeter"),
            ("FX", "ECB monthly average reference rates (reference/ecb_fx_monthly.csv), authorisation month, fee currency")]
    header(ws, r, 1, ["Fixed setting", "Value"])
    for i, (a, b) in enumerate(info):
        ws.cell(row=r + 1 + i, column=1, value=a)
        ws.cell(row=r + 1 + i, column=2, value=b)
    r = r + len(info) + 3
    ws.cell(row=r, column=1, value="Assumptions (every hypothesis made in the analysis)").font = BOLD
    assumptions = [
        ("Data", "The 2025 export is used as a dry run; the 1 Jan 2026 validity cut-off is a parameter (ANALYSIS_START) for the production run."),
        ("Data", "Booking Date is US Eastern wall-clock (EST = UTC-5, EDT = UTC-4); converted to UTC for durations and to Europe/Amsterdam for months. The export covers exactly 1 Jan–31 Dec 2025 CET."),
        ("Data", "No Merchant Account / payment Psp Reference columns in the export: account = Merchant Reference prefix (HY+brand = Hybris, SF+brand+region = SFCC, ARIIT = Ariete) x region from currency."),
        ("Data", "Brand codes inferred: D/DL = De'Longhi, K/KW = Kenwood, B/BR = Braun, C/CB = Nutribullet (Capital Brands). To be confirmed."),
        ("Data", "Payment instance = Merchant Reference + n-th Authorised; each modification is attached to the latest Authorised (same reference, same payment method) at or before it."),
        ("Scope", "Markets in scope: EU + EEA + CH + UK, identified by payment currency EUR, GBP, CHF, PLN, CZK, HUF, SEK, DKK, NOK, RON (user: only EU, CH, UK; NO and CH included)."),
        ("Scope", "PayPal excluded (user instruction). Numeric-only order references excluded (user instruction). Card validations and zero-amount authorisations excluded."),
        ("Scope", "Methods without separate capture excluded: iDEAL, Polish online banking, BLIK, MB WAY, Swish, Bancontact (card & mobile), Sofort, Dotpay, SEPA DD."),
        ("Scope", "Capture regime classified per account x month on the median Authorised->first SentForSettle: <1h Immediate, 1–12h Near-immediate (batch, kept in perimeter), >=12h Delayed (excluded)."),
        ("Scope", "Results are reported as one European total (user: the capture logic will be changed for all countries at once); market splits are informative."),
        ("Refunds", "Refund time = first record of the refund modification (SentForSettle-equivalent SentForRefund). Refunds within S are summed and capped at the captured amount."),
        ("Refunds", "Failed refunds (RefundFailed / RefundedReversed) and refunds requested at or after a chargeback are excluded."),
        ("Costs", "Fees on SentForSettle are estimates duplicated on Settled: only Settled fees are used."),
        ("Costs", "Settled fees are avoided pro rata to the share refunded within S (user formula). Fixed per-transaction parts of blended rates (e.g. Klarna EUR 0.10) are not avoided on partial refunds: slight overstatement for partials (2-5% of cases)."),
        ("Costs", "Cost of a cancel = average scheme fee observed on Cancelled records per payment method (Mastercard ~EUR 0.70-1.90, Visa ~EUR 0.01, others 0), applied to full refunds only."),
        ("Costs", "Authorisation processing fee (EUR 0.09 on Received) and per-authorisation services (Revenue Protect, 3DS, scheme auth fees) are paid in both scenarios: excluded."),
        ("Costs", "FX: ECB monthly average of the authorisation month applied to the fee currency (settlement currency for SC columns; EUR for processing fees)."),
        ("Behaviour", "Customers cancel at the same moment under delayed capture; a refund within S becomes a cancel 1:1. Supported by the 2025 natural experiment (Checks & Behaviour sheet)."),
        ("Opportunity cost", "Captured in-perimeter amount x S/24/365 x rate (user formula), i.e. full delay S applied to all captured GMV, including payments already captured with a ~1h batch."),
        ("Annualisation", "Nov–Dec estimate = % of GMV (basis A or B) x budget GMV Nov–Dec per market; sensitivity +25% / +50% on the avoidable part only."),
    ]
    header(ws, r + 1, 1, ["Area", "Assumption"])
    for i, (a, b) in enumerate(assumptions):
        ws.cell(row=r + 2 + i, column=1, value=a)
        c = ws.cell(row=r + 2 + i, column=2, value=b)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    r = r + 3 + len(assumptions)
    ws.cell(row=r, column=1, value="Missing optional inputs").font = BOLD
    missing = ["Account Configuration Report (capture delay per merchant account): not provided - capture delay inferred from data",
               "Merchant account -> brand / market mapping: not provided - inferred from Merchant Reference prefixes",
               "GMV budget Nov–Dec per market: not provided - Annualisation input cells left empty",
               "Dispute transaction details report: not provided - no reason codes",
               "Monthly invoice: provided for Sep 2026 (company DelonghiUS) - export is 2025, so only an order-of-magnitude / unit-price comparison is possible",
               "PayPal fee schedule: not needed (PayPal excluded)"]
    for i, m in enumerate(missing):
        ws.cell(row=r + 1 + i, column=1, value="•")
        ws.cell(row=r + 1 + i, column=2, value=m)
    widths(ws, [46, 120, 16, 80])

    # ------------------------------------------------------------------ Annualisation
    ws = sheets["Annualisation"]
    title(ws, "Annualisation: Nov–Dec estimate and sensitivity",
          "Fill the yellow budget cells (GMV in perimeter, EUR, Nov+Dec). Basis A/B and uplifts are set in 'Assumptions & Parameters'.")
    header(ws, 4, 1, ["Region", "Budget GMV Nov–Dec (EUR, in perimeter)"])
    for i, rg in enumerate(REGIONS):
        ws.cell(row=5 + i, column=1, value=rg)
        ws.cell(row=5 + i, column=2).fill = INFILL
        ws.cell(row=5 + i, column=2).number_format = EUR
    budget_ref = {rg: f"$B${5 + i}" for i, rg in enumerate(REGIONS)}
    cols = ["Threshold S (h)", "Region",
            "Actual GMV Jan–Oct", "Actual avoidable payments", "Actual avoidable cost (fees + chargeback)",
            "Rate A: cost % GMV", "Rate A: avoidable payments per EUR",
            "SFCC-immediate GMV (actual period)", "SFCC avoidable payments", "SFCC avoidable cost",
            "Rate B: cost % GMV", "Rate B: avoidable payments per EUR",
            "Chosen cost rate", "Chosen payments rate", "Budget GMV Nov–Dec",
            "Est. gross avoidable (base)", "Est. gross +uplift 1", "Est. gross +uplift 2",
            "Est. opportunity cost", "Est. net (base)", "Est. net +uplift 1", "Est. net +uplift 2",
            "Back-test: actual GMV Nov–Dec 2025", "Back-test: actual avoidable cost Nov–Dec 2025",
            "Back-test: estimate with actual GMV", "Back-test: estimate error %"]
    HR = 10
    header(ws, HR, 1, cols)
    r = HR + 1
    get = lambda basis, rg, s, col: float(base[(base.basis == basis) & (base.region == rg) & (base.threshold_h == s)][col].sum())
    total_rows = {}
    for s in ALL_THRESHOLDS_H:
        first = r
        for rg in REGIONS:
            A_, B_ = "A: all perimeter, actual period", "B: SFCC immediate, actual period"
            vals = {3: get(A_, rg, s, "captured_eur"), 4: get(A_, rg, s, "avoidable_payments"),
                    5: get(A_, rg, s, "avoidable_fee_cost_eur") + get(A_, rg, s, "chargeback_fees_eur"),
                    8: get(B_, rg, s, "captured_eur"), 9: get(B_, rg, s, "avoidable_payments"),
                    10: get(B_, rg, s, "avoidable_fee_cost_eur") + get(B_, rg, s, "chargeback_fees_eur"),
                    23: get("Back-test: forecast months actual", rg, s, "captured_eur"),
                    24: get("Back-test: forecast months actual", rg, s, "avoidable_fee_cost_eur") + get("Back-test: forecast months actual", rg, s, "chargeback_fees_eur")}
            ws.cell(row=r, column=1, value=s)
            ws.cell(row=r, column=2, value=rg)
            for cidx, v in vals.items():
                ws.cell(row=r, column=cidx, value=round(v, 2))
            b = budget_ref[rg]
            f = {6: f"=IFERROR(E{r}/C{r},0)", 7: f"=IFERROR(D{r}/C{r},0)", 11: f"=IFERROR(J{r}/H{r},0)", 12: f"=IFERROR(I{r}/H{r},0)",
                 13: f'=IF(Basis="B",K{r},F{r})', 14: f'=IF(Basis="B",L{r},G{r})',
                 15: f'=IF(ISBLANK({b}),"",{b})',
                 16: f'=IF(O{r}="","",M{r}*O{r}+N{r}*O{r}*CC_Contacts*CC_Cost)',
                 17: f'=IF(O{r}="","",(M{r}*O{r}+N{r}*O{r}*CC_Contacts*CC_Cost)*(1+Uplift1))',
                 18: f'=IF(O{r}="","",(M{r}*O{r}+N{r}*O{r}*CC_Contacts*CC_Cost)*(1+Uplift2))',
                 19: f'=IF(O{r}="","",O{r}*A{r}/24/365*Rate)',
                 20: f'=IF(O{r}="","",P{r}-S{r})', 21: f'=IF(O{r}="","",Q{r}-S{r})', 22: f'=IF(O{r}="","",R{r}-S{r})',
                 25: f"=M{r}*W{r}", 26: f'=IFERROR(Y{r}/X{r}-1,"")'}
            for cidx, v in f.items():
                ws.cell(row=r, column=cidx, value=v)
            r += 1
        last = r - 1
        ws.cell(row=r, column=1, value=s)
        ws.cell(row=r, column=2, value="TOTAL")
        for cidx in [3, 4, 5, 8, 9, 10, 23, 24, 25]:
            ws.cell(row=r, column=cidx, value=f"=SUM({L(cidx)}{first}:{L(cidx)}{last})")
        for cidx, v in {6: f"=IFERROR(E{r}/C{r},0)", 7: f"=IFERROR(D{r}/C{r},0)", 11: f"=IFERROR(J{r}/H{r},0)",
                        12: f"=IFERROR(I{r}/H{r},0)", 13: f'=IF(Basis="B",K{r},F{r})', 14: f'=IF(Basis="B",L{r},G{r})',
                        26: f'=IFERROR(Y{r}/X{r}-1,"")'}.items():
            ws.cell(row=r, column=cidx, value=v)
        for cidx in range(15, 23):
            col = L(cidx)
            ws.cell(row=r, column=cidx, value=f'=IF(COUNT({col}{first}:{col}{last})=0,"",SUM({col}{first}:{col}{last}))')
        for cidx in range(1, len(cols) + 1):
            ws.cell(row=r, column=cidx).fill = TOTFILL
            ws.cell(row=r, column=cidx).font = BOLD
        total_rows[s] = r
        r += 1
    for row in ws.iter_rows(min_row=HR + 1, max_row=r):
        for c in row:
            j = c.column
            c.number_format = {6: PCT3, 7: '0.000000', 11: PCT3, 12: '0.000000', 13: PCT3, 14: '0.000000', 26: '0.0%',
                               4: INT, 9: INT}.get(j, EUR if j >= 3 else 'General')
    ws.freeze_panes = ws.cell(row=HR + 1, column=3)
    widths(ws, [10, 9] + [15] * (len(cols) - 2))
    ws.row_dimensions[HR].height = 60
    ann_tot = total_rows

    # ------------------------------------------------------------------ Summary
    ws = sheets["Summary"]
    title(ws, "Cost of immediate vs delayed capture – Adyen, EU/EEA + CH + UK (2025 dry run)",
          "Avoidable cost = fees that would not arise if refunds within S were cancels instead. Positive net = delayed capture saves money. "
          "Parameters in 'Assumptions & Parameters'.")
    ws["A4"] = "1. Net avoidable cost by capture delay S (EUR)"
    ws["A4"].font = BOLD
    cols = ["Threshold S (h)",
            f"{ACTUAL_LABEL}: avoidable payments", "Refunded within S (EUR)", "Avoidable fee cost", "Chargeback fees on these payments",
            "Customer-care cost avoided", "Gross avoidable", "In-perimeter GMV", "Opportunity cost", "NET actual 10 months",
            f"{FORECAST_LABEL} estimate: gross", f"{FORECAST_LABEL} estimate: opportunity cost", f"{FORECAST_LABEL} estimate: net",
            "YEAR net (actual + estimate)", "YEAR net, uplift 1", "YEAR net, uplift 2",
            "Back-test 2025 Nov–Dec actual: gross", "Back-test: GMV", "Back-test: opportunity cost", "Back-test: net",
            "Full year 2025 actual net"]
    HR = 5
    header(ws, HR, 1, cols)
    r = HR + 1
    first_main = r
    for s in ALL_THRESHOLDS_H:
        if s == EXTRA_THRESHOLDS_H[0]:
            pass
        a, b_ = act.loc[s], bt.loc[s]
        t = ann_tot[s]
        ann = "Annualisation"
        row = {1: s, 2: int(a.avoidable_payments), 3: round(a.refunded_in_s_eur, 2), 4: round(a.avoidable_fee_cost_eur, 2),
               5: round(a.chargeback_fees_eur, 2), 6: f"=B{r}*CC_Contacts*CC_Cost", 7: f"=D{r}+E{r}+F{r}",
               8: round(a.captured_eur, 2), 9: f"=H{r}*A{r}/24/365*Rate", 10: f"=G{r}-I{r}",
               11: f"={ann}!P{t}", 12: f"={ann}!S{t}", 13: f'=IF(K{r}="","",K{r}-L{r})',
               14: f"=J{r}+N(M{r})", 15: f'=J{r}+IF(K{r}="",0,{ann}!Q{t}-L{r})', 16: f'=J{r}+IF(K{r}="",0,{ann}!R{t}-L{r})',
               17: f"={round(b_.avoidable_fee_cost_eur + b_.chargeback_fees_eur, 2)}+{int(b_.avoidable_payments)}*CC_Contacts*CC_Cost",
               18: round(b_.captured_eur, 2), 19: f"=R{r}*A{r}/24/365*Rate", 20: f"=Q{r}-S{r}", 21: f"=J{r}+T{r}"}
        for cidx, v in row.items():
            c = ws.cell(row=r, column=cidx, value=v)
            c.number_format = INT if cidx in (1, 2) else EUR
        if s in EXTRA_THRESHOLDS_H:
            for cidx in range(1, len(cols) + 1):
                ws.cell(row=r, column=cidx).font = Font(italic=True, color="595959")
        r += 1
    ws.cell(row=r, column=1, value="Italic rows (1–6 h) = supplementary short-delay sensitivity. Nov–Dec estimate stays empty until the budget is filled in 'Annualisation'.").font = NOTE
    ws.freeze_panes = "B6"
    ws.row_dimensions[HR].height = 75

    # go-forward block
    r += 2
    ws.cell(row=r, column=1, value="2. Go-forward view (decision for Stripe): SFCC immediate auto-capture run-rate applied to annual GMV").font = BOLD
    r += 1
    ws.cell(row=r, column=1, value="Run-rate measured on all 2025 SFCC account-months with immediate capture (Aug–Dec, includes peak season). Annual GMV = parameter GMV_Forward.").font = NOTE
    r += 1
    gcols = ["Threshold S (h)", "SFCC GMV (measured)", "SFCC avoidable payments", "SFCC avoidable cost (fees + CB)", "Cost in bps of GMV",
             "Annual gross avoidable", "Annual opportunity cost", "Annual NET", "Net in bps of GMV"]
    header(ws, r, 1, gcols)
    gh = r
    r += 1
    sf = base[base.basis == "SFCC immediate, all data"].groupby("threshold_h")[["captured_eur", "avoidable_payments", "avoidable_fee_cost_eur", "chargeback_fees_eur"]].sum()
    g_first = r
    for s in ALL_THRESHOLDS_H:
        x = sf.loc[s]
        vals = {1: s, 2: round(x.captured_eur, 2), 3: int(x.avoidable_payments), 4: round(x.avoidable_fee_cost_eur + x.chargeback_fees_eur, 2),
                5: f"=D{r}/B{r}*10000", 6: f"=D{r}/B{r}*GMV_Forward+C{r}/B{r}*GMV_Forward*CC_Contacts*CC_Cost",
                7: f"=GMV_Forward*A{r}/24/365*Rate", 8: f"=F{r}-G{r}", 9: f"=H{r}/GMV_Forward*10000"}
        for cidx, v in vals.items():
            c = ws.cell(row=r, column=cidx, value=v)
            c.number_format = {1: INT, 3: INT, 5: BPS, 9: BPS}.get(cidx, EUR)
        r += 1
    g_last = r - 1
    ws.cell(row=r, column=1, value="Best S")
    ws.cell(row=r, column=2, value=f"=INDEX(A{g_first}:A{g_last},MATCH(MAX(H{g_first}:H{g_last}),H{g_first}:H{g_last},0))")
    ws.cell(row=r, column=3, value="hours, net")
    ws.cell(row=r, column=4, value=f"=MAX(H{g_first}:H{g_last})").number_format = EUR
    ws.cell(row=r + 1, column=1, value="Best of main thresholds (12/24/48/72 h)")
    main_rows = [g_first + ALL_THRESHOLDS_H.index(s) for s in THRESHOLDS_H]
    ws.cell(row=r + 1, column=2, value=f"=INDEX(A{main_rows[0]}:A{main_rows[-1]},MATCH(MAX(H{main_rows[0]}:H{main_rows[-1]}),H{main_rows[0]}:H{main_rows[-1]},0))")
    ws.cell(row=r + 1, column=3, value="hours, net")
    ws.cell(row=r + 1, column=4, value=f"=MAX(H{main_rows[0]}:H{main_rows[-1]})").number_format = EUR
    for rr in (r, r + 1):
        for cc in range(1, 5):
            ws.cell(row=rr, column=cc).font = BOLD
    r += 3

    # KPIs
    ws.cell(row=r, column=1, value="3. Key KPIs").font = BOLD
    r += 1
    perim = pd.read_csv(P("phase2_lifecycle", "perimeter_summary.csv"))
    inp = perim[perim.status == "IN PERIMETER"].iloc[0]
    hist = pd.read_csv(P("phase3_refunds", "histogram_auth_to_first_refund.csv"))
    av = pd.read_csv(P("phase3_refunds", "avoidable_refunds_by_threshold.csv")).set_index("threshold_h")
    fb = pd.read_csv(P("phase4_costs", "fee_breakdown_by_threshold.csv")).set_index("threshold_h")
    kpis = [
        ("European authorisations analysed (2025)", int(perim.payments.sum()), INT),
        ("In-perimeter payments (2025)", int(inp.payments), INT),
        ("In-perimeter captured GMV 2025 (EUR)", float(inp.captured_eur), EUR),
        ("In-perimeter payments with any refund", int(inp.payments_with_refund), INT),
        ("Avoidable refunds within 24 h (2025, payments)", int(av.loc[24, "avoidable_payments"]), INT),
        ("…of which refunded within the first hour", int(hist.payments.iloc[0]), INT),
        ("Share of avoidable refunds that are full refunds (24 h)", float(av.loc[24, "full_refunds"] / av.loc[24, "avoidable_payments"]), PCT),
        ("Avoidable fee cost per avoidable refund (24 h, EUR)", float(fb.loc[24, "cost_per_avoidable_refund"]), EUR2),
        ("Refunded within 24 h, % of GMV - Hybris months (batch ~1 h)", None, PCT3),
        ("Refunded within 24 h, % of GMV - SFCC immediate months", None, PCT3),
        ("Opportunity cost of 1 day of delay, bps of GMV (at Rate)", "=1/365*Rate*10000", BPS),
    ]
    plat = pd.read_csv(P("phase7_trend", "by_platform.csv"))
    pf = plat[plat.threshold_h == 24].groupby("platform_group")[["refunded_in_s_eur", "captured_eur"]].sum()
    kpis[8] = (kpis[8][0], float(pf.loc["Hybris", "refunded_in_s_eur"] / pf.loc["Hybris", "captured_eur"]), PCT3)
    sfr = sf.loc[24]
    rf_sf = base[(base.basis == "SFCC immediate, all data") & (base.threshold_h == 24)]
    kpis[9] = (kpis[9][0], float(rf_sf.refunded_in_s_eur.sum() / rf_sf.captured_eur.sum()), PCT3)
    for lab, v, fmt in kpis:
        ws.cell(row=r, column=1, value=lab)
        c = ws.cell(row=r, column=2, value=v)
        c.number_format = fmt
        r += 1
    widths(ws, [30] + [15] * 20)

    # ------------------------------------------------------------------ breakdown sheets
    def breakdown(ws, csv, dims, ttl, extra_per_refund=False):
        df = pd.read_csv(P("phase7_trend", csv))
        df = df[df.threshold_h.isin(THRESHOLDS_H)]
        idx = ["period"] + dims + ["perimeter_payments", "captured_eur"]
        wide = df.pivot_table(index=idx, columns="threshold_h",
                              values=["avoidable_payments", "refunded_in_s_eur", "avoidable_fee_cost_eur"], aggfunc="sum").reset_index()
        title(ws, ttl, "Periods: 'Actual' = Jan–Oct 2025, 'Forecast months (actual data, back-test)' = Nov–Dec 2025. Use the filter. "
              "bps and per-refund columns are live formulas.")
        hdr = ["Period"] + dims + ["In-perimeter payments", "In-perimeter GMV (EUR)"]
        per_s = ["Avoidable payments", "Refunded within S (EUR)", "Avoidable fee cost (EUR)", "% payments", "Cost bps of GMV"]
        if extra_per_refund:
            per_s.append("Cost per avoidable refund (EUR)")
        for s in THRESHOLDS_H:
            hdr += [f"S={s}h: {x}" for x in per_s]
        HR = 4
        header(ws, HR, 1, hdr)
        r = HR + 1
        nd = len(dims) + 3
        for _, row in wide.iterrows():
            vals = [row[("period", "")]] + [row[(d, "")] for d in dims] + [int(row[("perimeter_payments", "")]), round(row[("captured_eur", "")], 2)]
            for j, v in enumerate(vals):
                ws.cell(row=r, column=1 + j, value=v)
            ws.cell(row=r, column=nd).number_format = INT
            ws.cell(row=r, column=nd + 1).number_format = EUR
            c0 = nd + 2
            for s in THRESHOLDS_H:
                n = row.get(("avoidable_payments", s), 0)
                ws.cell(row=r, column=c0, value=int(n) if pd.notna(n) else 0).number_format = INT
                ws.cell(row=r, column=c0 + 1, value=round(float(row.get(("refunded_in_s_eur", s), 0) or 0), 2)).number_format = EUR
                ws.cell(row=r, column=c0 + 2, value=round(float(row.get(("avoidable_fee_cost_eur", s), 0) or 0), 2)).number_format = EUR2
                ws.cell(row=r, column=c0 + 3, value=f"=IFERROR({L(c0)}{r}/{L(nd)}{r},0)").number_format = PCT3
                ws.cell(row=r, column=c0 + 4, value=f"=IFERROR({L(c0 + 2)}{r}/{L(nd + 1)}{r}*10000,0)").number_format = BPS
                if extra_per_refund:
                    ws.cell(row=r, column=c0 + 5, value=f'=IFERROR({L(c0 + 2)}{r}/{L(c0)}{r},"")').number_format = EUR2
                c0 += len(per_s)
            r += 1
        ws.auto_filter.ref = f"A{HR}:{L(len(hdr))}{r - 1}"
        ws.freeze_panes = ws.cell(row=HR + 1, column=nd)
        ws.row_dimensions[HR].height = 60
        widths(ws, [22] + [14] * (len(hdr) - 1))

    breakdown(sheets["By Market"], "by_market.csv", ["region", "country"],
              "By market (country). Country = currency country; SFCC EUR payments without shopper country use the issuer country")
    breakdown(sheets["By Merchant Account"], "by_account.csv", ["account_proxy", "platform", "brand", "region"],
              "By merchant account (reconstructed from Merchant Reference prefix x region)")
    breakdown(sheets["By Payment Method"], "by_method.csv", ["pm"], "By payment method (incl. average cost per avoidable refund)", True)

    # ------------------------------------------------------------------ Fee Breakdown
    ws = sheets["Fee Breakdown"]
    title(ws, "Fee breakdown of the avoidable cost (EUR)", "Sign: positive = cost avoided by delaying capture; negative = credit lost / cost of the cancel that replaces the refund.")
    comp = [("s_commission_eur", "Settled: Commission (blend: Klarna, Amex, TWINT…) x share"),
            ("s_markup_eur", "Settled: Markup (IC++) x share"), ("s_scheme_eur", "Settled: Scheme fees x share"),
            ("s_interchange_eur", "Settled: Interchange x share"), ("r_processing_fee_eur", "Refund: Processing fee (EUR 0.09 per refund)"),
            ("r_commission_fee_eur", "Refund: refund fee (Commission, e.g. Klarna EUR 0.22)"),
            ("r_commission_credit_eur", "Refund: commission returned (Amex) - credit, subtracted"),
            ("r_markup_scheme_eur", "Refund: markup / scheme fees on refund"), ("r_interchange_eur", "Refund: interchange on refund (credits negative)"),
            ("cancel_cost_eur", "Minus: cost of the cancel (scheme fee on Cancelled)"), ("chargeback_fees_eur", "Chargeback fees on these payments (phase 5)")]
    con.execute(f"""CREATE OR REPLACE VIEW cst AS SELECT c.*, CASE WHEN c.auth_month <= DATE '2025-10-01' THEN 'Actual Jan–Oct 2025'
                    ELSE 'Nov–Dec 2025 (back-test)' END AS period FROM read_parquet('{W('costs.parquet')}') c""")
    r = 4
    for per in ["Actual Jan–Oct 2025", "Nov–Dec 2025 (back-test)", "Full year 2025"]:
        flt = "TRUE" if per.startswith("Full") else f"period = '{per}'"
        agg = con.execute(f"SELECT threshold_h, " + ", ".join(f"sum({k}) AS {k}" for k, _ in comp) +
                          f", count(*) AS n FROM cst WHERE {flt} GROUP BY 1 ORDER BY 1").fetchdf().set_index("threshold_h")
        ws.cell(row=r, column=1, value=per).font = BOLD
        header(ws, r + 1, 1, ["Component"] + [f"S = {s} h" for s in ALL_THRESHOLDS_H])
        for i, (k, lab) in enumerate(comp):
            ws.cell(row=r + 2 + i, column=1, value=lab)
            for j, s in enumerate(ALL_THRESHOLDS_H):
                v = float(agg.loc[s, k]) if s in agg.index else 0.0
                ws.cell(row=r + 2 + i, column=2 + j, value=round(v, 2)).number_format = EUR2
        tr = r + 2 + len(comp)
        ws.cell(row=tr, column=1, value="TOTAL avoidable (fees + chargeback)").font = BOLD
        ws.cell(row=tr + 1, column=1, value="Avoidable payments")
        ws.cell(row=tr + 2, column=1, value="Cost per avoidable refund")
        for j, s in enumerate(ALL_THRESHOLDS_H):
            col = L(2 + j)
            c = ws.cell(row=tr, column=2 + j, value=f"=SUM({col}{r + 2}:{col}{tr - 1})")
            c.number_format, c.font, c.fill = EUR2, BOLD, TOTFILL
            ws.cell(row=tr + 1, column=2 + j, value=int(agg.loc[s, "n"]) if s in agg.index else 0).number_format = INT
            ws.cell(row=tr + 2, column=2 + j, value=f"=IFERROR({col}{tr}/{col}{tr + 1},0)").number_format = EUR2
        r = tr + 5
    widths(ws, [62] + [13] * len(ALL_THRESHOLDS_H))

    # ------------------------------------------------------------------ Monthly Trend
    ws = sheets["Monthly Trend"]
    title(ws, "Monthly trend (authorisation month)", "% columns are formulas. Jan–Sep perimeter is mostly Hybris (batch capture ~1h); SFCC immediate auto-capture from Aug–Oct depending on brand/region.")
    mt = pd.read_csv(P("phase7_trend", "monthly_trend.csv"))
    months = sorted(mt.auth_month.unique())
    hdr = ["Month", "In-perimeter payments", "In-perimeter GMV (EUR)"]
    for s in THRESHOLDS_H:
        hdr += [f"S={s}h: avoidable payments", f"S={s}h: % payments", f"S={s}h: refunded (EUR)", f"S={s}h: % GMV", f"S={s}h: avoidable fee cost (EUR)"]
    header(ws, 4, 1, hdr)
    r = 5
    for m in months:
        d = mt[mt.auth_month == m].set_index("threshold_h")
        ws.cell(row=r, column=1, value=m)
        ws.cell(row=r, column=2, value=int(d.perimeter_payments.iloc[0])).number_format = INT
        ws.cell(row=r, column=3, value=round(float(d.captured_eur.iloc[0]), 2)).number_format = EUR
        c0 = 4
        for s in THRESHOLDS_H:
            ws.cell(row=r, column=c0, value=int(d.loc[s, "avoidable_payments"])).number_format = INT
            ws.cell(row=r, column=c0 + 1, value=f"=IFERROR({L(c0)}{r}/B{r},0)").number_format = PCT3
            ws.cell(row=r, column=c0 + 2, value=round(float(d.loc[s, "refunded_in_s_eur"]), 2)).number_format = EUR
            ws.cell(row=r, column=c0 + 3, value=f"=IFERROR({L(c0 + 2)}{r}/C{r},0)").number_format = PCT3
            ws.cell(row=r, column=c0 + 4, value=round(float(d.loc[s, "avoidable_fee_cost_eur"]), 2)).number_format = EUR
            c0 += 5
        r += 1
    ws.cell(row=r, column=1, value="TOTAL").font = BOLD
    for j in range(2, len(hdr) + 1):
        col = L(j)
        if "%" in hdr[j - 1]:
            base_col = "B" if "payments" in hdr[j - 1] else "C"
            ws.cell(row=r, column=j, value=f"=IFERROR({L(j - 1)}{r}/{base_col}{r},0)").number_format = PCT3
        else:
            ws.cell(row=r, column=j, value=f"=SUM({col}5:{col}{r - 1})").number_format = EUR if "EUR" in hdr[j - 1] else INT
        ws.cell(row=r, column=j).fill = TOTFILL
    r += 3
    ws.cell(row=r, column=1, value="Split by platform, S = 24 h").font = BOLD
    mp = pd.read_csv(P("phase7_trend", "monthly_trend_by_platform.csv"))
    mp = mp[mp.threshold_h == 24][["auth_month", "platform_group", "perimeter_payments", "captured_eur", "avoidable_payments",
                                    "pct_payments_refunded_in_s", "pct_gmv_refunded_in_s", "avoidable_fee_cost_eur", "cost_bps_of_gmv"]]
    mp["pct_payments_refunded_in_s"] /= 100
    mp["pct_gmv_refunded_in_s"] /= 100
    put_df(ws, mp, r + 1, fmts={"captured_eur": EUR, "avoidable_fee_cost_eur": EUR2, "pct_payments_refunded_in_s": PCT3,
                                "pct_gmv_refunded_in_s": PCT3, "cost_bps_of_gmv": BPS, "perimeter_payments": INT})
    ws.freeze_panes = "B5"
    ws.row_dimensions[4].height = 45
    widths(ws, [14] + [13] * (len(hdr) - 1))

    # ------------------------------------------------------------------ Perimeter
    ws = sheets["Perimeter"]
    title(ws, "Perimeter: accounts, capture regimes and payment methods")
    ws["A3"] = "Perimeter summary (EUR at ECB monthly average)"
    ws["A3"].font = BOLD
    ps = perim.copy()
    r = put_df(ws, ps, 4, fmts={"payments": INT, "authorised_eur": EUR, "captured_eur": EUR, "payments_with_refund": INT})
    ws.cell(row=r, column=1, value="TOTAL (check: in + out)").font = BOLD
    for j, col in [(2, "B"), (3, "C"), (4, "D"), (5, "E")]:
        ws.cell(row=r, column=j, value=f"=SUM({col}5:{col}{r - 1})").number_format = EUR if j in (3, 4) else INT
    r += 3
    ws.cell(row=r, column=1, value="Capture regime per account and period (median Authorised -> first SentForSettle)").font = BOLD
    per = pd.read_csv(P("phase2_lifecycle", "capture_regime_periods.csv"))
    per["in_perimeter"] = per.capture_class.isin(["Immediate", "Near-immediate (batch)"]).map({True: "Included", False: "Excluded"})
    per["reason"] = per.capture_class.map({"Immediate": "Captures <1h after authorisation: delay would change the outcome",
                                           "Near-immediate (batch)": "Batch capture 1-12h: still captured before the smallest S",
                                           "Delayed / at shipment": "Already captures >=12h after authorisation (manual / at shipment)",
                                           "No captures": "No captures (zero-amount tokenisation)"})
    r = put_df(ws, per, r + 1, fmts={"payments": INT}) + 2
    ws.cell(row=r, column=1, value="Accounts, whole year (classes seen across months)").font = BOLD
    acc = pd.read_csv(P("phase2_lifecycle", "capture_delay_by_account.csv"))
    r = put_df(ws, acc, r + 1, fmts={"payments": INT, "share_lt_1h": PCT, "share_auto": PCT}) + 2
    ws.cell(row=r, column=1, value="Payment methods (European, excl. card validations / numeric references)").font = BOLD
    meth = pd.read_csv(P("phase2_lifecycle", "payment_methods.csv"))
    meth["status"] = meth.apply(lambda x: "Excluded - " + (x.excl_pm_reason if isinstance(x.excl_pm_reason, str) else
                                ("no separate capture: " + (x.note if isinstance(x.note, str) else "captured at authorisation")))
                                if (isinstance(x.excl_pm_reason, str) or not x.separate_capture) else "Included (separate auth / capture)", axis=1)
    meth = meth.drop(columns=["excl_pm_reason", "note"])
    put_df(ws, meth, r + 1, fmts={"payments": INT, "captured_eur": EUR, "cancels": INT, "payments_with_refund": INT})
    widths(ws, [40, 22, 16, 16, 16, 18, 18, 30, 60, 60])

    # ------------------------------------------------------------------ Examples
    ws = sheets["Examples"]
    title(ws, "Worked examples (real payments) – all records and step-by-step calculation",
          "Amounts in payment / settlement currency as in the export; calculation cells are formulas. Times in Europe/Amsterdam.")
    r = 4
    for ex_i, (pid, s, lab) in enumerate(EXAMPLES, start=1):
        mref = pid.split("#")[0]
        recs = con.execute(f"""
        WITH p AS (SELECT * FROM read_parquet('{W('payments.parquet')}') WHERE payment_id = '{pid}'),
        rows AS (
          SELECT e.row_id FROM ev e, p WHERE e.row_id = p.auth_row
          UNION SELECT row_id FROM read_parquet('{W('mods.parquet')}') WHERE payment_id = '{pid}'
          UNION SELECT e.row_id FROM ev e, p WHERE e.mref = p.mref AND e."Record Type" IN ('Received','AuthenticationRequested')
                AND abs(date_diff('second', e.ts_utc, p.auth_ts)) < 600)
        SELECT e."Record Type", strftime(e.ts_local, '%Y-%m-%d %H:%M:%S') AS time_cet,
          round(date_diff('second', p.auth_ts, e.ts_utc) / 3600.0, 2) AS hours_after_auth,
          e."Payment Method", e.ccy AS ccy, e."Authorised (PC)" AS authorised_pc, e."Captured (PC)" AS captured_pc,
          e."Settlement Currency" AS sc, e."Payable (SC)" AS payable_sc, e."Commission (SC)" AS commission_sc,
          e."Markup (SC)" AS markup_sc, e."Scheme Fees (SC)" AS scheme_sc, e."Interchange (SC)" AS interchange_sc,
          e."Processing Fee Currency" AS pf_ccy, e."Processing Fee (FC)" AS processing_fee, e."Modification Psp Reference" AS mod_psp
        FROM ev e, p WHERE e.row_id IN (SELECT row_id FROM rows) ORDER BY e.ts_utc, e.row_id""").fetchdf()
        cst = con.execute(f"SELECT * FROM read_parquet('{W('costs.parquet')}') WHERE payment_id = '{pid}' AND threshold_h = {s}").fetchdf().iloc[0]
        pay = con.execute(f"SELECT * FROM read_parquet('{W('payments.parquet')}') WHERE payment_id = '{pid}'").fetchdf().iloc[0]
        rf = con.execute(f"""SELECT sum(r_commission) c, sum(coalesce(r_markup,0)+coalesce(r_scheme,0)) ms, sum(r_interchange) ic, sum(r_processing_fee) pf, count(*) n
                             FROM read_parquet('{W('refunds_scoped.parquet')}') WHERE payment_id = '{pid}' AND refund_exclusion IS NULL AND refund_delay_h <= {s}""").fetchdf().iloc[0]
        shown = f"example #{ex_i} ({pid[:6]}…, identifiers masked)" if mask else pid
        if mask:
            recs["mod_psp"] = recs["mod_psp"].map(lambda v, m={}: None if (v is None or pd.isna(v)) else m.setdefault(v, f"MOD-{ex_i}-{len(m) + 1}"))
        ws.cell(row=r, column=1, value=f"{lab} – payment {shown} – threshold S = {s} h").font = Font(bold=True, size=12, color="1F3A5F")
        recs = recs.astype(object).where(pd.notna(recs), None)
        for col in ["authorised_pc", "captured_pc", "payable_sc", "commission_sc", "markup_sc", "scheme_sc", "interchange_sc", "processing_fee"]:
            recs[col] = recs[col].map(lambda v: float(v) if v is not None else None)
        r = put_df(ws, recs, r + 1) + 1
        ccy, sc = pay.ccy, (pay.settle_ccy or pay.ccy)
        steps = [
            ("Captured amount (PC, " + ccy + ")", round(float(pay.captured_amount), 2), None, '#,##0.00'),
            (f"Refunded within {s} h (PC), {int(rf.n)} refund(s), capped at captured", round(float(cst.refund_in_s), 2), None, '#,##0.00'),
            ("Share refunded within S = refunded / captured", None, "=B{1}/B{0}", '0.0000'),
            (f"Settled Commission + Markup + Scheme + Interchange ({sc})", round(float((pay.s_commission or 0) + (pay.s_markup or 0) + (pay.s_scheme or 0) + (pay.s_interchange or 0)), 2), None, '#,##0.00'),
            ("Settled fees avoided = settled fees x share", None, "=B{3}*B{2}", '#,##0.0000'),
            (f"Refund records: Commission ({sc}) (+ refund fee / - commission returned)", round(float(rf.c or 0), 2), None, '#,##0.00'),
            (f"Refund records: Markup + Scheme fees ({sc})", round(float(rf.ms or 0), 2), None, '#,##0.00'),
            (f"Refund records: Interchange ({sc}) (negative = credit)", round(float(rf.ic or 0), 2), None, '#,##0.00'),
            (f"ECB monthly rate {sc} per EUR ({str(pay.auth_month)[:7]})", round(float(cst.settle_rate), 6), None, '0.000000'),
            ("Refund records: Processing fee (EUR)", round(float(rf.pf or 0), 2), None, '#,##0.00'),
            ("Minus cost of a cancel (EUR, avg scheme fee on Cancelled for this method; full refunds only)", round(float(cst.cancel_cost_eur), 4), None, '#,##0.0000'),
            ("AVOIDABLE COST (EUR) = (settled avoided + refund SC fees) / rate + processing fee + cancel", None, "=(B{4}+B{5}+B{6}+B{7})/B{8}+B{9}+B{10}", '€#,##0.0000'),
            ("Model value (data/work/costs.parquet)", round(float(cst.avoidable_fee_cost_eur), 4), None, '€#,##0.0000'),
            ("Difference", None, "=B{11}-B{12}", '€#,##0.0000'),
        ]
        rows_idx = [r + i for i in range(len(steps))]
        for i, (labs, val, f, fmt) in enumerate(steps):
            ws.cell(row=r + i, column=1, value=labs)
            c = ws.cell(row=r + i, column=2, value=f.format(*rows_idx) if f else val)
            c.number_format = fmt
            if f:
                c.font = BOLD
        r += len(steps) + 3
    widths(ws, [70, 20, 15, 16, 8, 13, 13, 6, 12, 13, 11, 11, 13, 7, 12, 20])

    # cost per avoidable refund by method (phase 4 request) appended to Examples
    ws.cell(row=r, column=1, value="Average avoidable cost per avoidable refund by payment method (S = 24 h, full year 2025)").font = BOLD
    cm = pd.read_csv(P("phase4_costs", "cost_per_refund_by_method_S24.csv")).drop(columns=["threshold_h"])
    put_df(ws, cm, r + 1, fmts={"refunded_eur": EUR, "avoidable_fee_cost_eur": EUR2, "cost_per_avoidable_refund": EUR2})

    # ------------------------------------------------------------------ Checks & Behaviour
    ws = sheets["Checks & Behaviour"]
    title(ws, "Controls, invoice comparison and behavioural evidence")
    r = 3
    for ttl, f, fm in [
        ("Coherence checks", P("phase8_checks", "coherence_checks.csv"), {}),
        ("Invoice comparison (Sep 2026 invoice, company DelonghiUS, all regions) vs export Sep 2025 (all regions)", P("phase8_checks", "invoice_reconciliation.csv"),
         {"InvoiceAmount": '#,##0', "invoice_eur": EUR, "report_eur_comparison_month": EUR, "delta_eur": EUR}),
        ("Observed unit costs in the export (EU/CH/UK) - to compare with invoice unit prices below", P("phase8_checks", "observed_unit_costs.csv"), {}),
        ("Invoice unit prices (selected lines)", P("phase8_checks", "invoice_unit_prices_selected.csv"), {}),
        ("Behaviour by capture regime: % of payments cancelled / refunded within S (evidence that refunds become cancels)", P("phase5_secondary", "behaviour_by_capture_regime.csv"), {"payments": INT}),
        ("Disputes on avoidable payments", P("phase5_secondary", "disputes_on_avoidable_payments.csv"), {}),
        ("Cost of a cancel by payment method (scheme fee on Cancelled records)", P("phase4_costs", "cancel_cost_by_method.csv"), {}),
        ("Histogram data: Authorised -> first refund (hours)", P("phase3_refunds", "histogram_auth_to_first_refund.csv"), {"cum_share_of_refunded_payments": PCT}),
    ]:
        ws.cell(row=r, column=1, value=ttl).font = BOLD
        r = put_df(ws, pd.read_csv(f), r + 1, fmts=fm) + 2
    widths(ws, [60, 40, 18, 22, 60, 18, 14, 14, 14])

    out = XLSX if mask else XLSX_UNMASKED
    wb.save(out)
    print("Wrote", out)


if __name__ == "__main__":
    build(mask=True)
    build(mask=False)
