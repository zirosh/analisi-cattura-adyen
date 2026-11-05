"""Phase 8 - Controls.

1. Invoice reconciliation. If the invoice period is covered by the export, report fees are compared
   with invoice categories for that month. Otherwise (2025 export vs 2026 invoice) a rate benchmark is
   produced: invoice unit prices vs effective unit costs observed in the data, plus an order-of-magnitude
   comparison with the same calendar month of the export.
2. Coherence checks (perimeter totals, refunded <= captured, duplicates, FX coverage, orphans).
Outputs in output/phase8_checks/.
"""
# ----------------------------------------------------------------- PARAMETERS
import csv
import glob
import os

import pandas as pd

from common import DATA_DIR, OUT_DIR, REPO, WORK_DIR, connect, q

PHASE_DIR = os.path.join(OUT_DIR, "phase8_checks")
INVOICE_GLOB = os.path.join(DATA_DIR, "invoices", "*.csv")
FX_FILE = os.path.join(REPO, "reference", "ecb_fx_monthly.csv")
# Invoice category -> how it maps to the accounting report
CATEGORY_MAP = {
    "Processing Fees": "Processing Fee (FC) on Received + SentForRefund (+RefundFailed reversals)",
    "Payment Method Fees": "Settled Commission/Markup/Scheme/Interchange + scheme fees on Authorised/Refused/Retried/Cancelled/Expired - commission returned on refunds (Amex)",
    "Mobile Payment Fees": "Settled Commission on MobilePay/Vipps (included in Payment Method Fees in the report)",
    "Refund Fees": "Positive Commission on SentForRefund/Refunded (refund fees)",
    "Chargeback Service": "Fees on Chargeback/SecondChargeback/ChargebackReversed",
    "Management Service": "NOT in accounting report (0.10% on externally settled volume)",
    "Management & Reconciliation Service": "NOT in accounting report",
    "Revenue Protect Service": "NOT in accounting report (risk fee per transaction)",
    "Authentication Engine": "NOT in accounting report (3DS fee per authentication)",
    "Non-Transactional Scheme Fees": "NOT in accounting report",
}
# ----------------------------------------------------------------------------


def parse_invoice(path):
    rows = list(csv.reader(open(path, encoding="utf-8-sig")))
    header = {}
    out = {"IS": [], "CD": [], "MB": [], "IH": None}
    for r in rows:
        if not r:
            continue
        tag = r[0]
        if tag.endswith("C") and tag not in ("CD", "ACD", "MB"):
            header[tag[:-1]] = r[1:]
            continue
        if tag in ("IH", "IS", "CD", "MB"):
            rec = dict(zip(header.get(tag, []), r[1:]))
            if tag == "IH":
                out["IH"] = rec
            else:
                out[tag].append(rec)
    return out


def num(x):
    try:
        return float(str(x).replace(",", ""))
    except ValueError:
        return None


