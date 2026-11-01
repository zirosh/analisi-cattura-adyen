"""Phase 6 - Cost of delayed capture (opportunity cost) and net avoidable cost.

Opportunity cost = captured amount in perimeter x (S / 24) / 365 x rate     (rate default 3%)
Net avoidable cost = avoidable fee cost (phase 4) + chargeback fees + customer care (phase 5) - opportunity cost
The Excel model recomputes this with live formulas from the Assumptions sheet; this script
produces the same numbers at the default parameters for the record.
"""
# ----------------------------------------------------------------- PARAMETERS
import os

from common import ALL_THRESHOLDS_H as THRESHOLDS_H, OUT_DIR, WORK_DIR, connect, q

PHASE_DIR = os.path.join(OUT_DIR, "phase6_opportunity")
OPPORTUNITY_RATE = 0.03
CC_CONTACTS_PER_REFUND = 0.0
CC_COST_PER_CONTACT_EUR = 0.0
ACTUAL_START = "2025-01-01"     # actual period (auth months) used for the "10 months" figures
ACTUAL_END = "2025-10-01"       # last month included (first day of month)
# ----------------------------------------------------------------------------


def main():
    os.makedirs(PHASE_DIR, exist_ok=True)
    con = connect()
    W = lambda n: os.path.join(WORK_DIR, n)
    con.execute(f"CREATE VIEW p AS SELECT * FROM read_parquet('{W('payments.parquet')}')")
    con.execute(f"CREATE VIEW c AS SELECT * FROM read_parquet('{W('costs.parquet')}')")
    periods = {"actual": (ACTUAL_START, ACTUAL_END), "full_data": ("1900-01-01", "2100-01-01")}
    rows = []
    for name, (a, b) in periods.items():
        gmv = con.execute(f"""SELECT sum(captured_eur), count(*) FROM p WHERE in_perimeter
                              AND auth_month BETWEEN DATE '{a}' AND DATE '{b}'""").fetchone()
        for s in THRESHOLDS_H:
            fee, n, cbf = con.execute(f"""SELECT coalesce(sum(avoidable_fee_cost_eur),0), count(*), coalesce(sum(chargeback_fees_eur),0)
                                     FROM c WHERE threshold_h = {s} AND auth_month BETWEEN DATE '{a}' AND DATE '{b}'""").fetchone()
            cc = n * CC_CONTACTS_PER_REFUND * CC_COST_PER_CONTACT_EUR
            opp = gmv[0] * (s / 24) / 365 * OPPORTUNITY_RATE
            rows.append(dict(period=name, threshold_h=s, perimeter_payments=gmv[1], captured_eur=round(gmv[0], 2),
                             avoidable_payments=n, avoidable_fee_cost_eur=round(fee, 2), chargeback_fees_eur=round(cbf, 2),
                             customer_care_eur=cc, opportunity_cost_eur=round(opp, 2),
                             net_avoidable_cost_eur=round(fee + cbf + cc - opp, 2),
                             breakeven_rate=round((fee + cbf + cc) / (gmv[0] * (s / 24) / 365), 4)))
    import pandas as pd
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(PHASE_DIR, "net_cost_by_threshold.csv"), index=False)
    print(df.to_string())


if __name__ == "__main__":
    main()
