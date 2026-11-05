"""Phase 2 - Payment lifecycle reconstruction and perimeter.

Builds (git-ignored, in data/work/):
  mods.parquet      one row per relevant record, attached to a payment instance (payment_id)
  payments.parquet  one row per authorisation (= payment instance) with lifecycle aggregates + perimeter flags
  refunds.parquet   one row per refund request (SentForRefund / Modification Psp Reference)
Writes aggregate outputs to output/phase2_lifecycle/.

Payment key: the export has no payment Psp Reference, so a payment instance is
Merchant Reference + the n-th Authorised record. Each modification is attached (ASOF join)
to the latest Authorised of the same Merchant Reference and Payment Method at or before it.
"""
# ----------------------------------------------------------------- PARAMETERS
import os

from common import (ANALYSIS_START, EXPORT_END, IMMEDIATE_MAX_H, OUT_DIR, REPO, TAIL_DAYS, WORK_DIR, connect, q)

PHASE_DIR = os.path.join(OUT_DIR, "phase2_lifecycle")
FX_FILE = os.path.join(REPO, "reference", "ecb_fx_monthly.csv")
# Capture classification per account x month (median Authorised -> first SentForSettle):
#   < IMMEDIATE_MAX_H (1h) Immediate | < NEAR_IMMEDIATE_MAX_H Near-immediate (batch job) | else Delayed / at shipment
NEAR_IMMEDIATE_MAX_H = 12.0          # = smallest threshold tested: capture still happens before S
AT_SHIPMENT_MULTI_SHARE = 0.10       # share of payments with >1 capture to label 'At shipment'
IN_SCOPE_CLASSES = ["Immediate", "Near-immediate (batch)"]
# Reference groups excluded from the perimeter (user: numeric-only order references; card validations)
EXCLUDED_REF_GROUPS = {"NUM/NUM": "Numeric-only order reference (user instruction)",
                       "NUMERIC": "Numeric-only order reference (user instruction)",
                       "CARDVAL": "Zero/low-value card validation, not an order"}
# Payment methods excluded explicitly by the user
EXCLUDED_METHODS = {"paypal": "PayPal excluded by user (authorises/captures instantly; fees invoiced by PayPal)"}
# Payment methods that support separate authorisation and capture (Adyen). Everything else
# (bank transfers / instant payments / Bancontact) is captured at authorisation by design.
SEPARATE_CAPTURE_METHODS = [
    "visa", "mc", "amex", "cartebancaire", "maestro", "electron", "discover", "cup", "diners", "jcb",
    "visadankort", "klarna", "klarna_account", "klarna_paynow", "clearpay", "twint",
]
SEPARATE_CAPTURE_SUFFIXES = ["_applepay", "_googlepay", "_mobilepay", "_vipps"]
NO_SEPARATE_CAPTURE_NOTE = {
    "ideal": "iDEAL - bank redirect, captured at authorisation",
    "onlineBanking_PL": "Polish online banking (pay-by-link) - captured at authorisation",
    "blik": "BLIK - instant payment, captured at authorisation",
    "mbway": "MB WAY - captured at authorisation",
    "swish": "Swish - instant payment, captured at authorisation",
    "bcmc": "Bancontact card - Adyen does not support separate capture",
    "bcmc_mobile": "Bancontact mobile (Payconiq) - no separate capture",
    "directEbanking": "Sofort - bank transfer, captured at authorisation",
    "dotpay": "Dotpay - bank transfer, captured at authorisation",
    "sepadirectdebit": "SEPA Direct Debit - no authorisation hold",
}
MOD_TYPES = ["SentForSettle", "Settled", "SettledExternally", "CaptureFailed", "SettledReversed",
             "SentForRefund", "Refunded", "RefundedExternally", "RefundFailed", "RefundedReversed", "RefundNotCleared",
             "Cancelled", "Expired", "Chargeback", "ChargebackReversed", "SecondChargeback"]
# ----------------------------------------------------------------------------


def sep_capture_sql(col='"Payment Method"'):
    lst = ", ".join(f"'{m}'" for m in SEPARATE_CAPTURE_METHODS)
    suf = " OR ".join(f"{col} LIKE '%{s}'" for s in SEPARATE_CAPTURE_SUFFIXES)
    return f"({col} IN ({lst}) OR {suf})"


