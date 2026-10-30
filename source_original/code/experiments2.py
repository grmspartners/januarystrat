"""
Phase G - candidate protocols, rolling windows and core-satellite.

The variants of phase D are a search; this phase is the TEST. A short,
pre-declared list of protocols is evaluated on:
  * core sample 2009-2025 (near-complete data) and long sample 1997-2025
    (survivorship-patched), net of Italian taxes, in EUR;
  * every 10-year window starting 1997...2016 (rolling), vs the S&P 500 ETF;
  * the 12 possible start months (rebalance timing luck);
  * core-satellite mixes with an S&P 500 ETF core.
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

import patches
from config import OUT
from experiments import B, END, END_FY, NET_IT, S, row_from
from metrics import annual_returns, summary
from panel import Panel

PROTOCOLS = {
    "P0 thread: top1 stop35 cash": dict(top_n=1, stop=0.35),
    "P1 top1 no stop": dict(top_n=1, stop=None),
    "P2 top3 no stop": dict(top_n=3, stop=None),
    "P3 top3 stop35": dict(top_n=3, stop=0.35),
    "P4 top3 regime": dict(top_n=3, stop=None, regime_filter="sma10"),
    "P5 top1 stop35 regime": dict(top_n=1, stop=0.35, regime_filter="sma10"),
    "P6 top3 stop50 regime": dict(top_n=3, stop=0.50, regime_filter="sma10"),
    "P7 top3 keep-winners regime": dict(top_n=3, stop=None, regime_filter="sma10", keep_winners=True),
    "P8 LEAPS top3 35/65": dict(top_n=3, stop=None, instrument="leaps", leaps_alloc=0.35),
}


def main():
    t0 = time.time()
    pp = patches.apply(Panel.load())
    p = pp
    rows, curves = [], {}
    # ---------- G1 full samples
    for sname, fy, P, end in (("core 2009-2026YTD", 2009, pp, END), ("long 1997-2026YTD", 1997, pp, END),
                              ("core 2009-2025", 2009, pp, END_FY), ("long 1997-2025", 1997, pp, END_FY)):
        for name, kw in PROTOCOLS.items():
            r = S(P, universe="SPX", first_year=fy, currency="EUR", end=end, **NET_IT, **kw)
            rows.append(row_from(r, P, name, dict(sample=sname, kind="protocol")))
            curves[(sname, name)] = r["equity"]
        for which in ("SPX", "NDX"):
            if which == "NDX" and fy < 2009:
                continue
            b = B(p, which, fy, "bh", currency="EUR", end=end)
            rows.append(row_from(b, p, f"{which} ETF buy&hold", dict(sample=sname, kind="benchmark")))
            curves[(sname, f"{which} ETF buy&hold")] = b["equity"]
    full = pd.DataFrame(rows)
    full.to_csv(OUT / "G1_protocols.csv", index=False)
    pd.to_pickle(curves, OUT / "G1_curves.pkl")
    print("G1", round(time.time() - t0));

    # ---------- G2 rolling 10-year windows
    rows = []
    for y in range(1997, 2018):
        end = f"{y + 9}-12-31" if y + 9 <= 2025 else None   # last window: 2017-2026YTD
        b = B(p, "SPX", y, "bh", currency="EUR", end=end)
        bs = summary(b["equity"], None, b["final_after_liq"], 100.0)
        for name, kw in PROTOCOLS.items():
            if kw.get("instrument") == "leaps" and y < 2003:
                pass
            r = S(pp, universe="SPX", first_year=y, currency="EUR", end=end, **NET_IT, **kw)
            s = summary(r["equity"], None, r["final_after_liq"], 100.0)
            rows.append(dict(start=y, end=min(y + 9, 2026), protocol=name, cagr=s["cagr_after_liq"], max_dd=s["max_dd"],
                             bench_cagr=bs["cagr_after_liq"], bench_max_dd=bs["max_dd"],
                             excess_cagr=s["cagr_after_liq"] - bs["cagr_after_liq"]))
    roll = pd.DataFrame(rows)
    roll.to_csv(OUT / "G2_rolling10y.csv", index=False)
    print("G2", round(time.time() - t0))

    # ---------- G3 timing luck on protocols (core sample)
    rows = []
    for name, kw in PROTOCOLS.items():
        if kw.get("instrument") == "leaps":
            continue
        for m in range(1, 13):
            r = S(p, universe="SPX", first_year=2009, first_month=m, currency="EUR", end=END, **NET_IT, **kw)
            s = summary(r["equity"], None, r["final_after_liq"], 100.0)
            rows.append(dict(protocol=name, start_month=m, cagr=s["cagr_after_liq"], max_dd=s["max_dd"],
                             final=s["final_after_liq"]))
    tl = pd.DataFrame(rows)
    tl.to_csv(OUT / "G3_timing_luck.csv", index=False)
    print("G3", round(time.time() - t0))

    # ---------- G4 core-satellite (no rebalancing between sleeves: tax-efficient)
    rows = []
    for sname in ("core 2009-2026YTD", "long 1997-2026YTD"):
        bench = curves[(sname, "SPX ETF buy&hold")]
        b_after = full[(full["sample"] == sname) & (full.name == "SPX ETF buy&hold")].final_after_liq.iat[0]
        for name in PROTOCOLS:
            sat = curves[(sname, name)]
            s_after = full[(full["sample"] == sname) & (full.name == name)].final_after_liq.iat[0]
            idx = bench.index.intersection(sat.index)
            for w in (0.0, 0.1, 0.2, 0.3, 0.5, 1.0):
                mix = (1 - w) * bench.loc[idx] / bench.loc[idx].iloc[0] * 100 + w * sat.loc[idx] / sat.loc[idx].iloc[0] * 100
                final_after = (1 - w) * b_after + w * s_after
                s = summary(mix, None, final_after, 100.0)
                rows.append(dict(sample=sname, satellite=name, weight_satellite=w, cagr_after_liq=s["cagr_after_liq"],
                                 final_after_liq=final_after, max_dd=s["max_dd"], vol=s["vol"],
                                 worst_year=s["worst_year"]))
    cs = pd.DataFrame(rows)
    cs.to_csv(OUT / "G4_core_satellite.csv", index=False)
    print("G4", round(time.time() - t0))


if __name__ == "__main__":
    main()
