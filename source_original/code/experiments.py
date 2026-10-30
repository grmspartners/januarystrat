"""
Experiment suite. Every phase writes tidy CSV files to out/ so that the
results can be audited, charted and re-run.

Run:  python experiments.py [phase ...]      (default: all phases)

Phases
------
B  replication of the original thread (gross, USD)
C  from gross to net: costs, dividend tax, capital-gains tax with the
   4-year loss carry-forward, stamp duty, EUR base; benchmarks with the
   correct ETF regime; tax-deferred ("lordista") wrapper
D  requested variants: top-N, stop levels/types, after-stop switch, shorter
   lookbacks and faster rebalancing, LEAPS, universes, tax-aware holding
E  robustness: rank-by-rank test, timing luck, bootstrap, placebo,
   leave-best-years-out, sub-periods, deflated Sharpe
F  walk-forward selection among a pre-registered grid
"""
from __future__ import annotations

import itertools
import json
import math
import sys
import time

import numpy as np
import pandas as pd

import patches
from benchmarks import run_benchmark
from config import OUT
from engine import Config, run
from metrics import annual_returns, deflated_sharpe, probabilistic_sharpe, summary
from panel import Panel
from signals import ranking, year_end_rows

OUT.mkdir(exist_ok=True)

GROSS = dict(tax_mode="none", div_tax=0.0, cost=0.0, stamp=0.0, cash_yield=False)
GROSS_COST = dict(tax_mode="none", div_tax=0.0, cost=0.001, stamp=0.0, cash_yield=True)
NET_IT = dict(tax_mode="realized", cg_tax=0.26, div_tax=0.371, cost=0.001, stamp=0.002, cash_yield=True,
              cash_tax=0.125)
DEFERRED = dict(tax_mode="deferred", cg_tax=0.26, div_tax=0.15, cost=0.001, stamp=0.002, cash_yield=True,
                cash_tax=0.0)
END = None             # headline: through the last available date (2026 year-to-date included)
END_FY = "2025-12-31"  # sensitivity: full calendar years only
LAST = "2026YTD"
PRESETS = {"gross": GROSS, "gross_cost": GROSS_COST, "net_it": NET_IT, "deferred": DEFERRED}


def rf_series(p: Panel) -> pd.Series:
    tb = pd.Series(p.tbill_3m, index=p.dates).fillna(0.0)
    days = pd.Series(p.dates, index=p.dates).diff().dt.days.fillna(1)
    return tb * days / 360.0


def row_from(res: dict, p: Panel, name: str, extra: dict | None = None) -> dict:
    s = summary(res["equity"], rf_series(p), res.get("final_after_liq"), start_capital=res.get("start", 100.0))
    out = dict(name=name, first=str(res["equity"].index[0].date()), last=str(res["equity"].index[-1].date()))
    out.update(s)
    for k in ("tax_paid", "losses_wasted", "n_stops"):
        if k in res:
            out[k] = res[k]
    if extra:
        out.update(extra)
    return out


def S(p, **kw):
    """Run a strategy, returning the result dict. Prepends the start value to the equity curve."""
    res = run(p, **kw)
    eq = res["equity"]
    d0 = p.dates[p.dates.searchsorted(eq.index[0]) - 1]
    res["equity"] = pd.concat([pd.Series({d0: kw.get("start_capital", 100.0)}), eq])
    return res


def B(p, which, first_year, regime, currency="USD", **kw):
    return run_benchmark(p, which, first_year=first_year, regime=regime, currency=currency, **kw)


# ============================================================== Phase B
def phase_B(p, pp):
    rows = []
    for fy, label in [(2012, "thread 15y (2012-2026)"), (1997, "thread 30y (1997-2026)")]:
        for stop in (None, 0.35):
            for panel_name, P in (("raw", p), ("patched", pp)):
                if fy == 2012 and panel_name == "patched":
                    continue
                for ex in (["intraday", "close"] if stop else ["-"]):
                    kw = dict(universe="SPX", first_year=fy, top_n=1, stop=stop, **GROSS)
                    if stop:
                        kw["stop_exec"] = ex
                    r = S(P, **kw)
                    rows.append(row_from(r, P, f"winner top1 stop={stop} {ex}", dict(sample=label, data=panel_name)))
        b = B(p, "SPX", fy, "none", cost=0.0, ter=0.0)
        rows.append(row_from(b, p, "S&P 500 TR (gross)", dict(sample=label, data="raw")))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "B_replication.csv", index=False)
    return df


