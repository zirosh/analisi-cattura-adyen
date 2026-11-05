# Cost of immediate vs delayed capture (Adyen) – EU/EEA, CH, UK

**Status: dry run on the 2025 export.** The pipeline is parametrised and will be re-run on the
1 Jan – 31 Oct 2026 export (set `ANALYSIS_START` / `EXPORT_END` in `scripts/common.py`).

## Question
How much does it cost to capture immediately instead of with a delay S (12 h, 24 h, 48 h, 72 h; plus 1–6 h as
supplementary sensitivity)? With delayed capture, an order cancelled within S becomes a cancel of the
authorisation instead of a refund: the ad-valorem fees on the settled amount never arise and no refund fee is charged.
On the other side, cash arrives S hours later (opportunity cost).

## Method (one script per phase in `scripts/`)
1. **Profiling** – Adyen *Interactive payment accounting* export (3.84 M records), converted to Parquet, analysed with DuckDB.
   Booking Date is US Eastern (EST/EDT) → converted to UTC / CET. There are no Merchant Account or payment Psp Reference
   columns, so the account is rebuilt from the Merchant Reference prefix (Hybris `HY*`, SFCC `SF*`, Ariete), and payments are
   keyed on Merchant Reference + authorisation sequence.
2. **Lifecycle & perimeter** – 677 k European authorisations rebuilt (capture, settlement, refunds, cancels, chargebacks).
   The capture regime is classified **per account × month** because it changed in 2025. SFCC captured with a delay (median 24–47 h)
   until Aug–Oct, then switched to Adyen immediate auto-capture. Hybris captured with a ~1 h batch job.
   **Perimeter:** immediate or near-immediate account-months × methods with separate capture (cards, wallets, Klarna, Clearpay, TWINT).
   **Excluded:** PayPal and numeric-only references (user instructions), and methods without separate capture
   (iDEAL, BLIK, Polish online banking, MB WAY, Swish, Bancontact, …).
   **Result:** 378 k payments and €82.1 M captured are in perimeter.
3. **Avoidable refunds** – valid refund requests within S of authorisation, capped at the captured amount.
   Failed refunds and refunds requested after a chargeback are excluded.
4. **Cost attribution** – the avoidable cost has three parts:
   - Settled fees (Commission, Markup, Scheme Fees, Interchange) × share refunded;
   - plus the fees on the refund records (processing fee €0.09, Klarna/iDEAL refund fee €0.22, Amex commission returned as a credit);
   - minus the cost of the cancel that replaces the refund (scheme fee observed on Cancelled records, mainly Mastercard).

   Amounts are converted to EUR at the ECB monthly average rate, using the fee currency.
5. **Secondary effects** – chargebacks on the payments with an avoidable refund. Customer-care cost is a parameter (default 0).
   A behavioural check compares regimes (natural experiment).
6. **Opportunity cost** – GMV × S/24/365 × rate (3% default). Net = avoidable cost − opportunity cost.
7. **Trend & annualisation** – monthly trend. The Nov–Dec estimate is % of GMV × budget, with +25% / +50% sensitivity.
   Two bases are available: A (Jan–Oct actual, as specified) and B (SFCC immediate run-rate).
8. **Controls** – coherence checks (all pass) and a comparison with the Sep 2026 invoice.

## Key results (2025)
| | 1 h | 12 h | 24 h | 48 h | 72 h |
|---|---|---|---|---|---|
| Avoidable refunds (payments, full year) | 1,058 | 1,110 | 1,214 | 1,313 | 1,473 |
| Refunded within S, % of GMV | 0.41% | 0.42% | 0.44% | 0.45% | 0.47% |
| Avoidable fees, 2025 as observed | €5.9 k | €6.1 k | €6.3 k | €6.5 k | €6.7 k |
| Opportunity cost at 3% | €0.3 k | €3.4 k | €6.7 k | €13.5 k | €20.2 k |
| **Net, 2025 as observed** | **+€5.7 k** | **+€2.7 k** | **−€0.4 k** | **−€7.0 k** | **−€13.5 k** |
| **Net, go-forward (SFCC immediate run-rate on €82 M)** | **+€11.5 k** | **+€8.5 k** | **+€5.6 k** | **−€1.0 k** | **−€7.7 k** |
| Net, actual Jan–Oct only (mostly Hybris) | +€0.1 k | −€1.6 k | −€3.4 k | −€7.2 k | −€10.9 k |