def invoice_section(con):
    paths = sorted(glob.glob(INVOICE_GLOB))
    if not paths:
        print("No invoice found")
        return
    inv = parse_invoice(paths[0])
    ih = inv["IH"]
    period = ih["InvoicePeriod"]                       # e.g. 2026-09
    subtot = [r for r in inv["IS"] if r["Description"].startswith("Invoice Subtotal")][0]
    usd_per_eur = num(subtot["InvoiceAmount"]) / num(subtot["InvoiceLocalAmount"])
    cats = pd.DataFrame(inv["IS"])
    cats["InvoiceAmount"] = cats["InvoiceAmount"].map(num)
    cats = cats[cats["Description"].isin(CATEGORY_MAP)]
    cats["invoice_eur"] = cats["InvoiceAmount"] / usd_per_eur
    cats["mapping_to_accounting_report"] = cats["Description"].map(CATEGORY_MAP)

    data_months = con.execute("SELECT DISTINCT strftime(ts_local, '%Y-%m') FROM ev").fetchdf().iloc[:, 0].tolist()
    if period in data_months:
        comp_month, mode = period, "Full reconciliation (same month)"
    else:
        comp_month = str(int(period[:4]) - 1) + period[4:]
        mode = f"Invoice period {period} not in export: order-of-magnitude comparison with {comp_month}"
    con.execute(f"CREATE OR REPLACE TABLE fx AS SELECT ccy fx_ccy, month::DATE fx_month, rate_per_eur FROM read_csv('{FX_FILE}')")
    d = con.execute(f"""
    WITH e AS (SELECT ev.*, coalesce(fx1.rate_per_eur, 1) AS r_sc, coalesce(fx2.rate_per_eur, 1) AS r_pf FROM ev
               LEFT JOIN fx fx1 ON fx1.fx_ccy = coalesce("Settlement Currency", ccy) AND fx1.fx_month = date_trunc('month', ts_local)::DATE
               LEFT JOIN fx fx2 ON fx2.fx_ccy = "Processing Fee Currency" AND fx2.fx_month = date_trunc('month', ts_local)::DATE
               WHERE strftime(ts_local, '%Y-%m') = '{comp_month}')
    SELECT
      sum(coalesce("Processing Fee (FC)", 0) / r_pf) AS "Processing Fees",
      sum((coalesce("Commission (SC)",0)+coalesce("Markup (SC)",0)+coalesce("Scheme Fees (SC)",0)+coalesce("Interchange (SC)",0)) / r_sc)
        FILTER (WHERE "Record Type" IN ('Settled','Authorised','Refused','Retried','Cancelled','Expired'))
      + coalesce(sum("Commission (SC)" / r_sc) FILTER (WHERE "Record Type" IN ('SentForRefund','Refunded') AND "Commission (SC)" < 0), 0) AS "Payment Method Fees",
      sum("Commission (SC)" / r_sc) FILTER (WHERE "Record Type" IN ('SentForRefund','Refunded','RefundFailed','RefundedReversed') AND "Commission (SC)" > 0) AS "Refund Fees",
      sum((coalesce("Commission (SC)",0)+coalesce("Markup (SC)",0)+coalesce("Scheme Fees (SC)",0)+coalesce("Interchange (SC)",0)) / r_sc)
        FILTER (WHERE "Record Type" IN ('Chargeback','SecondChargeback','ChargebackReversed')) AS "Chargeback Service"
    FROM e""").fetchdf().T.reset_index()
    d.columns = ["Description", "report_eur_comparison_month"]
    rec = cats[["Description", "InvoiceAmount", "invoice_eur", "mapping_to_accounting_report"]].merge(d, how="left", on="Description")
    rec["delta_eur"] = rec["report_eur_comparison_month"] - rec["invoice_eur"]
    rec.insert(0, "mode", mode)
    rec.to_csv(os.path.join(PHASE_DIR, "invoice_reconciliation.csv"), index=False)
    print(rec.round(0).to_string())

    # ---- unit-rate benchmark: invoice prices vs effective costs observed in the export (EU/CH/UK, full export)
    cd = pd.DataFrame(inv["CD"])
    pick = lambda pat: cd[cd["Description"].str.contains(pat, regex=True)][["Description", "Count", "TurnoverCurrency", "TurnoverAmount", "Rate", "Currency", "Amount"]]
    bench_inv = pd.concat([pick(r"^Transaction fee"), pick(r"^Commission Markup EUR|^Commission Markup \(cartebancaire\)"),
                           pick(r"Commission Blend \(klarna_(?:DE|IT|GB|CH|NL|FR|AT|SE)\)"), pick(r"Commission Blend \(amex\)"),
                           pick(r"^Commission Blend Refunds \((?:klarna|ideal|bcmc|mbway|swish)"),
                           pick(r"Authorisation Scheme fee Cancelled"), pick(r"Chargebacks$")])
    bench_inv.to_csv(os.path.join(PHASE_DIR, "invoice_unit_prices_selected.csv"), index=False)
    obs = q(con, """
    WITH e AS (SELECT * FROM ev WHERE region <> 'Non-European')
    SELECT 'Processing fee per Received (auth) record, EUR' AS metric, round(avg("Processing Fee (FC)"), 4) AS observed
      FROM e WHERE "Record Type"='Received' AND "Processing Fee (FC)" IS NOT NULL
    UNION ALL SELECT 'Processing fee per SentForRefund, EUR', round(avg("Processing Fee (FC)"), 4) FROM e WHERE "Record Type"='SentForRefund' AND "Processing Fee (FC)" IS NOT NULL
    UNION ALL SELECT 'Card markup % of settled amount (visa/mc, EUR)', round(100*sum("Markup (SC)")/sum(-"Captured (PC)"), 4) FROM e WHERE "Record Type"='Settled' AND "Payment Method" IN ('visa','mc') AND ccy='EUR'
    UNION ALL SELECT 'Card interchange % (visa/mc, EUR)', round(100*sum("Interchange (SC)")/sum(-"Captured (PC)"), 4) FROM e WHERE "Record Type"='Settled' AND "Payment Method" IN ('visa','mc') AND ccy='EUR'
    UNION ALL SELECT 'Card scheme fee % (visa/mc, EUR)', round(100*sum("Scheme Fees (SC)")/sum(-"Captured (PC)"), 4) FROM e WHERE "Record Type"='Settled' AND "Payment Method" IN ('visa','mc') AND ccy='EUR'
    UNION ALL SELECT 'Klarna commission % of settled (klarna, EUR)', round(100*sum("Commission (SC)")/sum(-"Captured (PC)"), 4) FROM e WHERE "Record Type"='Settled' AND "Payment Method"='klarna' AND ccy='EUR'
    UNION ALL SELECT 'Amex commission % of settled (EUR)', round(100*sum("Commission (SC)")/sum(-"Captured (PC)"), 4) FROM e WHERE "Record Type"='Settled' AND "Payment Method"='amex' AND ccy='EUR'
    UNION ALL SELECT 'Refund fee per Klarna refund (Refunded commission, EUR)', round(avg("Commission (SC)"), 4) FROM e WHERE "Record Type"='Refunded' AND "Payment Method" LIKE 'klarna%' AND ccy='EUR'
    UNION ALL SELECT 'Scheme fee per Cancelled (mc, EUR)', round(avg(coalesce("Scheme Fees (SC)",0)), 4) FROM e WHERE "Record Type"='Cancelled' AND "Payment Method"='mc' AND ccy='EUR'
    UNION ALL SELECT 'Scheme fee per Cancelled (visa, EUR)', round(avg(coalesce("Scheme Fees (SC)",0)), 4) FROM e WHERE "Record Type"='Cancelled' AND "Payment Method"='visa' AND ccy='EUR'
    UNION ALL SELECT 'Interchange returned on card refunds (count of negative IC records)', count(*) FROM e WHERE "Record Type" IN ('Refunded','SentForRefund') AND "Interchange (SC)" < 0
    """, 30)
    obs.to_csv(os.path.join(PHASE_DIR, "observed_unit_costs.csv"), index=False)


