"""
Final decision, built on the 48-configuration tranche grid of final_selection.py.

1. Sleeve statistics: for every configuration and view, the 12 single-start-month
   outcomes (median, worst, share of start months beating the ETF).
2. Protocol revision (declared in the report): the absolute drawdown limits of
   final_selection.py (-50% core, -55% long) are violated by the S&P 500 ETF itself
   in the long sample (-65%), so they cannot separate "strategy" from "market",
   and no family office would hold a single-stock momentum rule as its whole
   equity allocation. The decision is therefore taken on ETF-core + satellite
   portfolios (no rebalancing between the two sleeves: tax efficient):
     a) for every one of the 48 rules and every satellite weight (5% steps),
        compute the worst-of-four-views excess CAGR over the ETF and the worst
        drawdown gap versus the ETF;
     b) admissible = drawdown not worse than the ETF's own by more than 5
        percentage points in ANY view (risk budget);
     c) the admissible (rule, weight) pair with the highest worst-view excess
        defines the satellite rule and the MAXIMUM weight;
     d) recommended weight = half of the maximum (rounded down to 5%), to allow
        for estimation error in the backtested edge (the edge is not
        statistically certain: see PSR versus the ETF).
3. Walk-forward: each January (2007-2026) pick the configuration with the best
   trailing excess over the ETF on the long tranche curves; hold it one year.
4. Current signals at the last date of the data.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import patches
from benchmarks import run_benchmark
from config import OUT
from engine import run
from experiments import NET_IT
from final_selection import VIEWS
from metrics import annual_returns, deflated_sharpe, probabilistic_sharpe
from names import company
from panel import Panel
from signals import ranking, year_end_rows

DD_TOL = 0.05
WEIGHTS = [round(x, 2) for x in np.arange(0, 1.0001, 0.05)]


def etf_sleeves(p):
    out = {}
    for view, (fy, end) in VIEWS.items():
        b = run_benchmark(p, "SPX", first_year=fy, regime="bh", currency="EUR", end=end)
        eq = b["equity"]
        mf = eq.groupby([eq.index.year, eq.index.month]).head(1)
        starts = [d for d in mf.index if d.year == fy][:12]
        c = []
        for s in starts:
            i = eq.index.get_loc(s)
            base = eq.iloc[i - 1] if i > 0 else 100.0
            g = 100 * eq.iloc[-1] / base - 100
            after = 100 + g - 0.26 * max(g, 0)
            yrs = (eq.index[-1] - eq.index[max(i - 1, 0)]).days / 365.25
            c.append((after / 100) ** (1 / yrs) - 1)
        out[view] = np.array(c)
    return out


def main():
    p = patches.apply(Panel.load())
    res = pd.read_pickle(OUT / "FS_raw_runs.pkl")
    grid = pd.read_csv(OUT / "FS_grid_tranche.csv").set_index("config")
    bench = pd.read_csv(OUT / "FS_benchmark_tranche.csv").set_index("view")
    cur = pd.read_pickle(OUT / "FS_tranche_curves.pkl")
    ports, bcur = cur["ports"], cur["bench"]

    # ---- 1. sleeve statistics
    es = etf_sleeves(p)
    rows = []
    for n in grid.index:
        rec = {"config": n}
        for v in VIEWS:
            c = []
            for m in range(1, 13):
                eq, after = res[(n, v, m)]
                yrs = (eq.index[-1] - eq.index[0]).days / 365.25
                c.append((after / 100) ** (1 / yrs) - 1)
            c = np.array(c)
            ex = c - es[v]
            for m in range(12):
                rec[f"{v}_m{m + 1:02d}"] = c[m]
            rec[f"{v}_median"] = np.median(c)
            rec[f"{v}_median_excess"] = np.median(ex)
            rec[f"{v}_worst"] = c.min()
            rec[f"{v}_best"] = c.max()
            rec[f"{v}_share_beating_etf"] = (ex > 0).mean()
        rows.append(rec)
    sleeves = pd.DataFrame(rows).set_index("config")
    sleeves.to_csv(OUT / "FD_sleeves.csv")
    etf_sl = pd.DataFrame({v: es[v] for v in VIEWS}, index=[f"m{m:02d}" for m in range(1, 13)])
    etf_sl.to_csv(OUT / "FD_etf_sleeves.csv")

    # ---- 2. joint choice of satellite rule and weight under the risk budget
    cs_rows = []
    for cfg in grid.index:
        for w in WEIGHTS:
            rec = {"config": cfg, "weight_satellite": w}
            for v in VIEWS:
                s, e = ports[(cfg, v)], bcur[v]
                idx = s.index.intersection(e.index)
                mix = (1 - w) * e.loc[idx] / e.loc[idx].iloc[0] * 100 + w * s.loc[idx] / s.loc[idx].iloc[0] * 100
                after = (1 - w) * bench.loc[v, "final"] + w * grid.loc[cfg, f"{v}_final"]
                yrs = (idx[-1] - idx[0]).days / 365.25
                cg = (after / 100) ** (1 / yrs) - 1
                dd = float((mix / mix.cummax() - 1).min())
                rec.update({f"{v}_cagr": cg, f"{v}_excess": cg - bench.loc[v, "cagr"], f"{v}_maxdd": dd,
                            f"{v}_dd_gap": dd - bench.loc[v, "maxdd"], f"{v}_final": after})
            rec["worst_excess"] = min(rec[f"{v}_excess"] for v in VIEWS)
            rec["worst_dd_gap"] = min(rec[f"{v}_dd_gap"] for v in VIEWS)
            rec["within_risk_budget"] = rec["worst_dd_gap"] >= -DD_TOL - 1e-9
            cs_rows.append(rec)
    cs = pd.DataFrame(cs_rows)
    cs.to_csv(OUT / "FD_core_satellite.csv", index=False)
    adm = cs[cs.within_risk_budget & (cs.weight_satellite > 0)].sort_values("worst_excess", ascending=False)
    best = adm.iloc[0]
    sat, w_max = best.config, float(best.weight_satellite)
    w_rec = round(float(np.floor(w_max / 2 / 0.05 + 1e-9) * 0.05), 2)
    frontier = adm.groupby("config").head(1).head(20)
    frontier.to_csv(OUT / "FD_frontier.csv", index=False)

    # ---- 3. walk-forward on the long tranche curves
    R = pd.DataFrame({n: ports[(n, "long")].pct_change() for n in grid.index}).dropna(how="all")
    Rb = bcur["long"].pct_change()
    wf = []
    for y in range(2007, 2027):
        past = R.loc[: f"{y - 1}-12-31"].fillna(0)
        yrs = len(past) / 252
        cg = (1 + past).prod() ** (1 / yrs) - 1
        bcg = (1 + Rb.loc[: f"{y - 1}-12-31"].fillna(0)).prod() ** (1 / yrs) - 1
        best = (cg - bcg).idxmax()
        nxt = R.loc[f"{y}-01-01": f"{y}-12-31", best]
        wf.append(dict(anno=y, scelta_walk_forward=best, rendimento_scelta=float((1 + nxt.fillna(0)).prod() - 1),
                       rendimento_regola_scelta=float((1 + R.loc[f"{y}-01-01": f"{y}-12-31", sat].fillna(0)).prod() - 1),
                       rendimento_etf=float((1 + Rb.loc[f"{y}-01-01": f"{y}-12-31"].fillna(0)).prod() - 1)))
    wf = pd.DataFrame(wf)
    wf.to_csv(OUT / "FD_walkforward.csv", index=False)

    sr = R.mean() / R.std()
    rb = R[sat].dropna()
    dsr = deflated_sharpe(float(sr[sat]), len(rb), float(rb.skew()), float(rb.kurt()), sr.values)
    rbe = Rb.dropna()
    sr_b = float(rbe.mean() / rbe.std())
    psr_b = probabilistic_sharpe(float(sr[sat]), len(rb), float(rb.skew()), float(rb.kurt()), sr_b)

    # ---- annual returns of satellite, ETF and the recommended mix (core view and long view)
    ann = {}
    for v in ("core", "long"):
        s, e = ports[(sat, v)], bcur[v]
        idx = s.index.intersection(e.index)
        for w in (w_max, w_rec):
            mix = (1 - w) * e.loc[idx] / e.loc[idx].iloc[0] + w * s.loc[idx] / s.loc[idx].iloc[0]
            ann[(v, f"mix {int(w * 100)}% satellite")] = annual_returns(mix)
        ann[(v, "satellite 12 tranches")] = annual_returns(s)
        ann[(v, "S&P 500 ETF")] = annual_returns(e)
        eq, _ = res[(sat, v, 1)]
        ann[(v, "satellite January only")] = annual_returns(eq)
    annual = pd.DataFrame(ann)
    annual.to_csv(OUT / "FD_annual.csv")

    # ---- 4. current signals
    c = grid.loc[sat]
    kw = dict(top_n=int(c.top_n), stop=(None if c.stop == "none" else float(c.stop)),
              regime_filter=(None if c.regime_filter == "none" else c.regime_filter),
              keep_winners=bool(c.keep_winners))
    sig_rows, trade_logs, tax_logs = [], [], []
    last = len(p.dates) - 1
    for m in range(1, 13):
        r = run(p, universe="SPX", first_year=2009, first_month=m, currency="EUR", **NET_IT, **kw)
        h = r["holdings"].iloc[-1]
        t = r["trades"].assign(tranche=m)
        trade_logs.append(t)
        tax_logs.append(r["tax_history"].assign(tranche=m))
        for lab in h.selected:
            j = p.lab_idx[lab]
            ent = p.row(h.period_start)
            entry_px = p.ao[ent, j] if np.isfinite(p.ao[ent, j]) else p.a[ent, j]
            low = np.nanmin(p.al[ent:last + 1, j])
            stop_lvl = entry_px * (1 - kw["stop"]) if kw["stop"] else np.nan
            stopped = bool(kw["stop"]) and low <= stop_lvl
            sig_rows.append(dict(tranche=m, periodo_dal=h.period_start, periodo_al=h.period_end, ticker=lab,
                                 societa=company(lab), momentum_alla_selezione=h.moms[list(h.selected).index(lab)],
                                 prezzo_ingresso_adj=entry_px, livello_stop_adj=stop_lvl,
                                 prezzo_9ott2026_adj=p.a[last, j], rendimento_da_ingresso=p.a[last, j] / entry_px - 1,
                                 stop_toccato=stopped,
                                 stato=("in liquidita (stop)" if stopped else "investito")))
    sig = pd.DataFrame(sig_rows)
    sig.to_csv(OUT / "FD_segnali_tranche.csv", index=False)
    pd.concat(trade_logs).to_csv(OUT / "FD_trade_log_tranche.csv", index=False)
    pd.concat(tax_logs).to_csv(OUT / "FD_zainetto_tranche.csv", index=False)

    ye = year_end_rows(p)
    rk = ranking(p, "SPX", last, ye[2025], min_days=126).head(15)
    rk["societa"] = rk.label.map(company)
    rk.to_csv(OUT / "FD_classifica_2026YTD.csv", index=False)
    me = p.month_end_rows()
    me_last = me[me <= last][-1] if p.dates[last].month != p.dates[me[me <= last][-1]].month else me[me <= last][-2]
    i = list(me).index(me_last)
    rk12 = ranking(p, "SPX", me_last, me[i - 12], min_days=126).head(15)
    rk12["societa"] = rk12.label.map(company)
    rk12["data_classifica"] = p.dates[me_last].date()
    rk12.to_csv(OUT / "FD_classifica_12m.csv", index=False)

    # regime (informative)
    from benchmarks import index_tr
    tr = index_tr(p, "SPX").reindex(p.dates)
    mtr = tr.iloc[me]
    sma10 = mtr.rolling(10).mean()
    regime = dict(date=str(mtr.index[-1].date()), sp500tr=float(mtr.iloc[-1]), sma10=float(sma10.iloc[-1]),
                  risk_on=bool(mtr.iloc[-1] > sma10.iloc[-1]))

    dec = dict(satellite_rule=sat, satellite_kwargs=kw, weight_cap=w_max, weight_recommended=w_rec,
               rule_best_standalone=grid["score_worst_excess"].idxmax(),
               dd_tolerance_pp=DD_TOL * 100, dsr_48_trials=float(dsr), psr_vs_etf=float(psr_b),
               sharpe_satellite_long=float(sr[sat] * np.sqrt(252)), sharpe_etf_long=float(sr_b * np.sqrt(252)),
               wf_cagr=float((1 + wf.rendimento_scelta).prod() ** (1 / len(wf)) - 1),
               wf_rule_cagr=float((1 + wf.rendimento_regola_scelta).prod() ** (1 / len(wf)) - 1),
               wf_etf_cagr=float((1 + wf.rendimento_etf).prod() ** (1 / len(wf)) - 1),
               wf_choices=wf.scelta_walk_forward.value_counts().to_dict(), regime=regime,
               last_date=str(p.dates[last].date()))
    json.dump(dec, open(OUT / "FD_decision.json", "w"), indent=1, default=str)
    print(json.dumps(dec, indent=1, default=str))
    print(frontier[["config", "weight_satellite", "worst_excess", "worst_dd_gap"]].round(4).to_string(index=False))
    print(cs[cs.config == sat][["weight_satellite", "worst_excess", "worst_dd_gap"] + [f"{v}_cagr" for v in VIEWS] + [f"{v}_maxdd" for v in VIEWS]].round(3).to_string(index=False))
    print(sig.round(3).to_string(index=False))
    print(rk[["label", "societa", "mom"]].round(3).to_string(index=False))
    print(rk12[["label", "societa", "mom", "data_classifica"]].round(3).to_string(index=False))
    print(wf.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