- **Almost all avoidable refunds happen in the first hour.**
  - 1,058 of the 1,214 avoidable refunds within 24 h are requested in the first hour (median ~9 minutes); 97% are full refunds.
  - They come almost entirely from SFCC auto-capture accounts: orders voided right after checkout.
  - Hybris did not have them: its ~1 h batch capture already turned them into cancels.
  - Avoided fees therefore saturate after ~1 h, while the opportunity cost grows linearly with S.
- **The amounts are small.** The avoidable cost is about **1.5 bps of GMV** under SFCC immediate capture.
  - The average cost per avoidable refund is ~€5.
  - By method: Klarna €11–15 (blended commission), Visa/MC €2.5–3, Apple Pay MC €0.6, Amex €0.2 (Adyen returns the commission).
  - For comparison, one day of delay costs 0.82 bps of GMV at 3%.
- **Behaviour is consistent with the hypothesis.** Under SFCC delayed capture, 1.2% of payments were cancelled within 24 h
  and almost none were refunded. Under immediate capture, 0.9% were cancelled and 0.7% refunded within 24 h.
  Delayed capture turns quick refunds into cancels.
- **No chargebacks** on the payments with an avoidable refund. No interchange credits on refunds exist in the data.
- **The Nov–Dec back-test misses badly.** The SFCC run-rate up to October underestimates the actual Nov–Dec 2025 cost by ~75%.
  Peak-season uplift is far larger than +50%, but the impact in euros stays small.
- **One-off event:** a spike at 48–50 h is a single batch refund of 79 Kenwood EU orders (15 Nov 2025).

## Recommendation
Do **not** configure a 24–72 h delay. A long delay costs more in delayed cash than it saves in fees.

Configure a **short delay of about 1–2 h**, or better, **capture when the order is accepted** (after the fraud check and order
creation, before the warehouse export). This keeps ~95% of the avoidable saving, about €10–12 k/year on 2025 volumes,
at negligible opportunity cost. **12 h is the upper bound** that still pays off.

On Stripe:
- Use `capture_method=manual` with capture on order acceptance, or an automatic capture job after N hours.
- Remember the card authorisation validity window.
- **Check the Stripe contract on refunds.** On standard pricing Stripe does not return processing fees on refunds,
  which would raise the cost per avoidable refund and strengthen the case for a short delay.

## Limits
- **2025 is a migration year.** Most Jan–Sep volume is Hybris with batch capture. The go-forward view relies on SFCC
  immediate months (Aug–Dec), which are dominated by peak season. Re-run on the 2026 export.
- **Missing columns.** Without Merchant Account and Psp Reference, accounts and payment keys are reconstructed.
  Recurring references (subscriptions) are handled with an as-of join. 11 k modifications belong to payments
  authorised before 2025 and are ignored.
- **Customer behaviour** could change with delayed capture (e.g. later cancellations, "pending" authorisations on statements).
  The natural experiment suggests the volume of cancellations is stable.
- **Partial refunds:** settled fees are avoided pro rata, so the fixed per-transaction parts of blended rates are slightly overstated.
- **Cost of a cancel** uses the observed average per method. Per-authorisation fees (auth fee €0.09, RevenueProtect, 3DS,
  scheme authorisation fees) are paid in both scenarios and are excluded.
- **FX:** ECB monthly averages of the authorisation month, not the actual Adyen conversion rate.
- **Invoice:** the provided invoice is for Sep 2026 and the export is 2025, so only an order-of-magnitude comparison is possible.
  - Payment Method Fees: €167 k invoiced vs €162 k in the Sep 2025 report.
  - Processing fees: €6.1 k vs €5.5 k (unit price €0.093–0.098 in 2026 vs €0.09 in 2025).
  - Full reconciliation will be possible with the 2026 export.
- **Missing optional inputs:** Account Configuration Report, merchant account mapping, Nov–Dec budget (input cells left empty),
  Dispute report.
- **PayPal** is excluded, so this is not a full-wallet view.

## Files
- `capture_delay_cost_analysis.xlsx`: Summary, breakdowns, Fee Breakdown, Monthly Trend, Annualisation (budget inputs),
  Assumptions & Parameters (live formulas), Perimeter, Examples (5 worked cases), Checks & Behaviour.
- `chart_auth_to_refund_histogram.png`, `chart_monthly_trend.png`, `chart_cost_by_threshold.png`.
- `phase*/`: aggregated CSV outputs of each phase. `reference/ecb_fx_monthly.csv`: FX rates used.
- Re-run: `00_fx.py` → `01_ingest.py` → `02_profile.py` … `11_excel.py` (transactional data stays in `data/`, git-ignored).
