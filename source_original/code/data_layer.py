"""
Data layer: builds one clean, aligned daily panel for every security the study
can ever hold, plus point-in-time index membership for the S&P 500 and the
Nasdaq-100.

Sources (all free, all reproducible)
------------------------------------
1. Johnbrick123/sp500-data (GitHub release, refreshed nightly). Point-in-time
   S&P 500 membership since 1996-01-02 and daily OHLCV for 1,000+ labels,
   including ~300 delisted companies recovered from Tiingo (permaTicker),
   Quandl WIKI and Kaggle archives. Delisted companies carry a dated label,
   e.g. "SNDK-201605" (old SanDisk, delisted May 2016), so a recycled ticker
   never points at the wrong company.
2. Yahoo Finance chart API (downloaded through the browser): Nasdaq-100
   members missing from source 1, plus benchmarks (^SP500TR, SPY, QQQ, ^VIX ...).
3. jmccarrell/n100tickers: Nasdaq-100 membership changes since Feb-2007.
4. FRED: T-bill and Treasury yields, EUR/USD, VIX.

Output
------
data/processed/panel.npz   wide float arrays [n_dates x n_labels]
data/processed/labels.json label metadata (source, first/last date)
data/processed/spx_intervals.parquet, ndx_intervals_resolved.parquet
"""
from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

from config import (FRED_JSON, JB_MEMBERS, JB_PRICES, JB_RENAMES, NDX_MEMBERS,
                    NDX_YAHOO_MAP, PROC, YAHOO_BATCH)

FIELDS = ["open", "high", "low", "close", "adj_close", "dividends", "volume"]
SUFFIX = re.compile(r"^(?P<base>.+)-(?P<ym>\d{6})$")


# ---------------------------------------------------------------------------
# 1. Raw sources
# ---------------------------------------------------------------------------
def load_jb() -> pd.DataFrame:
    p = pd.read_parquet(JB_PRICES)
    p["date"] = pd.to_datetime(p["date"])
    p["src"] = "jb:" + p["source"].astype(str)
    return p[["ticker", "date"] + FIELDS + ["src"]]


def load_yahoo() -> pd.DataFrame:
    y = pd.read_parquet(YAHOO_BATCH)
    y["date"] = pd.to_datetime(y["date"])
    y["src"] = "yahoo"
    y["ticker"] = "Y_" + y["ticker"]           # separate namespace from source 1
    return y[["ticker", "date"] + FIELDS + ["src"]]


def trading_calendar(y: pd.DataFrame) -> pd.DatetimeIndex:
    """NYSE trading days = days on which the S&P 500 index printed."""
    d = y.loc[y.ticker == "Y_^GSPC", "date"].drop_duplicates().sort_values()
    return pd.DatetimeIndex(d.values)


# ---------------------------------------------------------------------------
# 2. Nasdaq-100: resolve contemporaneous tickers to a price label
# ---------------------------------------------------------------------------
# Hand-checked identity fixes (contemporaneous ticker -> label that holds the
# ORIGINAL company's history). Each one is explained:
NDX_MANUAL = {
    # old News Corp (NWSA, NDX 2009-2013) was renamed Twenty-First Century Fox
    # in June 2013; its history lives under FOXA-201903 in source 1.
    ("NWSA", "2009-01-20"): "FOXA-201903",
    # GOLD in 2011-2013 was Randgold Resources ADR; today's GOLD is Barrick.
    ("GOLD", "2011-12-19"): None,
    # Yahoo! Inc. (YHOO) became Altaba (AABA) in June 2017; history kept under AABA.
    ("YHOO", "2007-01-01"): "AABA",
}


def _overlap_days(rng: pd.Series, s: pd.Timestamp, e: pd.Timestamp) -> int:
    a, b = max(rng["min"], s), min(rng["max"], e)
    return max(0, (b - a).days)


def resolve_ndx(ranges: pd.DataFrame) -> pd.DataFrame:
    """For every NDX membership interval pick the label whose price history
    covers it best. Candidates: same symbol in source 1 (bare or dated label),
    renamed symbol, Yahoo symbol, Yahoo mapped symbol. Reject candidates that
    cover < 60% of the interval (protects against recycled tickers)."""
    iv = pd.read_csv(NDX_MEMBERS, parse_dates=["start", "end"])
    ren = pd.read_csv(JB_RENAMES)
    renmap = dict(zip(ren.old, ren.new))
    ymap = json.load(open(NDX_YAHOO_MAP))
    labels = ranges.index
    base_of = {lab: (SUFFIX.match(lab).group("base") if SUFFIX.match(lab) else lab) for lab in labels}
    by_base: dict[str, list[str]] = {}
    for lab, b in base_of.items():
        by_base.setdefault(b, []).append(lab)
    end_cap = ranges["max"].max()
    out = []
    for r in iv.itertuples():
        s = r.start
        e = r.end if pd.notna(r.end) else end_cap
        key = (r.ticker, str(s.date()))
        if key in NDX_MANUAL:
            lab = NDX_MANUAL[key]
            out.append((r.ticker, s, r.end, lab, "manual"))
            continue
        cands = set()
        for sym in {r.ticker, renmap.get(r.ticker), ymap.get(r.ticker)} - {None}:
            cands |= set(by_base.get(sym, []))
            cands |= set(by_base.get("Y_" + sym, []))
        best, best_ov = None, 0
        need = max(1, (e - s).days)
        if need < 10:  # a member added days before the data cut-off: just require the start to be covered
            need = 1
        for c in cands:
            ov = _overlap_days(ranges.loc[c], s, e)
            # prefer source 1 (curated corporate actions) on ties
            score = ov + (0.5 if not c.startswith("Y_") else 0)
            if (ov / need >= 0.60 or (need == 1 and ranges.loc[c, 'min'] <= s)) and score > best_ov:
                best, best_ov = c, score
        out.append((r.ticker, s, r.end, best, "auto" if best else "missing"))
    return pd.DataFrame(out, columns=["ticker", "start", "end", "label", "how"])