# ============================================================== Phase C
def phase_C(p, pp):
    rows, curves = [], {}
    samples = [("core 2009-2026YTD", 2009, pp, None), ("core 2009-2025", 2009, pp, END_FY),
               ("long 1997-2026YTD", 1997, pp, None), ("long 1997-2025", 1997, pp, END_FY),
               ("thread 2012-2026YTD", 2012, pp, None)]
    for sname, fy, P, end in samples:
        for ccy in ("USD", "EUR"):
            for preset in ("gross", "gross_cost", "net_it", "deferred"):
                for stop in (None, 0.35):
                    for top in (1, 3):
                        kw = dict(universe="SPX", first_year=fy, top_n=top, stop=stop, currency=ccy, end=end,
                                  **PRESETS[preset])
                        r = S(P, **kw)
                        nm = f"SPX top{top} stop={stop} {preset}"
                        rows.append(row_from(r, P, nm, dict(sample=sname, ccy=ccy, preset=preset, kind="strategy",
                                                            top_n=top, stop=stop)))
                        curves[(sname, ccy, nm)] = r["equity"]
            for which in ("SPX",) + (("NDX",) if fy >= 2009 else ()):
                for regime in ("none", "bh", "annual", "annual_sym"):
                    b = B(p, which, fy, regime, currency=ccy, end=end,
                          **({"cost": 0.0, "ter": 0.0, "stamp": 0.0} if regime == "none" else {}))
                    nm = f"{which} ETF {regime}"
                    rows.append(row_from(b, p, nm, dict(sample=sname, ccy=ccy, preset=regime, kind="benchmark")))
                    curves[(sname, ccy, nm)] = b["equity"]
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "C_gross_to_net.csv", index=False)
    pd.to_pickle(curves, OUT / "C_curves.pkl")
    return df


# ============================================================== Phase D
def phase_D(p, pp):
    rows = []
    base = dict(universe="SPX", first_year=2009, currency="EUR", end=END, **NET_IT)

    def go(tag, P=p, **kw):
        cfg = dict(base)
        cfg.update(kw)
        t = time.time()
        r = S(P, **cfg)
        rows.append(row_from(r, P, tag, dict(cfg=json.dumps({k: v for k, v in cfg.items() if k in kw}),
                                             secs=round(time.time() - t, 2))))
        return r

    # D1 top-N x stop grid (core sample, both universes)
    for uni, fy in (("SPX", 2009), ("NDX", 2009), ("SPX+NDX", 2009), ("SPX", 1997)):
        P = pp if fy == 1997 else p
        for top in (1, 2, 3, 5, 10):
            for stop in (None, 0.15, 0.25, 0.35, 0.50):
                go(f"D1 {uni} {fy} top{top} stop{stop}", P=P, universe=uni, first_year=fy, top_n=top, stop=stop)
    # D2 stop mechanics
    for top in (1, 3):
        for ex in ("intraday", "close"):
            for st in ("entry", "trailing"):
                for lvl in (0.20, 0.35):
                    go(f"D2 top{top} {ex} {st} {lvl}", top_n=top, stop=lvl, stop_exec=ex, stop_type=st)
    # D3 after-stop behaviour
    for top in (1, 3):
        for a in ("cash", "leader"):
            go(f"D3 top{top} after={a}", top_n=top, stop=0.35, after_stop=a)
            go(f"D3 top{top} after={a} long", P=pp if top == 1 else p, first_year=1997, top_n=top, stop=0.35, after_stop=a)
    # D4 lookback / rebalancing frequency
    for lb, hold in ((12, 12), (6, 6), (6, 12), (12, 6), (12, 3), (12, 1), (6, 1), (3, 1), (1, 1)):
        for top in (1, 3, 5):
            for stop in (None, 0.35):
                go(f"D4 lb{lb} hold{hold} top{top} stop{stop}", lookback_m=lb, rebalance_m=hold, top_n=top, stop=stop)
    go("D4 12-1 hold12 top3", lookback_m=12, skip_m=1, rebalance_m=12, top_n=3, stop=0.35)
    go("D4 12-1 hold1 top3", lookback_m=12, skip_m=1, rebalance_m=1, top_n=3, stop=None)
    # D5 tax-aware holding & partial-year listings
    for top in (1, 3):
        go(f"D5 keep_winners top{top}", top_n=top, stop=0.35, keep_winners=True)
        go(f"D5 full-year only top{top}", top_n=top, stop=0.35, min_days=None)
        go(f"D5 buy at decision close top{top}", top_n=top, stop=0.35, buy_at="close")
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "D_variants.csv", index=False)
    return df


