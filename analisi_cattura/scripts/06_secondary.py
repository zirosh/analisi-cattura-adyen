"""Phase 5 - Secondary effects.

1. Disputes / chargebacks on payments with a refund within S (count, amounts, fees).
   No Dispute transaction details report was provided -> no reason codes.
2. Customer-care cost: parameter (contacts per avoidable refund x cost per contact), default 0,
   applied in the Excel model (Assumptions sheet).
3. Behavioural control ("natural experiment"): share of payments cancelled / refunded within S
   by capture regime (Hybris batch ~1h, SFCC delayed months, SFCC immediate months).
"""
# ----------------------------------------------------------------- PARAMETERS
import os

from common import OUT_DIR, THRESHOLDS_H, WORK_DIR, connect, q

PHASE_DIR = os.path.join(OUT_DIR, "phase5_secondary")
CC_CONTACTS_PER_REFUND = 0.0      # default, edited in Excel
CC_COST_PER_CONTACT_EUR = 0.0     # default, edited in Excel
# ----------------------------------------------------------------------------


def main():
    os.makedirs(PHASE_DIR, exist_ok=True)
    con = connect()
    W = lambda n: os.path.join(WORK_DIR, n)
    con.execute(f"CREATE VIEW p AS SELECT * FROM read_parquet('{W('payments.parquet')}')")
    con.execute(f"CREATE VIEW c AS SELECT * FROM read_parquet('{W('costs.parquet')}')")
    con.execute(f"CREATE VIEW rs AS SELECT * FROM read_parquet('{W('refunds_scoped.parquet')}')")

    cb = q(con, """
    SELECT threshold_h, count(*) AS avoidable_payments, sum((n_chargeback > 0)::INT) AS with_chargeback,
           sum(n_chargeback) AS chargebacks, round(sum(chargeback_amount_eur), 2) AS chargeback_amount_eur,
           round(sum(chargeback_fees_eur), 2) AS chargeback_fees_eur
    FROM c GROUP BY 1 ORDER BY 1""")
    cb.to_csv(os.path.join(PHASE_DIR, "disputes_on_avoidable_payments.csv"), index=False)
    ctx = q(con, """
    SELECT in_perimeter, count(*) FILTER (WHERE n_chargeback > 0) AS payments_with_chargeback,
           count(*) FILTER (WHERE n_chargeback > 0 AND n_refund > 0) AS with_chargeback_and_refund,
           round(sum(chargeback_fees / rate_per_eur), 2) AS chargeback_fees_eur_approx
    FROM p GROUP BY 1""")
    ctx.to_csv(os.path.join(PHASE_DIR, "disputes_context.csv"), index=False)

    # ---- behavioural control by capture regime (same accounts, payments with separate capture)
    parts = []
    for s in THRESHOLDS_H:
        parts.append(f"""
        SELECT {s} AS threshold_h, regime, count(*) AS payments,
          round(100.0 * avg((cancel_ts IS NOT NULL AND date_diff('second', auth_ts, cancel_ts) <= {s} * 3600)::INT), 3) AS pct_cancelled_within_s,
          round(100.0 * avg((rf.first_h IS NOT NULL AND rf.first_h <= {s})::INT), 3) AS pct_refunded_within_s
        FROM pp LEFT JOIN rf USING (payment_id) GROUP BY ALL""")
    con.execute("""
    CREATE TABLE pp AS SELECT *,
      CASE WHEN platform = 'Hybris' THEN 'Hybris (batch capture ~1h)'
           WHEN platform LIKE 'SFCC%' AND capture_class LIKE 'Delayed%' THEN 'SFCC delayed capture (median ~24-47h)'
           WHEN platform LIKE 'SFCC%' THEN 'SFCC immediate auto-capture'
           WHEN platform = 'Ariete' THEN 'Ariete immediate auto-capture' END AS regime
    FROM p WHERE separate_capture AND excl_ref_reason IS NULL AND excl_pm_reason IS NULL AND auth_amount > 0
      AND exclusion_reason IS DISTINCT FROM 'Authorised in last 3 days of export (refund tail incomplete)'
      AND platform IN ('Hybris', 'SFCC', 'Ariete')""")
    con.execute("""CREATE TABLE rf AS SELECT payment_id, min(refund_delay_h) AS first_h FROM rs
                   WHERE refund_exclusion IS NULL GROUP BY 1""")
    ne = q(con, " UNION ALL ".join(parts) + " ORDER BY 2, 1", 40)
    ne["pct_cancel_or_refund_within_s"] = ne["pct_cancelled_within_s"] + ne["pct_refunded_within_s"]
    ne.to_csv(os.path.join(PHASE_DIR, "behaviour_by_capture_regime.csv"), index=False)
    print(ne.to_string())


if __name__ == "__main__":
    main()
