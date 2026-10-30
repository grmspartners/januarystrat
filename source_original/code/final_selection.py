"""
Final selection of the strategy - declared criterion, 12-tranche basis.

Why 12 tranches: the annual rule started in January is one draw out of twelve
possible start months; results move by several points of CAGR with the start
month alone (rebalance-timing luck). A portfolio of 12 sleeves, each following
the same annual rule but rebalancing in a different month, removes that luck and
is also how a family office would implement the rule in practice (1/12 of the
capital rebalanced every month).

Grid (48 configurations, all already in the families tested in phases D and G):
    top_n         1, 2, 3, 5
    stop          none, 35%, 50% below entry
    regime        none, S&P 500 TR above its 10-month average
    keep_winners  no, yes (tax deferral: a name selected again is not sold)
All runs: S&P 500 point-in-time universe with the survivorship patches,
investor resident in Italy, EUR, 26% capital-gains tax with 4-year loss carry,
37.1% on dividends, 0.20% stamp duty, 10 bps costs per side, cash in T-bills
taxed at 12.5%, final value after the tax due on liquidation.

Four views: core sample (2009 -> 9-Oct-2026), long sample (1997 -> 9-Oct-2026),
and the same two ending 31-Dec-2025 (to show the weight of the 2026 outlier).

Declared criterion
    1. eligibility: max drawdown of the 12-tranche portfolio not worse than
       -50% in the core sample and -55% in the long sample;
    2. score = the WORST of the four views of
       (12-tranche net CAGR - 12-tranche net CAGR of the S&P 500 ETF buy & hold);
    3. the configuration with the highest score wins; the S&P 500 ETF wins if no
       configuration has a positive score.
"""
from __future__ import annotations

import itertools
import json
import math
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

import patches
from benchmarks import run_benchmark
from config import OUT
from engine import run
from experiments import NET_IT
from metrics import deflated_sharpe, probabilistic_sharpe
from panel import Panel
from signals import ranking, year_end_rows

GRID = dict(top_n=(1, 2, 3, 5), stop=(None, 0.35, 0.50), regime_filter=(None, "sma10"), keep_winners=(False, True))
VIEWS = {"core": (2009, None), "long": (1997, None), "core_fy": (2009, "2025-12-31"), "long_fy": (1997, "2025-12-31")}
DD_LIMIT = {"core": -0.50, "long": -0.55, "core_fy": -0.50, "long_fy": -0.55}
_P = None


def cfg_name(c: dict) -> str:
    s = f"top{c['top_n']}"
    s += f" stop{int(c['stop'] * 100)}" if c["stop"] else " nostop"
    s += " regime" if c["regime_filter"] else ""
    s += " keep" if c["keep_winners"] else ""
    return s


def _init():
    global _P
    _P = patches.apply(Panel.load())


def _one(args):
    name, c, view, m = args
    fy, end = VIEWS[view]
    r = run(_P, universe="SPX", first_year=fy, first_month=m, currency="EUR", end=end, **NET_IT, **c)
    eq = r["equity"]
    return name, view, m, eq, r["final_after_liq"]


def tranche(eqs: list[pd.Series], afters: list[float], start: pd.Timestamp):
    """Equal-weight portfolio of 12 sleeves of 100/12 each; a sleeve not yet started holds cash at 0%."""
    idx = sorted(set().union(*[e.index for e in eqs]))
    M = pd.DataFrame({i: e.reindex(idx) for i, e in enumerate(eqs)}).bfill().ffill()
    port = M.mean(axis=1)
    port = pd.concat([pd.Series({start: 100.0}), port])
    after = float(np.mean(afters))
    years = (port.index[-1] - port.index[0]).days / 365.25
    cagr = (after / 100.0) ** (1 / years) - 1
    dd = float((port / port.cummax() - 1).min())
    return port, cagr, dd, after