def phase_D_leaps(p, pp):
    rows = []
    base = dict(universe="SPX", first_year=2009, currency="EUR", instrument="leaps", stop=None, end=END, **NET_IT)
    for fy, P in ((2009, p), (1997, pp)):
        for top in (1, 3):
            for alloc in (0.35, 0.50, 1.0):
                for ivm in (0.9, 1.1, 1.3):
                    for hs in (0.01, 0.03, 0.06):
                        if fy == 1997 and (ivm != 1.1 or hs != 0.03):
                            continue
                        cfg = dict(base)
                        cfg.update(first_year=fy, top_n=top, leaps_alloc=alloc, leaps_iv_mult=ivm, leaps_half_spread=hs)
                        r = S(P, **cfg)
                        ev = r["events"]
                        ks = ev.loc[ev.event == "leaps_buy", "K_over_S"].mean() if len(ev) else np.nan
                        rows.append(row_from(r, P, f"LEAPS {fy} top{top} alloc{alloc} iv{ivm} hs{hs}",
                                             dict(first_year=fy, top_n=top, alloc=alloc, iv_mult=ivm, half_spread=hs,
                                                  avg_K_over_S=ks)))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "D_leaps.csv", index=False)
    return df


# ============================================================== Phase E
def phase_E_ranks(p):
    """Next-year total return of the stock ranked k by the previous calendar
    year's return, k = 1..50, and of each decile; excess vs the equal-weight
    average of all ranked members (same universe, same year)."""
    ye = year_end_rows(p)
    rows = []
    for index, y0 in (("SPX", 2008), ("NDX", 2008), ("SPX", 1996)):
        for y in range(y0, 2024 + 1):   # full next year available
            d, d0 = ye[y], ye[y - 1]
            e = ye.get(y + 1, len(p.dates) - 1)
            rk = ranking(p, index, d, d0, min_days=126)
            nxt = []
            for j in rk.col:
                ee = min(e, p.last_row[j])
                nxt.append(p.a[ee, j] / p.a[d, j] - 1 if ee > d else 0.0)
            rk["next"] = nxt
            ew = float(np.mean(nxt))
            n = len(rk)
            rk["rank"] = np.arange(1, n + 1)
            rk["decile"] = np.minimum(10, (np.arange(n) * 10 // n) + 1)
            for r in rk.itertuples():
                rows.append(dict(sample=f"{index} {y0}-2024", index=index, year=y, rank=r.rank, decile=r.decile,
                                 label=r.label, mom=r.mom, next=r.next, ew_next=ew, excess=r.next - ew))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "E_rank_returns.csv", index=False)
    return df


def phase_E_timing(p):
    """Rebalance-timing luck: the same annual rule started in each month."""
    rows = []
    for top in (1, 3):
        for stop in (None, 0.35):
            for m in range(1, 13):
                for preset in ("gross", "net_it"):
                    cfg = dict(universe="SPX", first_year=2009, first_month=m, top_n=top, stop=stop,
                               currency="EUR", end=END, **PRESETS[preset])
                    r = S(p, **cfg)
                    rows.append(row_from(r, p, f"E2 start month {m} top{top} stop{stop} {preset}",
                                         dict(start_month=m, top_n=top, stop=stop, preset=preset)))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "E_timing_luck.csv", index=False)
    return df


