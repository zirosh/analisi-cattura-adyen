"""Phase 0 - Ingest: extract the Adyen "Interactive payment accounting" export and convert it to Parquet.

Never modifies the original archive: it is extracted (copied) into data/.
Re-usable for other exports: change the parameters below.
"""
# ----------------------------------------------------------------- PARAMETERS
import glob
import os
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO, "data")
ZIP_GLOB = [os.path.join(REPO, "*.zip"), os.path.join(DATA_DIR, "*.zip")]  # where the raw archives live
PARQUET_OUT = os.path.join(DATA_DIR, "accounting.parquet")
# ----------------------------------------------------------------------------

import duckdb

COLUMNS = {
    "Merchant Reference": "VARCHAR", "Payment Method": "VARCHAR", "Booking Date": "TIMESTAMP",
    "TimeZone": "VARCHAR", "Main Currency": "VARCHAR", "Main Amount": "DECIMAL(18,2)",
    "Record Type": "VARCHAR", "Payment Currency": "VARCHAR", "Received (PC)": "DECIMAL(18,2)",
    "Authorised (PC)": "DECIMAL(18,2)", "Captured (PC)": "DECIMAL(18,2)", "Settlement Currency": "VARCHAR",
    "Payable (SC)": "DECIMAL(18,2)", "Commission (SC)": "DECIMAL(18,2)", "Markup (SC)": "DECIMAL(18,2)",
    "Scheme Fees (SC)": "DECIMAL(18,2)", "Interchange (SC)": "DECIMAL(18,2)",
    "Processing Fee Currency": "VARCHAR", "Processing Fee (FC)": "DECIMAL(18,2)",
    "Payment Method Variant": "VARCHAR", "Issuer Country": "VARCHAR", "Shopper Country": "VARCHAR",
    "Modification Merchant Reference": "VARCHAR", "Payable Batch": "VARCHAR", "Unique Terminal ID": "VARCHAR",
    "Store": "VARCHAR", "Modification Psp Reference": "VARCHAR", "Issuer Name": "VARCHAR",
}


def extract():
    csvs = []
    for pattern in ZIP_GLOB:
        for z in sorted(glob.glob(pattern)):
            with zipfile.ZipFile(z) as zf:
                for n in zf.namelist():
                    if n.lower().endswith(".csv"):
                        out = os.path.join(DATA_DIR, os.path.basename(n))
                        if not os.path.exists(out):
                            zf.extract(n, DATA_DIR)
                        csvs.append(out)
    return sorted(set(csvs))


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    csvs = extract()
    print("CSV files:", [os.path.basename(c) for c in csvs])
    con = duckdb.connect()
    cols = ", ".join(f"'{k}': '{v}'" for k, v in COLUMNS.items())
    files = "[" + ", ".join(f"'{c}'" for c in csvs) + "]"
    # row_id preserves the original file order (used as tie-breaker for same-second events)
    con.execute(f"""
        COPY (
          SELECT row_number() OVER () AS row_id, *
          FROM read_csv({files}, header=true, delim=',', quote='"', escape='"',
                        columns={{{cols}}}, timestampformat='%Y-%m-%d %H:%M:%S')
        ) TO '{PARQUET_OUT}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    n = con.execute(f"select count(*) from '{PARQUET_OUT}'").fetchone()[0]
    print(f"Wrote {PARQUET_OUT}: {n:,} rows")


if __name__ == "__main__":
    main()