def bench_tranche(p, fy, end):
    """S&P 500 UCITS ETF buy & hold, 12 sleeves entering in month 1..12 of the first year, 26% tax at the end."""
    b = run_benchmark(p, "SPX", first_year=fy, regime="bh", currency="EUR", end=end)
    eq = b["equity"]
    month_first = eq.groupby([eq.index.year, eq.index.month]).head(1)
    starts = [d for d in month_first.index if d.year == fy][:12]
    sleeves, afters = [], []
    for s in starts:
        i = eq.index.get_loc(s)
        base = eq.iloc[i - 1] if i > 0 else 100.0
        sl = 100.0 * eq / base
        sl[eq.index < s] = 100.0
        sleeves.append(sl)
        g = sl.iloc[-1] - 100.0
        afters.append(100.0 + g - 0.26 * max(g, 0.0))
    start = eq.index[0]
    port, cagr, dd, after = tranche(sleeves, afters, start)
    return port, cagr, dd, after, b


def main(quick=False):
    t0 = time.time()
    p = patches.apply(Panel.load())
    combos = [dict(zip(GRID, v)) for v in itertools.product(*GRID.values())]
    jobs = [(cfg_name(c), c, v, m) for c in combos for v in VIEWS for m in range(1, 13)]
    if quick:
        jobs = jobs[:24]
    print(len(combos), "configurations,", len(jobs), "backtests", flush=True)
    res = {}
    with Pool(2, initializer=_init) as pool:
        for k, (name, view, m, eq, after) in enumerate(pool.imap_unordered(_one, jobs, chunksize=4)):
            res[(name, view, m)] = (eq, after)
            if k % 200 == 0:
                print(k, round(time.time() - t0), flush=True)
    pd.to_pickle(res, OUT / "FS_raw_runs.pkl")

    # ---- benchmarks
    bench = {}
    for view, (fy, end) in VIEWS.items():
        port, cagr, dd, after, b = bench_tranche(p, fy, end)
        bench[view] = dict(port=port, cagr=cagr, dd=dd, after=after)

    # ---- tranche portfolios and scores
    rows, ports = [], {}
    for c in combos:
        name = cfg_name(c)
        rec = dict(config=name, **{k: (v if v is not None else "none") for k, v in c.items()})
        ok = True
        exc = []
        for view, (fy, end) in VIEWS.items():
            if (name, view, 1) not in res:
                ok = False
                continue
            eqs = [res[(name, view, m)][0] for m in range(1, 13)]
            afts = [res[(name, view, m)][1] for m in range(1, 13)]
            start = bench[view]["port"].index[0]
            port, cagr, dd, after = tranche(eqs, afts, start)
            ports[(name, view)] = port
            single = []
            for m in range(1, 13):
                e = res[(name, view, m)]
                yrs = (e[0].index[-1] - e[0].index[0]).days / 365.25
                single.append((e[1] / 100.0) ** (1 / yrs) - 1)
            rec[f"{view}_cagr"] = cagr
            rec[f"{view}_excess"] = cagr - bench[view]["cagr"]
            rec[f"{view}_maxdd"] = dd
            rec[f"{view}_final"] = after
            rec[f"{view}_jan_cagr"] = single[0]
            rec[f"{view}_worst_month_cagr"] = min(single)
            rec[f"{view}_best_month_cagr"] = max(single)
            exc.append(cagr - bench[view]["cagr"])
            if dd < DD_LIMIT[view]:
                ok = False
        rec["eligible"] = ok and len(exc) == 4
        rec["score_worst_excess"] = min(exc) if exc else np.nan
        rows.append(rec)
    tab = pd.DataFrame(rows).sort_values(["eligible", "score_worst_excess"], ascending=[False, False])
    tab.to_csv(OUT / "FS_grid_tranche.csv", index=False)
    brow = pd.DataFrame([dict(view=v, cagr=b["cagr"], maxdd=b["dd"], final=b["after"]) for v, b in bench.items()])
    brow.to_csv(OUT / "FS_benchmark_tranche.csv", index=False)
    pd.to_pickle(dict(ports=ports, bench={k: v["port"] for k, v in bench.items()}), OUT / "FS_tranche_curves.pkl")

    winner = tab.iloc[0]
    if not (winner.eligible and winner.score_worst_excess > 0):
        winner_name = "S&P 500 ETF"
    else:
        winner_name = winner.config
    print("winner:", winner_name, flush=True)

    # ---- deflated Sharpe across the 48 trials (long view, daily returns of the tranche portfolios)
    R = pd.DataFrame({n: ports[(n, "long")].pct_change() for n in tab.config if (n, "long") in ports}).dropna(how="all")
    sr = R.mean() / R.std()
    w = winner.config
    rb = R[w].dropna()
    dsr = deflated_sharpe(float(sr[w]), len(rb), float(rb.skew()), float(rb.kurt()), sr.values)
    psr = probabilistic_sharpe(float(sr[w]), len(rb), float(rb.skew()), float(rb.kurt()), 0.0)
    rbm = bench["long"]["port"].pct_change().dropna()
    sr_b = float(rbm.mean() / rbm.std())
    psr_vs_bench = probabilistic_sharpe(float(sr[w]), len(rb), float(rb.skew()), float(rb.kurt()), sr_b)

    # ---- walk-forward on the long view: each January from 2007 choose the configuration with the best
    # trailing worst-case excess (trailing core = since 2009 when available, trailing long = since 1997),
    # subject to the drawdown limit, hold it for the calendar year.
    wf = []
    Rb = bench["long"]["port"].pct_change()
    for y in range(2007, 2027):
        past = R.loc[: f"{y - 1}-12-31"]
        eqp = (1 + past.fillna(0)).cumprod()
        yrs = len(eqp) / 252
        cg = eqp.iloc[-1] ** (1 / yrs) - 1
        bpast = (1 + Rb.loc[: f"{y - 1}-12-31"].fillna(0)).cumprod()
        bcg = bpast.iloc[-1] ** (1 / yrs) - 1
        mdd = (eqp / eqp.cummax() - 1).min()
        sc = (cg - bcg).where(mdd >= DD_LIMIT["long"], -np.inf)
        best = sc.idxmax()
        if not np.isfinite(sc[best]) or sc[best] <= 0:
            best = "S&P 500 ETF"
            nxt = Rb.loc[f"{y}-01-01": f"{y}-12-31"]
        else:
            nxt = R.loc[f"{y}-01-01": f"{y}-12-31", best]
        wf.append(dict(year=y, chosen=best, ret=float((1 + nxt.fillna(0)).prod() - 1),
                       winner_fixed=float((1 + R.loc[f"{y}-01-01": f"{y}-12-31", w].fillna(0)).prod() - 1),
                       etf=float((1 + Rb.loc[f"{y}-01-01": f"{y}-12-31"].fillna(0)).prod() - 1)))
    wf = pd.DataFrame(wf)
    wf.to_csv(OUT / "FS_walkforward.csv", index=False)
    summ = dict(n_trials=len(combos), winner=winner_name, winner_score=float(winner.score_worst_excess),
                dsr=float(dsr), psr_vs_zero=float(psr), psr_vs_etf=float(psr_vs_bench),
                ann_sharpe_winner=float(sr[w] * math.sqrt(252)), ann_sharpe_etf=float(sr_b * math.sqrt(252)),
                wf_cagr=float((1 + wf.ret).prod() ** (1 / len(wf)) - 1),
                wf_fixed_cagr=float((1 + wf.winner_fixed).prod() ** (1 / len(wf)) - 1),
                wf_etf_cagr=float((1 + wf.etf).prod() ** (1 / len(wf)) - 1), seconds=round(time.time() - t0))
    json.dump(summ, open(OUT / "FS_summary.json", "w"), indent=1)
    print(json.dumps(summ, indent=1))
    cols = ["config", "eligible", "score_worst_excess"] + [f"{v}_{k}" for v in VIEWS for k in ("cagr", "maxdd")]
    print(tab[cols].head(15).round(3).to_string())
    print(brow.round(3).to_string())


if __name__ == "__main__":
    main(quick="--quick" in sys.argv)