def main():
    os.makedirs(PHASE_DIR, exist_ok=True)
    con = connect()
    W = lambda n: os.path.join(WORK_DIR, n)
    mod_list = ", ".join(f"'{m}'" for m in MOD_TYPES)

    # ---------------------------------------------------------------- authorisations = payment instances
    con.execute(f"""
    CREATE OR REPLACE TABLE auths AS
    SELECT mref, "Payment Method" AS pm,
           mref || '#' || row_number() OVER (PARTITION BY mref ORDER BY ts_utc, row_id) AS payment_id,
           row_id AS auth_row, ts_utc AS auth_ts, ts_local AS auth_local, "Authorised (PC)" AS auth_amount,
           ccy, region, country, platform, brand, ref_group, account_proxy,
           "Payment Method Variant" AS variant, "Shopper Country" AS shopper_country, "Issuer Country" AS issuer_country
    FROM ev2 WHERE "Record Type" = 'Authorised' AND region <> 'Non-European'
    """)

    # ---------------------------------------------------------------- modifications -> payment (ASOF)
    con.execute(f"""
    CREATE OR REPLACE TABLE mods_raw AS
    SELECT row_id, mref, "Payment Method" AS pm, "Record Type" AS rt, ts_utc, ts_local,
           "Modification Psp Reference" AS mod_psp, "Modification Merchant Reference" AS mod_mref,
           "Authorised (PC)" AS authorised_pc, "Captured (PC)" AS captured_pc, "Payable (SC)" AS payable_sc,
           "Settlement Currency" AS settle_ccy, coalesce("Commission (SC)",0) AS commission,
           coalesce("Markup (SC)",0) AS markup, coalesce("Scheme Fees (SC)",0) AS scheme_fees,
           coalesce("Interchange (SC)",0) AS interchange, coalesce("Processing Fee (FC)",0) AS processing_fee,
           "Processing Fee Currency" AS pf_ccy, "Main Amount" AS main_amount, ccy
    FROM ev WHERE "Record Type" IN ({mod_list}) AND region <> 'Non-European'
    """)
    # Same-second ordering: a modification can share the timestamp of its authorisation -> allow equality.
    con.execute("""
    CREATE OR REPLACE TABLE mods AS
    WITH m1 AS (
      SELECT m.*, a.payment_id AS pid_same_pm
      FROM mods_raw m ASOF LEFT JOIN auths a ON m.mref = a.mref AND m.pm = a.pm AND m.ts_utc >= a.auth_ts
    ), m2 AS (
      SELECT m1.*, a.payment_id AS pid_any
      FROM m1 ASOF LEFT JOIN auths a ON m1.mref = a.mref AND m1.ts_utc >= a.auth_ts
    )
    SELECT * EXCLUDE (pid_same_pm, pid_any), coalesce(pid_same_pm, pid_any) AS payment_id,
           CASE WHEN pid_same_pm IS NOT NULL THEN 'same_method' WHEN pid_any IS NOT NULL THEN 'any_method'
                ELSE 'orphan' END AS link_type
    FROM m2
    """)
    con.execute(f"COPY mods TO '{W('mods.parquet')}' (FORMAT PARQUET)")

    # ---------------------------------------------------------------- refunds (one row per refund request)
    con.execute("""
    CREATE OR REPLACE TABLE refunds AS
    WITH r AS (
      SELECT mod_psp, any_value(payment_id) AS payment_id,
        min(ts_utc) FILTER (WHERE rt = 'SentForRefund') AS sfr_ts,
        min(ts_utc) FILTER (WHERE rt IN ('Refunded','RefundedExternally')) AS refunded_ts,
        -abs(sum(captured_pc) FILTER (WHERE rt = 'SentForRefund')) * -1 AS sfr_amount,
        abs(sum(captured_pc) FILTER (WHERE rt IN ('Refunded','RefundedExternally'))) AS refunded_amount,
        count(*) FILTER (WHERE rt = 'RefundFailed') AS n_failed,
        count(*) FILTER (WHERE rt = 'RefundedReversed') AS n_reversed,
        count(*) FILTER (WHERE rt = 'RefundNotCleared') AS n_not_cleared,
        -- refund-side fees (all records of this refund modification: SentForRefund, Refunded, RefundFailed, RefundedReversed)
        sum(commission) AS r_commission, sum(markup) AS r_markup, sum(scheme_fees) AS r_scheme,
        sum(interchange) AS r_interchange, sum(processing_fee) AS r_processing_fee,
        any_value(settle_ccy) FILTER (WHERE settle_ccy IS NOT NULL) AS r_settle_ccy,
        any_value(pf_ccy) FILTER (WHERE pf_ccy IS NOT NULL) AS r_pf_ccy,
        any_value(link_type) AS link_type
      FROM mods WHERE rt IN ('SentForRefund','Refunded','RefundedExternally','RefundFailed','RefundedReversed','RefundNotCleared')
      GROUP BY mod_psp
    )
    SELECT *, coalesce(sfr_ts, refunded_ts) AS refund_request_ts,
           coalesce(abs(sfr_amount), refunded_amount) AS refund_amount,
           (n_failed > 0 OR n_reversed > 0) AS refund_failed
    FROM r
    """)

    # ---------------------------------------------------------------- payment aggregates
    con.execute("""
    CREATE OR REPLACE TABLE pay_mods AS
    SELECT payment_id,
      count(*) FILTER (WHERE rt='SentForSettle') AS n_capture,
      min(ts_utc) FILTER (WHERE rt='SentForSettle') AS first_capture_ts,
      max(ts_utc) FILTER (WHERE rt='SentForSettle') AS last_capture_ts,
      sum(captured_pc) FILTER (WHERE rt='SentForSettle') AS captured_amount,
      bool_or(mod_mref = '<auto>') FILTER (WHERE rt='SentForSettle') AS auto_capture,
      count(*) FILTER (WHERE rt='Settled') AS n_settled,
      count(*) FILTER (WHERE rt='SettledExternally') AS n_settled_ext,
      -sum(captured_pc) FILTER (WHERE rt='Settled') AS settled_amount_pc,
      sum(commission) FILTER (WHERE rt='Settled') AS s_commission,
      sum(markup) FILTER (WHERE rt='Settled') AS s_markup,
      sum(scheme_fees) FILTER (WHERE rt='Settled') AS s_scheme,
      sum(interchange) FILTER (WHERE rt='Settled') AS s_interchange,
      sum(processing_fee) FILTER (WHERE rt='Settled') AS s_processing_fee,
      any_value(settle_ccy) FILTER (WHERE rt='Settled') AS settle_ccy,
      -- settled reversals / capture failures
      count(*) FILTER (WHERE rt='CaptureFailed') AS n_capture_failed,
      count(*) FILTER (WHERE rt='SettledReversed') AS n_settled_reversed,
      sum(commission+markup+scheme_fees+interchange) FILTER (WHERE rt IN ('SettledReversed','CaptureFailed')) AS reversal_fees,
      -- cancel / expiry
      min(ts_utc) FILTER (WHERE rt='Cancelled') AS cancel_ts,
      count(*) FILTER (WHERE rt='Cancelled') AS n_cancel,
      sum(scheme_fees+commission+markup+interchange) FILTER (WHERE rt='Cancelled') AS cancel_fees,
      count(*) FILTER (WHERE rt='Expired') AS n_expired,
      -- disputes
      count(*) FILTER (WHERE rt='Chargeback') AS n_chargeback,
      min(ts_utc) FILTER (WHERE rt='Chargeback') AS first_chargeback_ts,
      -sum(payable_sc) FILTER (WHERE rt='Chargeback') AS chargeback_amount_sc,
      sum(commission+markup+scheme_fees+interchange) FILTER (WHERE rt IN ('Chargeback','SecondChargeback','ChargebackReversed')) AS chargeback_fees,
      count(*) FILTER (WHERE rt='ChargebackReversed') AS n_chargeback_reversed,
      count(*) FILTER (WHERE rt='SecondChargeback') AS n_second_chargeback
    FROM mods WHERE payment_id IS NOT NULL GROUP BY 1
    """)
    con.execute("""
    CREATE OR REPLACE TABLE pay_ref AS
    SELECT payment_id, count(*) AS n_refund, count(*) FILTER (WHERE NOT refund_failed) AS n_refund_ok,
           min(refund_request_ts) AS first_refund_ts,
           sum(refund_amount) FILTER (WHERE NOT refund_failed) AS refund_amount_ok,
           count(*) FILTER (WHERE refund_failed) AS n_refund_failed
    FROM refunds WHERE payment_id IS NOT NULL GROUP BY 1
    """)

    sep = sep_capture_sql("a.pm")
    excl_ref = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in EXCLUDED_REF_GROUPS.items())
    excl_pm = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in EXCLUDED_METHODS.items())
    con.execute(f"""
    CREATE OR REPLACE TABLE payments_tmp AS
    SELECT a.*, m.* EXCLUDE (payment_id), r.* EXCLUDE (payment_id),
      date_diff('second', a.auth_ts, m.first_capture_ts) / 3600.0 AS capture_delay_h,
      date_diff('second', a.auth_ts, r.first_refund_ts) / 3600.0 AS first_refund_delay_h,
      date_trunc('month', a.auth_local)::DATE AS auth_month,
      {sep} AS separate_capture,
      CASE a.ref_group {excl_ref} END AS excl_ref_reason,
      CASE a.pm {excl_pm} END AS excl_pm_reason
    FROM auths a LEFT JOIN pay_mods m USING (payment_id) LEFT JOIN pay_ref r USING (payment_id)
    """)

    # ---------------------------------------------------------------- FX (ECB monthly average, auth month)
    con.execute(f"""CREATE OR REPLACE TABLE fx AS
        SELECT ccy AS fx_ccy, month::DATE AS fx_month, rate_per_eur FROM read_csv('{FX_FILE}', header=true)""")

    # ---------------------------------------------------------------- capture regime per account x month
    con.execute(f"""
    CREATE OR REPLACE TABLE regime AS
    SELECT account_proxy, auth_month, count(*) AS payments,
      median(capture_delay_h) AS median_h, quantile_cont(capture_delay_h, 0.9) AS p90_h,
      avg((capture_delay_h < {IMMEDIATE_MAX_H})::INT) AS share_lt_1h, avg(auto_capture::INT) AS share_auto,
      avg((n_capture > 1)::INT) FILTER (WHERE n_capture > 0) AS share_multi_capture,
      CASE WHEN median(capture_delay_h) IS NULL THEN 'No captures'
           WHEN median(capture_delay_h) < {IMMEDIATE_MAX_H} THEN 'Immediate'
           WHEN median(capture_delay_h) < {NEAR_IMMEDIATE_MAX_H} THEN 'Near-immediate (batch)'
           WHEN avg((n_capture > 1)::INT) FILTER (WHERE n_capture > 0) >= {AT_SHIPMENT_MULTI_SHARE} THEN 'At shipment'
           ELSE 'Delayed / at shipment' END AS capture_class
    FROM payments_tmp
    WHERE separate_capture AND excl_ref_reason IS NULL AND excl_pm_reason IS NULL
    GROUP BY ALL
    """)

    tail_cut = f"TIMESTAMP '{EXPORT_END}' - INTERVAL {TAIL_DAYS} DAY"
    con.execute(f"""
    CREATE OR REPLACE TABLE payments AS
    SELECT p.* EXCLUDE (country),
      CASE WHEN p.country = '??' THEN coalesce(p.issuer_country, 'EU-unknown') ELSE p.country END AS country,
      g.capture_class,
      fx.rate_per_eur,
      p.auth_amount / fx.rate_per_eur AS auth_eur,
      coalesce(p.captured_amount, 0) / fx.rate_per_eur AS captured_eur,
      CASE
        WHEN p.auth_local < TIMESTAMP '{ANALYSIS_START}' THEN 'Before analysis start'
        WHEN p.excl_ref_reason IS NOT NULL THEN p.excl_ref_reason
        WHEN p.auth_amount <= 0 THEN 'Zero-amount authorisation (tokenisation / validation)'
        WHEN p.excl_pm_reason IS NOT NULL THEN p.excl_pm_reason
        WHEN NOT p.separate_capture THEN 'Payment method without separate capture'
        WHEN g.capture_class NOT IN ({", ".join(repr(c) for c in IN_SCOPE_CLASSES)}) THEN 'Account-month already captures with delay / at shipment'
        WHEN p.auth_local > {tail_cut} THEN 'Authorised in last {TAIL_DAYS} days of export (refund tail incomplete)'
        ELSE NULL END AS exclusion_reason
    FROM payments_tmp p
    LEFT JOIN regime g USING (account_proxy, auth_month)
    LEFT JOIN fx ON fx.fx_ccy = p.ccy AND fx.fx_month = p.auth_month
    """)
    con.execute("ALTER TABLE payments ADD COLUMN in_perimeter BOOLEAN")
    con.execute("UPDATE payments SET in_perimeter = exclusion_reason IS NULL")
    con.execute(f"COPY payments TO '{W('payments.parquet')}' (FORMAT PARQUET)")
    con.execute(f"COPY refunds TO '{W('refunds.parquet')}' (FORMAT PARQUET)")

    # ---------------------------------------------------------------- outputs
    acc = q(con, """
    SELECT account_proxy, any_value(platform) platform, any_value(brand) brand, any_value(region) region,
      count(*) AS payments,
      round(median(capture_delay_h), 2) AS median_h, round(quantile_cont(capture_delay_h, 0.9), 2) AS p90_h,
      round(avg((capture_delay_h < 1)::INT), 3) AS share_lt_1h, round(avg(auto_capture::INT), 3) AS share_auto,
      string_agg(DISTINCT capture_class, ' / ') AS classes_seen
    FROM payments WHERE separate_capture AND excl_ref_reason IS NULL AND excl_pm_reason IS NULL AND auth_amount > 0
    GROUP BY account_proxy ORDER BY payments DESC
    """, 60)
    acc.to_csv(os.path.join(PHASE_DIR, "capture_delay_by_account.csv"), index=False)
    reg = con.execute("SELECT * FROM regime ORDER BY account_proxy, auth_month").fetchdf()
    reg.to_csv(os.path.join(PHASE_DIR, "capture_regime_by_account_month.csv"), index=False)
    # regime periods (consecutive months with same class)
    per = q(con, """
    WITH r AS (SELECT *, row_number() OVER (PARTITION BY account_proxy ORDER BY auth_month)
                       - row_number() OVER (PARTITION BY account_proxy, capture_class ORDER BY auth_month) AS grp FROM regime)
    SELECT account_proxy, capture_class, min(auth_month) AS from_month, max(auth_month) AS to_month,
           sum(payments) AS payments, round(median(median_h), 2) AS median_of_monthly_median_h
    FROM r GROUP BY account_proxy, capture_class, grp ORDER BY account_proxy, from_month
    """, 80)
    per.to_csv(os.path.join(PHASE_DIR, "capture_regime_periods.csv"), index=False)

    meth = q(con, """
    SELECT pm AS payment_method, separate_capture, count(*) AS payments,
      round(median(capture_delay_h), 3) AS median_capture_h, sum(n_cancel) AS cancels, sum((n_refund > 0)::INT) AS payments_with_refund,
      round(sum(captured_eur)) AS captured_eur, any_value(excl_pm_reason) AS excl_pm_reason
    FROM payments WHERE excl_ref_reason IS NULL AND auth_amount > 0 GROUP BY ALL ORDER BY payments DESC
    """, 60)
    meth["note"] = meth["payment_method"].map(NO_SEPARATE_CAPTURE_NOTE)
    meth.to_csv(os.path.join(PHASE_DIR, "payment_methods.csv"), index=False)

    perim = q(con, """
    SELECT coalesce(exclusion_reason, 'IN PERIMETER') AS status, count(*) AS payments,
      round(sum(auth_eur)) AS authorised_eur, round(sum(captured_eur)) AS captured_eur,
      sum((n_refund > 0)::INT) AS payments_with_refund
    FROM payments GROUP BY 1 ORDER BY (status = 'IN PERIMETER') DESC, payments DESC
    """)
    perim.to_csv(os.path.join(PHASE_DIR, "perimeter_summary.csv"), index=False)
    q(con, "select link_type, count(*) n from mods group by 1")
    q(con, """select count(*) n, count(*) filter (where settle_ccy is not null and settle_ccy <> ccy) settle_ccy_differs,
              count(*) filter (where rate_per_eur is null) missing_fx from payments""")


if __name__ == "__main__":
    main()
