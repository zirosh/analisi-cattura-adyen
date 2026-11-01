"""Phase 7 - Monthly trend, breakdowns and annualisation inputs.

Outputs in output/phase7_trend/:
  monthly_trend.csv            month x threshold (+ platform split)
  by_market.csv / by_account.csv / by_method.csv     period x threshold
  annualisation_base.csv       region x threshold: actual-period GMV & cost, SFCC-immediate run-rate,
                               and (back-test, only when data exists) Nov-Dec actual
Basis A (user spec): % of GMV per market in the actual period (Jan-Oct).
Basis B (go-forward): % of GMV in account-months with SFCC immediate auto-capture inside the actual period
(the configuration that will be live when migrating to Stripe; Hybris is decommissioned).
"""
# ----------------------------------------------------------------- PARAMETERS
import os

import pandas as pd

from common import ALL_THRESHOLDS_H, OUT_DIR, WORK_DIR, connect, q

PHASE_DIR = os.path.join(OUT_DIR, "phase7_trend")
ACTUAL_START = "2025-01-01"
ACTUAL_END = "2025-10-01"          # last actual month (first day)
FORECAST_START = "2025-11-01"      # months to estimate (back-test available only for 2025 data)
FORECAST_END = "2025-12-01"
# ----------------------------------------------------------------------------


def grouped(con, dims, where_p="TRUE", where_c="TRUE", extra_cols=""):
    d = ", ".join(dims)
    return con.execute(f"""
    WITH g AS (SELECT {d}, count(*) AS perimeter_payments, sum(captured_eur) AS captured_eur
               FROM p WHERE in_perimeter AND {where_p} GROUP BY ALL),
    t AS (SELECT DISTINCT threshold_h FROM c),
    a AS (SELECT {d}, threshold_h, count(*) AS avoidable_payments, sum(refund_in_s_eur) AS refunded_in_s_eur,
                 sum(avoidable_fee_cost_eur) AS avoidable_fee_cost_eur, sum(chargeback_fees_eur) AS chargeback_fees_eur
          FROM c WHERE {where_c} GROUP BY ALL)
    SELECT g.*, t.threshold_h, coalesce(a.avoidable_payments, 0) AS avoidable_payments,
      coalesce(a.refunded_in_s_eur, 0) AS refunded_in_s_eur, coalesce(a.avoidable_fee_cost_eur, 0) AS avoidable_fee_cost_eur,
      coalesce(a.chargeback_fees_eur, 0) AS chargeback_fees_eur,
      100.0 * coalesce(a.avoidable_payments, 0) / g.perimeter_payments AS pct_payments_refunded_in_s,
      100.0 * coalesce(a.refunded_in_s_eur, 0) / nullif(g.captured_eur, 0) AS pct_gmv_refunded_in_s,
      10000.0 * coalesce(a.avoidable_fee_cost_eur, 0) / nullif(g.captured_eur, 0) AS cost_bps_of_gmv
    FROM g CROSS JOIN t LEFT JOIN a USING ({d}, threshold_h)
    ORDER BY ALL
    """).fetchdf()


def main():
    os.makedirs(PHASE_DIR, exist_ok=True)
    con = connect()
    W = lambda n: os.path.join(WORK_DIR, n)
    con.execute(f"""CREATE VIEW p AS SELECT *, CASE WHEN platform LIKE 'SFCC%' THEN 'SFCC'
                     WHEN platform = 'Hybris' THEN 'Hybris' ELSE 'Other (Ariete, misc.)' END AS platform_group,
                     CASE WHEN auth_month BETWEEN DATE '{ACTUAL_START}' AND DATE '{ACTUAL_END}' THEN 'Actual'
                          WHEN auth_month BETWEEN DATE '{FORECAST_START}' AND DATE '{FORECAST_END}' THEN 'Forecast months (actual data, back-test)'
                          ELSE 'Outside' END AS period
                     FROM read_parquet('{W('payments.parquet')}')""")
    con.execute(f"""CREATE VIEW c AS SELECT c.*, p.platform_group, p.period, p.capture_class
                    FROM read_parquet('{W('costs.parquet')}') c JOIN p USING (payment_id)""")

    mt = grouped(con, ["auth_month"])
    mt.to_csv(os.path.join(PHASE_DIR, "monthly_trend.csv"), index=False)
    grouped(con, ["auth_month", "platform_group"]).to_csv(os.path.join(PHASE_DIR, "monthly_trend_by_platform.csv"), index=False)
    for name, dims in [("by_market", ["period", "region", "country"]), ("by_account", ["period", "account_proxy", "platform", "brand", "region"]),
                       ("by_method", ["period", "pm"]), ("by_region", ["period", "region"]), ("by_period", ["period"]),
                       ("by_platform", ["period", "platform_group"])]:
        grouped(con, dims).to_csv(os.path.join(PHASE_DIR, f"{name}.csv"), index=False)
    # whole data, all periods together
    grouped(con, ["region"]).to_csv(os.path.join(PHASE_DIR, "by_region_full_data.csv"), index=False)

    # SFCC immediate auto-capture run-rate (basis B), in the actual period and over the full data
    sf_a = grouped(con, ["region"], "platform_group = 'SFCC' AND period = 'Actual'", "platform_group = 'SFCC' AND period = 'Actual'")
    sf_a["basis"] = "B: SFCC immediate, actual period"
    sf_f = grouped(con, ["region"], "platform_group = 'SFCC'", "platform_group = 'SFCC'")
    sf_f["basis"] = "SFCC immediate, all data"
    act = grouped(con, ["region"], "period = 'Actual'", "period = 'Actual'")
    act["basis"] = "A: all perimeter, actual period"
    bt = grouped(con, ["region"], "period LIKE 'Forecast%'", "period LIKE 'Forecast%'")
    bt["basis"] = "Back-test: forecast months actual"
    base = pd.concat([act, sf_a, sf_f, bt])
    base.to_csv(os.path.join(PHASE_DIR, "annualisation_base.csv"), index=False)
    print(base[base.threshold_h == 24].round(3).to_string())
    print(mt[mt.threshold_h == 24].round(3).to_string())


if __name__ == "__main__":
    main()
