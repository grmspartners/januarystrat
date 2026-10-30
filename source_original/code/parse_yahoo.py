"""
Parse the Yahoo Finance batch (NDJSON, gzip) downloaded through the browser
into a tidy parquet: date, ticker, open, high, low, close, volume, adj_close,
dividends, stock_splits. Yahoo's 'close' is split-adjusted; 'adj_close' is
split- and dividend-adjusted. Timestamps are converted to the exchange date.
"""
from __future__ import annotations

import gzip
import json

import pandas as pd

from config import PROC, YAHOO_BATCH, YAHOO_META, YAHOO_RAW


def main():
    rows, meta = [], {}
    with gzip.open(YAHOO_RAW, "rt") as f:
        head = json.loads(f.readline())
        for line in f:
            d = json.loads(line)
            s = d["s"]
            meta[s] = d["meta"]
            tz = d["meta"]["tz"] or "America/New_York"
            df = pd.DataFrame({"ts": d["t"], "open": d["o"], "high": d["h"], "low": d["l"], "close": d["c"],
                               "volume": d["v"], "adj_close": d["ac"] if d["ac"] else d["c"]})
            df["date"] = pd.to_datetime(df.ts, unit="s", utc=True).dt.tz_convert(tz).dt.tz_localize(None).dt.normalize()
            conv = lambda k: pd.to_datetime(int(k), unit="s", utc=True).tz_convert(tz).tz_localize(None).normalize()
            div = pd.Series({conv(k): v["amount"] for k, v in d["div"].items()}, dtype=float)
            spl = pd.Series({conv(k): v["numerator"] / v["denominator"] for k, v in d["spl"].items()}, dtype=float)
            df["dividends"] = df.date.map(div).fillna(0.0)
            df["stock_splits"] = df.date.map(spl).fillna(0.0)
            df["ticker"] = s
            rows.append(df.drop(columns="ts"))
    y = pd.concat(rows, ignore_index=True).dropna(subset=["close"]).drop_duplicates(["ticker", "date"], keep="last")
    PROC.mkdir(parents=True, exist_ok=True)
    y.to_parquet(YAHOO_BATCH, index=False)
    json.dump(meta, open(YAHOO_META, "w"), indent=0)
    print(y.shape, y.ticker.nunique(), "symbols not found on Yahoo:", len(head["fail"]))


if __name__ == "__main__":
    main()
