"""FX - Download ECB monthly average reference rates (units of currency per 1 EUR).

Source: ECB Data Portal, dataset EXR, series M.<CCY>.EUR.SP00.A (monthly average).
Output: reference/ecb_fx_monthly.csv (not transactional data, committed for reproducibility).
EUR amount = amount in CCY / rate.
"""
# ----------------------------------------------------------------- PARAMETERS
import io
import os
import urllib.request

import pandas as pd

from common import REPO

CURRENCIES = ["GBP", "CHF", "PLN", "CZK", "HUF", "SEK", "DKK", "NOK", "RON", "USD", "JPY", "AUD", "CAD"]
START_PERIOD = "2025-01"
END_PERIOD = "2026-12"
OUT = os.path.join(REPO, "reference", "ecb_fx_monthly.csv")
# ----------------------------------------------------------------------------


def main():
    url = ("https://data-api.ecb.europa.eu/service/data/EXR/M." + "+".join(CURRENCIES) +
           f".EUR.SP00.A?startPeriod={START_PERIOD}&endPeriod={END_PERIOD}&format=csvdata")
    raw = urllib.request.urlopen(url, timeout=60).read().decode()
    df = pd.read_csv(io.StringIO(raw))[["CURRENCY", "TIME_PERIOD", "OBS_VALUE"]]
    df.columns = ["ccy", "month", "rate_per_eur"]
    df["month"] = pd.to_datetime(df["month"] + "-01").dt.date
    eur = pd.DataFrame({"ccy": "EUR", "month": sorted(df["month"].unique()), "rate_per_eur": 1.0})
    df = pd.concat([df, eur]).sort_values(["ccy", "month"])
    df["source"] = "ECB EXR monthly average (SP00.A)"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT}: {len(df)} rows; months {df.month.min()} - {df.month.max()}")
    print(df.pivot(index="month", columns="ccy", values="rate_per_eur").round(4).tail(14).to_string())


if __name__ == "__main__":
    main()