def coherence(con):
    W = lambda n: os.path.join(WORK_DIR, n)
    con.execute(f"CREATE OR REPLACE VIEW p AS SELECT * FROM read_parquet('{W('payments.parquet')}')")
    con.execute(f"CREATE OR REPLACE VIEW rs AS SELECT * FROM read_parquet('{W('refunds_scoped.parquet')}')")
    con.execute(f"CREATE OR REPLACE VIEW av AS SELECT * FROM read_parquet('{W('avoidable.parquet')}')")
    con.execute(f"CREATE OR REPLACE VIEW mods AS SELECT * FROM read_parquet('{W('mods.parquet')}')")
    checks = []
    tot = con.execute("SELECT count(*) FROM ev WHERE \"Record Type\"='Authorised' AND region <> 'Non-European'").fetchone()[0]
    inn, out = con.execute("SELECT count(*) FILTER (WHERE in_perimeter), count(*) FILTER (WHERE NOT in_perimeter) FROM p").fetchone()
    checks.append(("Perimeter: in + out = total European authorisations", f"{inn:,} + {out:,} = {inn+out:,} vs {tot:,}", inn + out == tot))
    g = con.execute("SELECT round(sum(captured_eur) FILTER (WHERE in_perimeter) + sum(captured_eur) FILTER (WHERE NOT in_perimeter) - sum(captured_eur), 6) FROM p").fetchone()[0]
    checks.append(("Perimeter: GMV in + out = total GMV (EUR)", f"difference {g}", abs(g) < 0.01))
    n = con.execute("SELECT count(*) FROM av WHERE refund_in_s > captured_amount + 0.005").fetchone()[0]
    checks.append(("No refunded-within-S amount greater than captured", f"{n} violations (refunds capped at captured)", n == 0))
    n2 = con.execute("SELECT count(*) FROM av WHERE refund_in_s_raw > captured_amount + 0.005").fetchone()[0]
    checks.append(("Raw refunds within S exceeding captured (before cap)", f"{n2} payments", True))
    n3 = con.execute("SELECT count(*) FROM p WHERE coalesce(refund_amount_ok,0) > coalesce(captured_amount,0) + 0.005 AND in_perimeter").fetchone()[0]
    checks.append(("In perimeter: total valid refunds > captured (any time)", f"{n3} payments (multi-auth references / partial data)", True))
    d1 = con.execute("SELECT count(*) - count(DISTINCT payment_id) FROM p").fetchone()[0]
    checks.append(("No duplicate payment key (Merchant Reference + auth sequence)", f"{d1} duplicates", d1 == 0))
    d2 = con.execute("SELECT count(*) - count(DISTINCT mod_psp) FROM rs").fetchone()[0]
    checks.append(("No duplicate refund Modification Psp Reference", f"{d2} duplicates", d2 == 0))
    d3 = con.execute("SELECT count(*) FROM (SELECT mod_psp FROM mods WHERE rt='Settled' GROUP BY 1 HAVING count(*) > 1)").fetchone()[0]
    checks.append(("No capture settled twice (Settled per Modification Psp Reference)", f"{d3} duplicates", d3 == 0))
    d4 = con.execute("SELECT count(*) FROM (SELECT row_id FROM mods GROUP BY 1 HAVING count(*) > 1)").fetchone()[0]
    checks.append(("Each record attached to at most one payment", f"{d4} duplicates", d4 == 0))
    o = con.execute("SELECT count(*) FILTER (WHERE link_type='orphan'), count(*) FROM mods").fetchone()
    checks.append(("Orphan modifications (payment authorised before export start)", f"{o[0]:,} of {o[1]:,} records", True))
    fxm = con.execute("SELECT count(*) FROM p WHERE rate_per_eur IS NULL").fetchone()[0]
    checks.append(("FX coverage (ECB monthly rate found for every payment)", f"{fxm} missing", fxm == 0))
    sfs, st = con.execute("""SELECT sum(markup+scheme_fees+interchange) FILTER (WHERE rt='SentForSettle'),
                                    sum(markup+scheme_fees+interchange) FILTER (WHERE rt='Settled') FROM mods""").fetchone()
    checks.append(("Fees on SentForSettle duplicate Settled (only Settled used)", f"SFS {sfs:,.0f} vs Settled {st:,.0f} (local ccy sum)", True))
    df = pd.DataFrame(checks, columns=["check", "result", "pass"])
    df.to_csv(os.path.join(PHASE_DIR, "coherence_checks.csv"), index=False)
    print(df.to_string())


def main():
    os.makedirs(PHASE_DIR, exist_ok=True)
    con = connect()
    invoice_section(con)
    coherence(con)


if __name__ == "__main__":
    main()
