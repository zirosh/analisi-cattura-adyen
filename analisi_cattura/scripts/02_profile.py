"""Phase 1 - Profiling of the Adyen Interactive payment accounting export.

Outputs (aggregates only, no transactional rows) in output/phase1_profile/.
"""
# ----------------------------------------------------------------- PARAMETERS
from common import ANALYSIS_START, EXPORT_END, OUT_DIR, connect
import os

PROFILE_DIR = os.path.join(OUT_DIR, "phase1_profile")
COST_COLS = ["Commission (SC)", "Markup (SC)", "Scheme Fees (SC)", "Interchange (SC)", "Processing Fee (FC)"]
# ----------------------------------------------------------------------------


def save(con, name, sql):
    df = con.execute(sql).fetchdf()
    df.to_csv(os.path.join(PROFILE_DIR, f"{name}.csv"), index=False)
    return df


def main():
    os.makedirs(PROFILE_DIR, exist_ok=True)
    con = connect()
    md = ["# Phase 1 - Profiling\n"]

    # 1. Columns and types
    cols = con.execute("DESCRIBE SELECT * FROM read_parquet('../data/accounting.parquet')".replace(
        "../data/accounting.parquet", __import__("common").PARQUET_RAW)).fetchdf()[["column_name", "column_type"]]
    cols.to_csv(os.path.join(PROFILE_DIR, "columns.csv"), index=False)
    md.append("## Columns\n" + cols.to_markdown(index=False) + "\n")

    rt = save(con, "record_type_counts", """
        SELECT "Record Type", count(*) AS records,
               count(*) FILTER (WHERE region <> 'Non-European') AS records_eu_ch_uk
        FROM ev GROUP BY 1 ORDER BY 2 DESC""")
    md.append("## Records by Record Type\n" + rt.to_markdown(index=False) + "\n")

    save(con, "account_proxy_counts", """
        SELECT account_proxy, platform, brand, region, count(*) FILTER (WHERE "Record Type"='Authorised') AS authorisations,
               count(*) AS records, min(ts_local) AS first_local, max(ts_local) AS last_local
        FROM ev2 GROUP BY ALL ORDER BY authorisations DESC""")
    save(con, "payment_method_counts", """
        SELECT region = 'Non-European' AS non_european, "Payment Method", "Payment Method Variant",
               count(*) FILTER (WHERE "Record Type"='Authorised') AS authorisations, count(*) AS records
        FROM ev GROUP BY ALL ORDER BY authorisations DESC""")
    save(con, "currency_counts", """
        SELECT ccy, region, count(*) FILTER (WHERE "Record Type"='Authorised') AS authorisations,
               sum("Authorised (PC)") FILTER (WHERE "Record Type"='Authorised') AS authorised_amount_pc,
               count(*) AS records
        FROM ev GROUP BY ALL ORDER BY records DESC""")

    # 2. Date range / time zone
    dr = save(con, "date_range", f"""
        SELECT "TimeZone", min("Booking Date") AS min_booking_raw, max("Booking Date") AS max_booking_raw,
               min(ts_local) AS min_local, max(ts_local) AS max_local, count(*) AS records,
               count(*) FILTER (WHERE ts_local < TIMESTAMP '{ANALYSIS_START}') AS before_start_local,
               count(*) FILTER (WHERE "Booking Date" < TIMESTAMP '{ANALYSIS_START}') AS before_start_raw_eastern
        FROM ev GROUP BY 1""")
    md.append("## Date range\n" + dr.to_markdown(index=False) + "\n")

    # 3. Linking of modifications
    save(con, "linking_modpsp_pairs", """
        SELECT a."Record Type" AS first_type, b."Record Type" AS second_type, count(*) AS pairs
        FROM ev a JOIN ev b ON a."Modification Psp Reference" = b."Modification Psp Reference" AND a.row_id < b.row_id
        GROUP BY 1, 2 ORDER BY 3 DESC""")
    save(con, "linking_modification_merchant_reference", """
        SELECT "Record Type",
          CASE WHEN "Modification Merchant Reference" = "Merchant Reference" THEN 'same as Merchant Reference'
               WHEN "Modification Merchant Reference" = '<auto>' THEN '<auto> (Adyen auto-capture)'
               WHEN "Modification Merchant Reference" LIKE 'FO-%' THEN 'FO-* (OMS reference)'
               WHEN regexp_matches("Modification Merchant Reference", '^[0-9]+$') THEN 'numeric'
               WHEN "Modification Merchant Reference" IS NULL THEN 'empty'
               ELSE 'other' END AS modification_merchant_reference,
          count(*) AS records, count("Modification Psp Reference") AS with_mod_psp
        FROM ev GROUP BY ALL ORDER BY 1, 3 DESC""")
    save(con, "merchant_reference_multi_auth", """
        WITH a AS (SELECT mref, region, count(*) n FROM ev WHERE "Record Type"='Authorised' GROUP BY 1, 2)
        SELECT region, n AS authorisations_per_reference, count(*) AS references FROM a GROUP BY ALL ORDER BY 1, 2""")

    # 4. Cost columns by record type
    parts = []
    for c in COST_COLS:
        parts.append(f"""count("{c}") AS "{c} n", count(*) FILTER (WHERE "{c}" <> 0) AS "{c} nonzero",
                         count(*) FILTER (WHERE "{c}" < 0) AS "{c} negative" """)
    cost = save(con, "cost_columns_by_record_type", f"""
        SELECT "Record Type", count(*) AS records, {", ".join(parts)},
               string_agg(DISTINCT "Settlement Currency", ',') AS settlement_ccys,
               string_agg(DISTINCT "Processing Fee Currency", ',') AS proc_fee_ccys
        FROM ev WHERE region <> 'Non-European' GROUP BY 1 ORDER BY 2 DESC""")
    md.append("## Cost columns by Record Type (EU/CH/UK)\n" + cost.to_markdown(index=False) + "\n")

    with open(os.path.join(PROFILE_DIR, "profile.md"), "w") as f:
        f.write("\n".join(md))
    print("\n".join(md)[:6000])


if __name__ == "__main__":
    main()