def phase_E_placebo(p, n_sims=400, seed=7):
    """Placebo: instead of the #1 stock, pick at random (a) one of ranks 2-10,
    (b) one random index member. Annual rule, 2009-2026, gross USD, no stop and 35% stop.
    Implemented directly on annual returns with the same stop logic re-run on
    daily data for each draw."""
    rng = np.random.default_rng(seed)
    ye = year_end_rows(p)
    years = list(range(2008, 2026))   # last holding year = 2026 YTD
    rk_cache = {}
    for y in years:     # only names that can actually be bought at the next open (same filter as the engine)
        rk = ranking(p, "SPX", ye[y], ye[y - 1], min_days=126)
        s0 = ye[y] + 1
        rk_cache[y] = rk[[p.last_row[j] >= s0 and np.isfinite(p.a[s0, j]) for j in rk.col]].reset_index(drop=True)

    def hold_ret(j, y, stop):
        s = ye[y] + 1
        e = ye.get(y + 1, len(p.dates) - 1)
        e2 = min(e, p.last_row[j])
        entry = p.ao[s, j] if np.isfinite(p.ao[s, j]) else p.a[s, j]
        if stop:
            lvl = entry * (1 - stop)
            lows = p.al[s:e2 + 1, j]
            hit = np.where(lows <= lvl)[0]
            if len(hit):
                t = s + hit[0]
                op = p.ao[t, j]
                fill = op if (np.isfinite(op) and op <= lvl and t != s) else lvl
                return fill / entry - 1
        return p.a[e2, j] / entry - 1

    out = []
    for stop in (None, 0.35):
        actual = np.prod([1 + hold_ret(rk_cache[y].col.iloc[0], y, stop) for y in years])
        for kind in ("rank2-10", "random member", "rank1-3 random"):
            finals = []
            for _ in range(n_sims):
                w = 1.0
                for y in years:
                    rk = rk_cache[y]
                    if kind == "rank2-10":
                        j = rk.col.iloc[rng.integers(1, 10)]
                    elif kind == "rank1-3 random":
                        j = rk.col.iloc[rng.integers(0, 3)]
                    else:
                        j = rk.col.iloc[rng.integers(0, len(rk))]
                    w *= 1 + hold_ret(j, y, stop)
                finals.append(w)
            finals = np.array(finals)
            out.append(dict(stop=stop, placebo=kind, actual_multiple=actual, median_multiple=np.median(finals),
                            p10=np.percentile(finals, 10), p90=np.percentile(finals, 90),
                            pct_placebo_beating_actual=(finals >= actual).mean()))
    df = pd.DataFrame(out)
    df.to_csv(OUT / "E_placebo.csv", index=False)
    return df


def phase_E_bootstrap(p, pp, n_sims=5000, seed=11):
    """Stationary bootstrap of ANNUAL net returns (strategy and benchmark drawn
    jointly, same years) -> distribution of 10y and 20y outcomes."""
    rng = np.random.default_rng(seed)
    rows = []
    for sname, fy, P in (("core 2009-2025", 2009, pp), ("long 1997-2025", 1997, pp)):
        for top, stop in ((1, None), (1, 0.35), (3, None), (3, 0.35)):
            r = S(P, universe="SPX", first_year=fy, top_n=top, stop=stop, currency="EUR", end=END_FY, **NET_IT)
            b = B(p, "SPX", fy, "bh", currency="EUR", end=END_FY)
            sa = annual_returns(r["equity"])
            ba = annual_returns(b["equity"])
            idx = sa.index.intersection(ba.index)
            idx = idx[idx <= 2025]
            sa, ba = sa.loc[idx].values, ba.loc[idx].values
            for H in (10, 20):
                sw, bw = [], []
                for _ in range(n_sims):
                    k = rng.integers(0, len(sa), H)
                    sw.append(np.prod(1 + sa[k]))
                    bw.append(np.prod(1 + ba[k]))
                sw, bw = np.array(sw), np.array(bw)
                rows.append(dict(sample=sname, top_n=top, stop=stop, horizon=H,
                                 strat_median=np.median(sw), strat_p05=np.percentile(sw, 5),
                                 strat_p95=np.percentile(sw, 95), bench_median=np.median(bw),
                                 p_strat_below_bench=(sw < bw).mean(), p_strat_loss=(sw < 1).mean(),
                                 p_strat_halved=(sw < 0.5).mean()))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "E_bootstrap.csv", index=False)
    return df


def phase_E_concentration(p, pp):
    """How much of the terminal wealth comes from the best years?"""
    rows = []
    for sname, fy, P in (("core 2009-2026YTD", 2009, pp), ("long 1997-2026YTD", 1997, pp)):
        for top, stop in ((1, None), (1, 0.35), (3, 0.35)):
            r = S(P, universe="SPX", first_year=fy, top_n=top, stop=stop, end=END, **GROSS)
            ar = annual_returns(r["equity"]).sort_values(ascending=False)
            full = float(np.prod(1 + ar))
            for k in (0, 1, 2, 3, 5):
                rest = ar.iloc[k:]
                rows.append(dict(sample=sname, top_n=top, stop=stop, removed_best=k,
                                 removed_years=",".join(map(str, ar.index[:k])),
                                 multiple=float(np.prod(1 + rest)), share_of_full=float(np.prod(1 + rest)) / full,
                                 cagr=float(np.prod(1 + rest)) ** (1 / len(ar)) - 1))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "E_concentration.csv", index=False)
    return df


