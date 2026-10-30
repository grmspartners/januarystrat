"""
Deliverable 1: top-3 performers of every calendar year since 1990, S&P 500 and
Nasdaq-100, with the year's total return, the next year's total return and a
data-quality flag for every year.

Quality flags
-------------
A  point-in-time membership, price coverage >= 95% of members, top names
   cross-checked where a published list exists
B  point-in-time membership, coverage 75-95%: top names cross-checked against
   published year-end lists; known missing winners listed in `missing_known`
C  point-in-time membership, coverage < 75%: same treatment as B, lower confidence
P  PROXY universe (no point-in-time membership available for free): members
   of a later date with available data -> survivorship-biased, indicative only
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import OUT
from panel import Panel
from signals import ranking, year_end_rows

# Winners missing from the free price data. "patched" = reinserted as a reconstructed series
# from SEC filings (see patches.py); "still missing" = known member below the top-3 not reinserted.
KNOWN_MISSING = {
    ("SPX", 1999): "patched: Sprint PCS +343% (#2), Nextel +337% (#3). Still missing below top-3: LSI Logic +319%, "
                   "Nortel +304% (not in the point-in-time membership file)",
    ("SPX", 2000): "patched: Reebok +234% (#1, S&P DJI price return), Dynegy +220% (#2, proxy TSR)",
    ("SPX", 2002): "patched: Providian +82.8% (#1, proxy TSR)",
    ("SPX", 2003): "patched: Avaya +428% (#1), Dynegy +263% (#3). Still missing below top-3: Novell +215%",
    ("SPX", 2004): "patched: TXU +178% (#3)",
    ("SPX", 2008): "patched: UST Inc. +26.6% (#2, cash-out 6-Jan-2009)",
}
VERIFIED = {
    ("SPX", 1997): "S&P DJI: Dell 216%", ("SPX", 1998): "S&P DJI: Dell 248%",
    ("SPX", 1999): "S&P DJI: Qualcomm 2,620%; Sprint PCS / Nextel proxy TSR tables",
    ("SPX", 2000): "S&P DJI: Reebok 234%; Dynegy proxy TSR 220%",
    ("SPX", 2001): "Plansponsor/Instinet: NVIDIA 308%, Office Depot 160%",
    ("SPX", 2002): "Providian proxy TSR 82.8%",
    ("SPX", 2003): "Forbes / S&P DJI: Avaya 428%; Dynegy proxy TSR 263%",
    ("SPX", 2004): "CNN: Autodesk 214%, Apple 200%, TXU 176% (price)",
    ("SPX", 2005): "CNN: Apple, Valero, Express Scripts", ("SPX", 2007): "CNN: NOV biggest S&P gainer",
    ("SPX", 2008): "CNN: Family Dollar 38.5%, UST 26.6%", ("SPX", 2009): "S&P DJI: XL Capital 395% (price)",
    ("SPX", 2010): "S&P DJI: Netflix 219%", ("SPX", 2013): "S&P DJI: Netflix 298%", ("SPX", 2016): "S&P DJI: NVIDIA 224% (price)",
    ("SPX", 2020): "S&P DJI: Tesla 743%",
}


def coverage(p: Panel, index: str, d_row: int, d0_row: int) -> float:
    n_all = p.members_count(index, p.dates[d_row])
    if index == "SPX":   # reconstructed series duplicate an existing membership row: do not double count
        m = p.spx[p.spx.ticker.str.startswith("PATCH_")]
        dd = p.dates[d_row]
        n_all -= int(((m.start <= dd) & (m.end.isna() | (m.end > dd))).sum())
    n_ok = len(ranking(p, index, d_row, d0_row, min_days=None))
    return n_ok / n_all if n_all else np.nan


def build(p: Panel) -> pd.DataFrame:
    ye = year_end_rows(p)
    rows = []
    for index, pit_start in (("SPX", 1996), ("NDX", 2007)):
        for y in range(1990, 2027):          # 2026 = year to date
            d, d0 = ye[y], ye[y - 1]
            if y >= pit_start:
                rk = ranking(p, index, d, d0, min_days=126)
                cov = coverage(p, index, d, d0)
                flag = "A" if cov >= 0.95 else ("B" if cov >= 0.75 else "C")
                universe = "point-in-time"
            else:
                # proxy: members on the first point-in-time date, with prices in year y
                proxy_date = p.dates[ye[pit_start - 1] + 1]
                cols = p.members(index, proxy_date)
                rk = ranking(p, index, d, d0, min_days=126, cols=cols)
                cov, flag, universe = np.nan, "P", f"proxy: members on {proxy_date.date()}"
            nxt_end = ye.get(y + 1, len(p.dates) - 1)
            for k, r in enumerate(rk.head(3).itertuples(), start=1):
                j = r.col
                e = min(nxt_end, p.last_row[j])
                nxt = p.a[e, j] / p.a[d, j] - 1 if e > d else np.nan
                if y == p.dates[-1].year:
                    nxt = np.nan
                rows.append(dict(index=index, year=y, rank=k, label=r.label, total_return=r.mom,
                                 partial_year=r.partial, next_year_return=nxt,
                                 next_year_to=str(p.dates[e].date()), n_ranked=len(rk),
                                 coverage=cov, quality=flag, universe=universe,
                                 verified=VERIFIED.get((index, y), ""),
                                 missing_known=KNOWN_MISSING.get((index, y), "")))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import patches
    p = patches.apply(Panel.load())
    df = build(p)
    OUT.mkdir(exist_ok=True)
    df.to_csv(OUT / "top3_by_year.csv", index=False)
    print(df.groupby(["index", "quality"]).year.nunique())