# ---------------------------------------------------------------------------
# 3. Wide panel
# ---------------------------------------------------------------------------
def build_panel():
    jb, y = load_jb(), load_yahoo()
    cal = trading_calendar(y)
    allp = pd.concat([jb, y], ignore_index=True)
    allp = allp[allp.date.isin(cal)]
    ranges = allp.groupby("ticker").date.agg(["min", "max"])

    spx = pd.read_parquet(JB_MEMBERS)
    spx["start"] = pd.to_datetime(spx["start"])
    spx["end"] = pd.to_datetime(spx["end"])
    ndx = resolve_ndx(ranges)

    bench = [t for t in ranges.index if t.startswith("Y_^") or t in
             ("Y_SPY", "Y_QQQ", "Y_RSP", "Y_MTUM", "Y_SPMO", "Y_IWM", "Y_DIA", "Y_EURUSD=X")]
    keep = sorted(set(spx.ticker) | set(ndx.label.dropna()) | set(bench))
    keep = [k for k in keep if k in ranges.index]

    sub = allp[allp.ticker.isin(keep)].drop_duplicates(["ticker", "date"], keep="first")
    lab_idx = {k: i for i, k in enumerate(keep)}
    d_idx = pd.Series(np.arange(len(cal)), index=cal)
    ri = d_idx.loc[sub.date].values
    ci = sub.ticker.map(lab_idx).values
    arrays = {}
    for f in FIELDS:
        a = np.full((len(cal), len(keep)), np.nan, dtype=np.float64)
        a[ri, ci] = sub[f].astype(float).values
        arrays[f] = a
    arrays["dividends"] = np.nan_to_num(arrays["dividends"], nan=0.0)

    # Forward-fill isolated holes INSIDE a security's life (never before its
    # first or after its last print), and flag how many cells were filled.
    filled = 0
    for j in range(len(keep)):
        col = arrays["adj_close"][:, j]
        ok = np.where(~np.isnan(col))[0]
        if len(ok) == 0:
            continue
        a0, a1 = ok[0], ok[-1]
        for f in ["open", "high", "low", "close", "adj_close"]:
            seg = pd.Series(arrays[f][a0:a1 + 1, j]).ffill().values
            filled += int(np.isnan(arrays[f][a0:a1 + 1, j]).sum()) if f == "adj_close" else 0
            arrays[f][a0:a1 + 1, j] = seg
    # Bars where open/high/low are missing but close exists -> use close.
    for f in ["open", "high", "low"]:
        m = np.isnan(arrays[f]) & ~np.isnan(arrays["close"])
        arrays[f][m] = arrays["close"][m]

    meta = {k: {"src": sub.loc[sub.ticker == k, "src"].mode().iat[0] if (sub.ticker == k).any() else None,
                "first": str(ranges.loc[k, "min"].date()), "last": str(ranges.loc[k, "max"].date())}
            for k in keep}
    np.savez_compressed(PROC / "panel.npz", dates=cal.values.astype("datetime64[D]").astype(np.int64),
                        labels=np.array(keep), **arrays)
    json.dump(meta, open(PROC / "labels.json", "w"), indent=0)
    spx.to_parquet(PROC / "spx_intervals.parquet", index=False)
    ndx.to_parquet(PROC / "ndx_intervals_resolved.parquet", index=False)
    return dict(n_dates=len(cal), n_labels=len(keep), filled=filled,
                ndx_missing=int((ndx.how == "missing").sum()), ndx_total=len(ndx))


# ---------------------------------------------------------------------------
# 4. FRED
# ---------------------------------------------------------------------------
def load_fred() -> pd.DataFrame:
    raw = json.load(open(FRED_JSON))["data"]
    cols = {}
    for k, txt in raw.items():
        from io import StringIO
        df = pd.read_csv(StringIO(txt))
        name = k.replace("_b", "")
        s = pd.to_numeric(df.iloc[:, 1], errors="coerce")
        s.index = pd.to_datetime(df.iloc[:, 0])
        cols[name] = s
    return pd.DataFrame(cols).sort_index()


if __name__ == "__main__":
    print(build_panel())
