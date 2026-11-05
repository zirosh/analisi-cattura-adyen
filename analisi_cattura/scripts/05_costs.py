"""Phase 4 - Cost attribution of avoidable refunds.

Avoidable cost per payment and threshold S (EUR):
  + Settled fees (Commission + Markup + Scheme Fees + Interchange) x share refunded within S
  + fees on the refund records within S (SentForRefund / Refunded / RefundFailed...):
      Processing Fee, refund Commission (refund fee; negative = commission returned, e.g. Amex),
      Markup / Scheme / Interchange on refunds (negative = credits)
  - cost of a cancel (Scheme fee observed on Cancelled records, average per payment method), full refunds only
The authorisation processing fee (Received) is paid in both scenarios and is ignored.
FX: ECB monthly average of the authorisation month, applied to the fee's own currency
(settlement currency for SC columns, Processing Fee Currency for the processing fee).

Writes data/work/costs.parquet and output/phase4_costs/.
"""
# ----------------------------------------------------------------- PARAMETERS
import os

from common import ALL_THRESHOLDS_H as THRESHOLDS_H, OUT_DIR, REPO, WORK_DIR, connect, q

PHASE_DIR = os.path.join(OUT_DIR, "phase4_costs")
FX_FILE = os.path.join(REPO, "reference", "ecb_fx_monthly.csv")
CANCEL_COST_ONLY_FULL = True       # partial refund -> partial capture: no cancel record expected
EXAMPLE_THRESHOLD_H = 24
# ----------------------------------------------------------------------------


