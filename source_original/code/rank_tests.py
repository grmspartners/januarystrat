"""
Statistical tests of the "winner effect".

1. Calendar-year test (the thread's rule): next-year excess return of ranks 1..10
   vs the equal-weight universe, with t-statistics and bootstrap confidence
   intervals of the mean.
2. Calendar-free test: at EVERY month-end, rank members by trailing 12-month
   total return and measure the following 12-month return of ranks 1..10 and
   of the equal-weight universe. Overlapping observations -> Newey-West
   (Bartlett, 11 lags) standard errors. This removes the dependence on the
   January calendar (rebalance-timing luck).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from config import OUT
import patches
from panel import Panel
from signals import ranking


def newey_west_t(x: np.ndarray, lags: int = 11) -> tuple[float, float]:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    m = x.mean()
    e = x - m
    g0 = (e @ e) / n
    s = g0
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        s += 2 * w * (e[L:] @ e[:-L]) / n
    se = math.sqrt(s / n)
    return m, m / se if se > 0 else np.nan


def boot_ci(x, n=10000, seed=3):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    ms = rng.choice(x, size=(n, len(x)), replace=True).mean(1)
    return np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def calendar_tests():
    df = pd.read_csv(OUT / "E_rank_returns.csv")
    rows = []
    for s, g in df.groupby("sample"):
        for k in range(1, 11):
            x = g[g["rank"] == k].excess.values
            lo, hi = boot_ci(x)
            t = x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))
            rows.append(dict(sample=s, rank=k, n_years=len(x), mean_excess=x.mean(), median_excess=np.median(x),
                             t_stat=t, ci95_lo=lo, ci95_hi=hi, hit_rate=(x > 0).mean(),
                             mean_next=g[g["rank"] == k].next.mean()))
        top3 = g[g["rank"] <= 3].groupby("year").excess.mean().values
        lo, hi = boot_ci(top3)
        rows.append(dict(sample=s, rank="1-3 avg", n_years=len(top3), mean_excess=top3.mean(),
                         median_excess=np.median(top3), t_stat=top3.mean() / (top3.std(ddof=1) / math.sqrt(len(top3))),
                         ci95_lo=lo, ci95_hi=hi, hit_rate=(top3 > 0).mean()))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "E_rank_tests_calendar.csv", index=False)
    return out


def monthly_overlapping(p: Panel, index="SPX", start="1996-12-31", end="2025-09-30"):
    me = p.month_end_rows()
    me = [r for r in me if pd.Timestamp(start) <= p.dates[r] <= pd.Timestamp(end)]
    all_me = p.month_end_rows()
    pos = {r: i for i, r in enumerate(all_me)}
    rows = []
    for d in me:
        i = pos[d]
        if i < 12 or i + 12 >= len(all_me):
            continue
        d0, e = all_me[i - 12], all_me[i + 12]
        rk = ranking(p, index, d, d0, min_days=126)
        # tradability at next open
        rk = rk[[p.last_row[j] >= d + 1 for j in rk.col]].reset_index(drop=True)
        nxt = np.array([p.a[min(e, p.last_row[j]), j] / p.a[d, j] - 1 for j in rk.col])
        ew = nxt.mean()
        rec = dict(date=p.dates[d], ew=ew, n=len(rk))
        for k in range(10):
            rec[f"r{k + 1}"] = nxt[k] - ew
        rec["top3"] = nxt[:3].mean() - ew
        rec["dec1"] = nxt[: max(1, len(nxt) // 10)].mean() - ew
        rows.append(rec)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"E_rank_monthly_{index}.csv", index=False)
    res = []
    for c in [f"r{k}" for k in range(1, 11)] + ["top3", "dec1"]:
        m, t = newey_west_t(df[c].values, 11)
        res.append(dict(index=index, portfolio=c, months=len(df), mean_excess_12m=m, nw_t=t,
                        median=df[c].median(), hit=(df[c] > 0).mean()))
        # by calendar month of formation
    by_month = df.assign(m=df.date.dt.month).groupby("m")[["r1", "top3", "dec1"]].mean()
    by_month.to_csv(OUT / f"E_rank_monthly_by_formation_month_{index}.csv")
    out = pd.DataFrame(res)
    out.to_csv(OUT / f"E_rank_tests_monthly_{index}.csv", index=False)
    return out, by_month


if __name__ == "__main__":
    print(calendar_tests().round(3).to_string())
    p = patches.apply(Panel.load())
    for idx, st in (("SPX", "1996-12-31"), ("SPX", "2008-12-31"), ("NDX", "2008-12-31")):
        o, bm = monthly_overlapping(p, idx, start=st)
        o["start"] = st
        o.to_csv(OUT / f"E_rank_tests_monthly_{idx}_{st[:4]}.csv", index=False)
        print(o.round(3).to_string())
        print(bm.round(3).to_string())
