"""
Nasdaq-100 point-in-time membership (Feb-2007 onward) from the YAML change
files of github.com/jmccarrell/n100tickers (MIT licence).

Usage: git clone https://github.com/jmccarrell/n100tickers  (anywhere)
       python build_ndx_membership.py <path-to-clone>

Output: data/raw/ndx_membership_intervals.csv (ticker, start, end) with the
CONTEMPORANEOUS ticker (e.g. PCLN, not BKNG). YAML is read with BaseLoader so
that a ticker like ON is not parsed as boolean True.
"""
from __future__ import annotations

import datetime as dt
import glob
import sys

import pandas as pd
import yaml

from config import NDX_MEMBERS


def main(repo):
    base = f"{repo}/src/nasdaq_100_ticker_history"
    load = lambda y: yaml.load(open(f"{base}/n100-ticker-changes-{y}.yaml"), Loader=yaml.BaseLoader)
    years = sorted(int(f.split("-")[-1][:4]) for f in glob.glob(base + "/n100-ticker-changes-*.yaml"))
    d0 = load(years[0])
    cur = set(d0["tickers_on_Jan_1"])
    start = {t: dt.date(years[0], 1, 1) for t in cur}
    intervals = []
    for y in years:
        d = load(y)
        jan = set(d["tickers_on_Jan_1"])
        if jan != cur:
            for t in cur - jan:
                intervals.append((t, start.pop(t), dt.date(y, 1, 1)))
            for t in jan - cur:
                start[t] = dt.date(y, 1, 1)
            cur = set(jan)
        ch = d.get("changes") or {}
        for ds in sorted(ch):
            day = dt.date.fromisoformat(ds)
            ops = ch[ds]
            for t in ops.get("difference", []) or []:
                if t in cur:
                    cur.discard(t)
                    intervals.append((t, start.pop(t), day))
            for t in ops.get("union", []) or []:
                if t not in cur:
                    cur.add(t)
                    start[t] = day
    for t in cur:
        intervals.append((t, start[t], None))
    iv = pd.DataFrame(intervals, columns=["ticker", "start", "end"]).sort_values(["ticker", "start"])
    iv.to_csv(NDX_MEMBERS, index=False)
    print(len(iv), "intervals,", iv.ticker.nunique(), "tickers, current members:", len(cur))


if __name__ == "__main__":
    main(sys.argv[1])