def main():
    os.makedirs(PHASE_DIR, exist_ok=True)
    con = connect()
    W = lambda n: os.path.join(WORK_DIR, n)
    con.execute(f"CREATE VIEW p AS SELECT * FROM read_parquet('{W('payments.parquet')}')")
    con.execute(f"CREATE VIEW rs AS SELECT * FROM read_parquet('{W('refunds_scoped.parquet')}')")
    con.execute(f"CREATE VIEW av AS SELECT * FROM read_parquet('{W('avoidable.parquet')}')")
    con.execute(f"CREATE VIEW mods AS SELECT * FROM read_parquet('{W('mods.parquet')}')")
    con.execute(f"""CREATE TABLE fx AS SELECT ccy AS fx_ccy, month::DATE AS fx_month, rate_per_eur
                    FROM read_csv('{FX_FILE}', header=true)""")

    # ------------------------------------------------ cost of a cancel: avg fee per Cancelled record, by method
    cancel = q(con, """
    WITH c AS (
      SELECT m.pm, (m.scheme_fees + m.commission + m.markup + m.interchange) / fx.rate_per_eur AS fee_eur
      FROM mods m
      LEFT JOIN p USING (payment_id)
      JOIN fx ON fx.fx_ccy = coalesce(m.settle_ccy, m.ccy) AND fx.fx_month = date_trunc('month', m.ts_local)::DATE
      WHERE m.rt = 'Cancelled'
    )
    SELECT pm, count(*) AS cancels, round(avg(fee_eur), 4) AS avg_cancel_fee_eur,
           round(sum(fee_eur), 2) AS total_cancel_fee_eur FROM c GROUP BY 1 ORDER BY 2 DESC
    """, 40)
    cancel.to_csv(os.path.join(PHASE_DIR, "cancel_cost_by_method.csv"), index=False)
    con.register("cancel_df", cancel)
    tot_c = cancel["total_cancel_fee_eur"].sum() / cancel["cancels"].sum()

    # ------------------------------------------------ refund-side fees per payment and threshold
    parts = []
    for s in THRESHOLDS_H:
        parts.append(f"""
        SELECT {s} AS threshold_h, rs.payment_id,
          sum(coalesce(r_commission, 0) / fxs.rate_per_eur) FILTER (WHERE r_commission > 0) AS r_commission_pos_eur,
          sum(coalesce(r_commission, 0) / fxs.rate_per_eur) FILTER (WHERE r_commission < 0) AS r_commission_credit_eur,
          sum((coalesce(r_markup, 0) + coalesce(r_scheme, 0)) / fxs.rate_per_eur) AS r_markup_scheme_eur,
          sum(coalesce(r_interchange, 0) / fxs.rate_per_eur) AS r_interchange_eur,
          sum(coalesce(r_processing_fee, 0) / fxp.rate_per_eur) AS r_processing_fee_eur
        FROM rs
        JOIN p USING (payment_id)
        LEFT JOIN fx fxs ON fxs.fx_ccy = coalesce(rs.r_settle_ccy, p.ccy) AND fxs.fx_month = p.auth_month
        LEFT JOIN fx fxp ON fxp.fx_ccy = coalesce(rs.r_pf_ccy, 'EUR') AND fxp.fx_month = p.auth_month
        WHERE rs.in_perimeter AND rs.refund_exclusion IS NULL AND rs.refund_delay_h <= {s}
        GROUP BY rs.payment_id""")
    con.execute("CREATE TABLE rfees AS " + " UNION ALL ".join(parts))

    con.execute(f"""
    CREATE TABLE costs AS
    SELECT av.threshold_h, av.payment_id, av.n_refunds_in_s, av.refund_in_s, av.refund_in_s_eur, av.share_refunded, av.is_full,
      p.account_proxy, p.platform, p.brand, p.region, p.country, p.pm, p.variant, p.ccy, p.settle_ccy, p.auth_month,
      p.captured_amount, p.captured_eur, fxs.rate_per_eur AS settle_rate,
      coalesce(p.s_commission, 0) / fxs.rate_per_eur * av.share_refunded AS s_commission_eur,
      coalesce(p.s_markup, 0) / fxs.rate_per_eur * av.share_refunded AS s_markup_eur,
      coalesce(p.s_scheme, 0) / fxs.rate_per_eur * av.share_refunded AS s_scheme_eur,
      coalesce(p.s_interchange, 0) / fxs.rate_per_eur * av.share_refunded AS s_interchange_eur,
      coalesce(rf.r_processing_fee_eur, 0) AS r_processing_fee_eur,
      coalesce(rf.r_commission_pos_eur, 0) AS r_commission_fee_eur,
      coalesce(rf.r_commission_credit_eur, 0) AS r_commission_credit_eur,
      coalesce(rf.r_markup_scheme_eur, 0) AS r_markup_scheme_eur,
      coalesce(rf.r_interchange_eur, 0) AS r_interchange_eur,
      CASE WHEN av.is_full OR NOT {CANCEL_COST_ONLY_FULL} THEN -coalesce(c.avg_cancel_fee_eur, {tot_c}) ELSE 0 END AS cancel_cost_eur,
      -- disputes on the same payment (phase 5)
      p.n_chargeback, coalesce(p.chargeback_fees, 0) / fxs.rate_per_eur AS chargeback_fees_eur,
      coalesce(p.chargeback_amount_sc, 0) / fxs.rate_per_eur AS chargeback_amount_eur
    FROM av
    JOIN p USING (payment_id)
    LEFT JOIN fx fxs ON fxs.fx_ccy = coalesce(p.settle_ccy, p.ccy) AND fxs.fx_month = p.auth_month
    LEFT JOIN rfees rf ON rf.payment_id = av.payment_id AND rf.threshold_h = av.threshold_h
    LEFT JOIN cancel_df c ON c.pm = p.pm
    """)
    con.execute("""ALTER TABLE costs ADD COLUMN avoidable_fee_cost_eur DOUBLE""")
    con.execute("""UPDATE costs SET avoidable_fee_cost_eur = s_commission_eur + s_markup_eur + s_scheme_eur + s_interchange_eur
                   + r_processing_fee_eur + r_commission_fee_eur + r_commission_credit_eur + r_markup_scheme_eur
                   + r_interchange_eur + cancel_cost_eur""")
    con.execute(f"COPY costs TO '{W('costs.parquet')}' (FORMAT PARQUET)")

    summ = q(con, """
    SELECT threshold_h, count(*) AS avoidable_payments, round(sum(refund_in_s_eur)) AS refunded_eur,
      round(sum(s_commission_eur), 2) AS settled_commission, round(sum(s_markup_eur), 2) AS settled_markup,
      round(sum(s_scheme_eur), 2) AS settled_scheme, round(sum(s_interchange_eur), 2) AS settled_interchange,
      round(sum(r_processing_fee_eur), 2) AS refund_processing_fee, round(sum(r_commission_fee_eur), 2) AS refund_commission_fee,
      round(sum(r_commission_credit_eur), 2) AS refund_commission_credit, round(sum(r_markup_scheme_eur), 2) AS refund_markup_scheme,
      round(sum(r_interchange_eur), 2) AS refund_interchange, round(sum(cancel_cost_eur), 2) AS cancel_cost,
      round(sum(avoidable_fee_cost_eur), 2) AS avoidable_fee_cost,
      round(sum(avoidable_fee_cost_eur) / count(*), 3) AS cost_per_avoidable_refund,
      round(sum(chargeback_fees_eur), 2) AS chargeback_fees, sum((n_chargeback > 0)::INT) AS payments_with_chargeback
    FROM costs GROUP BY 1 ORDER BY 1
    """)
    summ.to_csv(os.path.join(PHASE_DIR, "fee_breakdown_by_threshold.csv"), index=False)
    pm = q(con, f"""
    SELECT threshold_h, pm AS payment_method, count(*) AS avoidable_payments, round(sum(refund_in_s_eur)) AS refunded_eur,
      round(sum(avoidable_fee_cost_eur), 2) AS avoidable_fee_cost_eur,
      round(sum(avoidable_fee_cost_eur) / count(*), 3) AS cost_per_avoidable_refund,
      round(10000 * sum(avoidable_fee_cost_eur) / nullif(sum(refund_in_s_eur), 0), 1) AS cost_bps_of_refunded
    FROM costs WHERE threshold_h = {EXAMPLE_THRESHOLD_H} GROUP BY ALL ORDER BY avoidable_payments DESC
    """, 40)
    pm.to_csv(os.path.join(PHASE_DIR, f"cost_per_refund_by_method_S{EXAMPLE_THRESHOLD_H}.csv"), index=False)
    q(con, "SELECT count(*) FILTER (WHERE settle_rate IS NULL) missing_fx, count(*) FROM costs")


if __name__ == "__main__":
    main()
