"""Shared parameters and helpers for the capture-delay analysis.

Every phase script imports this module. Change the parameters here (or override them
in the phase script header) to re-run on a new export (e.g. 2026 data, or Stripe data
after re-mapping the columns).
"""
import os

import duckdb

# ============================================================== PARAMETERS ==
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO, "data")
OUT_DIR = os.path.join(REPO, "output")
WORK_DIR = os.path.join(DATA_DIR, "work")          # intermediate parquet (git-ignored)
PARQUET_RAW = os.path.join(DATA_DIR, "accounting.parquet")

# Analysis window, expressed in Europe/Amsterdam local time (the export is cut on CET days).
# Production run (2026 export): ANALYSIS_START = '2026-01-01', EXPORT_END = '2026-10-31 23:59:59'
ANALYSIS_START = "2025-01-01 00:00:00"
EXPORT_END = "2025-12-31 23:59:59"
TAIL_DAYS = 3                                       # auths in the last N days are left out of perimeter
REPORT_TZ = "Europe/Amsterdam"                      # time zone used for months / dates in outputs

# Markets in scope (user instruction: only EU, CH and UK; US/CA/APAC already capture manually)
EUROPEAN_CURRENCIES = ["EUR", "GBP", "CHF", "PLN", "CZK", "HUF", "SEK", "DKK", "NOK", "RON"]

# Capture-delay thresholds (hours)
THRESHOLDS_H = [12, 24, 48, 72]                     # main thresholds requested
EXTRA_THRESHOLDS_H = [1, 2, 4, 6]                   # supplementary short-delay sensitivity
ALL_THRESHOLDS_H = sorted(EXTRA_THRESHOLDS_H + THRESHOLDS_H)
# Capture classification of an account (median Authorised -> first SentForSettle)
IMMEDIATE_MAX_H = 1.0
# ============================================================================

# Currency -> country for non-EUR European currencies (used when the reference has no country)
CCY_COUNTRY = {"GBP": "GB", "CHF": "CH", "PLN": "PL", "CZK": "CZ", "HUF": "HU", "SEK": "SE",
               "DKK": "DK", "NOK": "NO", "RON": "RO"}

# Reference prefix -> (platform, brand). Inferred from the data: to be confirmed by the business.
PREFIX_MAP = {
    "HYD": ("Hybris", "De'Longhi"), "HYK": ("Hybris", "Kenwood"), "HYB": ("Hybris", "Braun"),
    "HYC": ("Hybris", "Nutribullet"),
    "SFDL": ("SFCC", "De'Longhi"), "SFKW": ("SFCC", "Kenwood"), "SFBR": ("SFCC", "Braun"),
    "SFCB": ("SFCC", "Nutribullet"), "SSFDL": ("SFCC-Service", "De'Longhi"),
    "ARI": ("Ariete", "Ariete"),
}


def connect(threads=4):
    con = duckdb.connect()
    con.execute(f"SET threads={threads}")
    con.execute("SET TimeZone='UTC'")
    os.makedirs(WORK_DIR, exist_ok=True)
    create_events_view(con)
    return con


def create_events_view(con):
    """`ev`: raw records + normalised columns (UTC timestamp, local month, market keys)."""
    ccy_case = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in CCY_COUNTRY.items())
    eu_list = ", ".join(f"'{c}'" for c in EUROPEAN_CURRENCIES)
    pfx_case_platform = " ".join(f"WHEN '{k}' THEN '{v[0]}'" for k, v in PREFIX_MAP.items())
    pfx_case_brand = " ".join(f"WHEN '{k}' THEN '{v[1].replace(chr(39), chr(39)*2)}'" for k, v in PREFIX_MAP.items())
    con.execute(f"""
    CREATE OR REPLACE VIEW ev AS
    WITH b AS (
      SELECT *,
        -- Booking Date is US Eastern wall-clock; the TimeZone column says EST (UTC-5) or EDT (UTC-4)
        "Booking Date" + CASE "TimeZone" WHEN 'EST' THEN INTERVAL 5 HOUR WHEN 'EDT' THEN INTERVAL 4 HOUR END AS ts_utc,
        coalesce("Main Currency", "Payment Currency") AS ccy,
        "Merchant Reference" AS mref,
        CASE
          WHEN "Merchant Reference" LIKE 'card-validation%' THEN 'CARDVAL'
          WHEN regexp_matches("Merchant Reference", '^SSFDL[A-Z]{{2}}') THEN 'SSFDL'
          WHEN regexp_matches("Merchant Reference", '^SF[A-Z]{{2}}(EU|UK|CH|US|CA|AU|JP|NZ)') THEN substr("Merchant Reference", 1, 4)
          WHEN regexp_matches("Merchant Reference", '^HY[A-Z][A-Z]{{2}}[0-9]') THEN substr("Merchant Reference", 1, 3)
          WHEN "Merchant Reference" LIKE 'ARIIT%' THEN 'ARI'
          WHEN regexp_matches("Merchant Reference", '^[0-9]+/[0-9]+$') THEN 'NUM/NUM'
          WHEN regexp_matches("Merchant Reference", '^[0-9]+$') THEN 'NUMERIC'
          WHEN "Merchant Reference" LIKE 'payment_%' THEN 'PAYMENT_UUID'
          WHEN regexp_matches("Merchant Reference", '^[0-9a-f]{{10}}$') THEN 'HEX10'
          ELSE 'OTHER'
        END AS ref_group
      FROM read_parquet('{PARQUET_RAW}')
    )
    SELECT *,
      timezone('{REPORT_TZ}', ts_utc::TIMESTAMPTZ)::TIMESTAMP AS ts_local,
      CASE WHEN ccy = 'GBP' THEN 'UK' WHEN ccy = 'CHF' THEN 'CH'
           WHEN ccy IN ({eu_list}) THEN 'EU' ELSE 'Non-European' END AS region,
      coalesce(CASE ref_group {pfx_case_platform} END, 'Other') AS platform,
      coalesce(CASE ref_group {pfx_case_brand} END, 'Unknown') AS brand,
      CASE
        WHEN ccy <> 'EUR' AND ccy IN ({eu_list}) THEN CASE ccy {ccy_case} END
        WHEN ref_group IN ('HYD','HYK','HYB','HYC') THEN substr(mref, 4, 2)
        WHEN ref_group = 'SSFDL' THEN substr(mref, 6, 2)
        WHEN ref_group = 'ARI' THEN 'IT'
        ELSE coalesce("Shopper Country", '??')
      END AS country
    FROM b
    """)
    con.execute("""
    CREATE OR REPLACE VIEW ev2 AS
    SELECT *, ref_group || '_' || region AS account_proxy FROM ev
    """)


def q(con, sql, n=50):
    """Run a query and print a compact table (never huge output)."""
    df = con.execute(sql).fetchdf()
    print(df.head(n).to_string(max_colwidth=45))
    if len(df) > n:
        print(f"... {len(df) - n} more rows")
    return df
