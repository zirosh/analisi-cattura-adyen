"""Phase 3 - Avoidable refunds.

For each threshold S: payments in perimeter with at least one (valid) refund request within S
hours of Authorised; amount refunded within S (capped at captured amount).
Excluded refunds: failed (RefundFailed / RefundedReversed) and chargeback-linked (requested at or
after the first chargeback of the payment).

Writes data/work/avoidable.parquet (payment x threshold) and data/work/refunds_scoped.parquet,
aggregates in output/phase3_refunds/.
"""
# ----------------------------------------------------------------- PARAMETERS
import os

from common import ALL_THRESHOLDS_H as THRESHOLDS_H, OUT_DIR, WORK_DIR, connect, q

PHASE_DIR = os.path.join(OUT_DIR, "phase3_refunds")
HIST_MAX_H = 168            # histogram range 0-7 days, hourly bins
FULL_REFUND_TOL = 0.999     # share >= tol -> treated as full refund (= cancel)
# ----------------------------------------------------------------------------


def main():
    os.makedirs(PHASE_DIR, exist_ok=True)
    con = connect()
    W = lambda n: os.path.join(WORK_DIR, n)
    con.execute(f"CREATE VIEW p AS SELECT * FROM read_parquet('{W('payments.parquet')}')")
    con.execute(f"CREATE VIEW r AS SELECT * FROM read_parquet('{W('refunds.parquet')}')")

    con.execute("""
    CREATE OR REPLACE TABLE rs AS
    SELECT r.*, p.auth_ts, p.captured_amount, p.first_chargeback_ts, p.in_perimeter,
      date_diff('second', p.auth_ts, r.refund_request_ts) / 3600.0 AS refund_delay_h,
      CASE WHEN r.refund_failed THEN 'Failed / reversed refund'
           WHEN p.first_chargeback_ts IS NOT NULL AND r.refund_request_ts >= p.first_chargeback_ts THEN 'Chargeback-linked refund'
           ELSE NULL END AS refund_exclusion
    FROM r JOIN p USING (payment_id)
    """)
    con.execute(f"COPY rs TO '{W('refunds_scoped.parquet')}' (FORMAT PARQUET)")

    q(con, """SELECT in_perimeter, coalesce(refund_exclusion,'valid') AS status, count(*) AS refunds,
                     round(sum(refund_amount)) AS amount_pc FROM rs GROUP BY ALL ORDER BY 1 DESC, 3 DESC""")

    parts = []
    for s in THRESHOLDS_H:
        parts.append(f"""
        SELECT {s} AS threshold_h, payment_id,
          count(*) AS n_refunds_in_s,
          sum(refund_amount) AS refund_in_s_raw,
          least(sum(refund_amount), any_value(captured_amount)) AS refund_in_s,
          min(refund_delay_h) AS first_refund_h
        FROM rs WHERE in_perimeter AND refund_exclusion IS NULL AND refund_delay_h <= {s}
        GROUP BY payment_id""")
    con.execute("CREATE OR REPLACE TABLE av AS " + " UNION ALL ".join(parts))
    con.execute(f"""
    CREATE OR REPLACE TABLE avoidable AS
    SELECT a.*, p.captured_amount, p.ccy, p.rate_per_eur,
      CASE WHEN p.captured_amount > 0 THEN a.refund_in_s / p.captured_amount ELSE 0 END AS share_refunded,
      (CASE WHEN p.captured_amount > 0 THEN a.refund_in_s / p.captured_amount ELSE 0 END) >= {FULL_REFUND_TOL} AS is_full,
      a.refund_in_s / p.rate_per_eur AS refund_in_s_eur
    FROM av a JOIN p USING (payment_id)
    """)
    con.execute(f"COPY avoidable TO '{W('avoidable.parquet')}' (FORMAT PARQUET)")

    summ = q(con, """
    WITH tot AS (SELECT count(*) AS n_perim, sum(captured_eur) AS gmv FROM p WHERE in_perimeter)
    SELECT threshold_h, count(*) AS avoidable_payments,
      round(100.0 * count(*) / any_value(n_perim), 3) AS pct_of_payments,
      sum(is_full::INT) AS full_refunds, sum((NOT is_full)::INT) AS partial_refunds,
      sum((n_refunds_in_s > 1)::INT) AS multi_refund_payments,
      round(sum(refund_in_s_eur)) AS refunded_in_s_eur,
      round(100.0 * sum(refund_in_s_eur) / any_value(gmv), 3) AS pct_of_gmv,
      sum((refund_in_s_raw > captured_amount + 0.005)::INT) AS capped_cases
    FROM avoidable, tot GROUP BY threshold_h ORDER BY 1
    """)
    summ.to_csv(os.path.join(PHASE_DIR, "avoidable_refunds_by_threshold.csv"), index=False)

    # Histogram Authorised -> first valid refund request, 0-7 days, hourly
    hist = con.execute(f"""
    WITH f AS (SELECT payment_id, min(refund_delay_h) h FROM rs
               WHERE in_perimeter AND refund_exclusion IS NULL GROUP BY 1)
    SELECT floor(h)::INT AS hour_bin, count(*) AS payments FROM f WHERE h >= 0 AND h < {HIST_MAX_H}
    GROUP BY 1 ORDER BY 1
    """).fetchdf()
    allp = con.execute("""SELECT count(DISTINCT payment_id) FROM rs WHERE in_perimeter AND refund_exclusion IS NULL""").fetchone()[0]
    hist["cum_share_of_refunded_payments"] = hist["payments"].cumsum() / allp
    hist.to_csv(os.path.join(PHASE_DIR, "histogram_auth_to_first_refund.csv"), index=False)
    print("payments with any valid refund in perimeter:", allp)
    print(hist.head(12).to_string())


if __name__ == "__main__":
    main()