# ============================================================== Phase F
GRID = dict(top_n=(1, 3, 5), stop=(None, 0.25, 0.35, 0.50), lookback_m=(6, 12), rebalance_m=(6, 12),
            after_stop=("cash", "leader"))


def phase_F(p):
    """Walk-forward: every January from 2014, choose the configuration with the
    best trailing Calmar (net EUR) on all data since 2009 that would have been
    known, hold it for the year. Compare with fixed baseline (thread rule)."""
    combos = [dict(zip(GRID, v)) for v in itertools.product(*GRID.values())]
    combos = [c for c in combos if not (c["stop"] is None and c["after_stop"] == "leader")]
    curves = {}
    rows = []
    for c in combos:
        tag = json.dumps(c)
        r = S(p, universe="SPX", first_year=2009, currency="EUR", end=END, **NET_IT, **c)
        curves[tag] = r["equity"]
        rows.append(row_from(r, p, tag, c))
    full = pd.DataFrame(rows)
    full.to_csv(OUT / "F_grid_full_sample.csv", index=False)
    # daily returns matrix
    R = pd.DataFrame({k: v.pct_change() for k, v in curves.items()}).dropna(how="all")
    wf = []
    for y in range(2014, 2027):
        past = R.loc[: f"{y - 1}-12-31"]
        eqp = (1 + past.fillna(0)).cumprod()
        cagr = eqp.iloc[-1] ** (252 / len(eqp)) - 1
        mdd = (eqp / eqp.cummax() - 1).min()
        calmar = cagr / mdd.abs()
        best = calmar.idxmax()
        nxt = R.loc[f"{y}-01-01": f"{y}-12-31", best]
        wf.append(dict(year=y, chosen=best, ret=float((1 + nxt.fillna(0)).prod() - 1)))
    wf = pd.DataFrame(wf)
    wf.to_csv(OUT / "F_walkforward.csv", index=False)
    # deflated Sharpe of the best in-sample configuration
    daily_sr = (R.mean() / R.std())
    best = daily_sr.idxmax()
    rb = R[best].dropna()
    dsr = deflated_sharpe(float(daily_sr[best]), len(rb), float(rb.skew()), float(rb.kurt()), daily_sr.values)
    psr = probabilistic_sharpe(float(daily_sr[best]), len(rb), float(rb.skew()), float(rb.kurt()), 0.0)
    json.dump(dict(n_trials=len(combos), best=best, best_sharpe_ann=float(daily_sr[best] * math.sqrt(252)),
                   psr_vs_zero=psr, dsr=dsr), open(OUT / "F_deflated_sharpe.json", "w"), indent=1)
    return full, wf


if __name__ == "__main__":
    phases = sys.argv[1:] or ["B", "C", "D", "DL", "E", "F"]
    t0 = time.time()
    p_raw = Panel.load()
    pp = patches.apply(Panel.load())
    p = pp      # every analysis runs on the survivorship-patched panel
    if "B" in phases:
        print(phase_B(p_raw, pp)[["name", "sample", "data", "final", "cagr", "max_dd"]].to_string()); sys.stdout.flush()
    if "C" in phases:
        phase_C(p, pp); print("C done", round(time.time() - t0)); sys.stdout.flush()
    if "D" in phases:
        phase_D(p, pp); print("D done", round(time.time() - t0)); sys.stdout.flush()
    if "DL" in phases:
        phase_D_leaps(p, pp); print("DL done", round(time.time() - t0)); sys.stdout.flush()
    if "E" in phases:
        phase_E_ranks(p); phase_E_timing(p); phase_E_placebo(p); phase_E_bootstrap(p, pp); phase_E_concentration(p, pp)
        print("E done", round(time.time() - t0)); sys.stdout.flush()
    if "F" in phases:
        phase_F(p); print("F done", round(time.time() - t0))
