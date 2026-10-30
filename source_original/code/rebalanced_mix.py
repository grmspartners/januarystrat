"""
ETF core + satellite with ANNUAL rebalancing to the target weight (checked at each year-end).
Tax treatment (approximation, declared in the report):
  * satellite -> ETF transfers: no extra tax (the satellite realises its gains at every tranche rebalance anyway,
    so the excess can be skimmed from realised proceeds during the year);
  * ETF -> satellite transfers: 26% on the ETF's embedded gain of the amount sold (cost basis tracked, average cost);
  * end of period: ETF taxed 26% on (value - basis); satellite reduced by its own liquidation-tax ratio.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from config import OUT
from final_selection import VIEWS


def simulate(s: pd.Series, e: pd.Series, w: float, sat_ratio: float, band: float = 0.0):
    idx = s.index.intersection(e.index)
    s, e = s.loc[idx], e.loc[idx]
    rs, re_ = s.pct_change().fillna(0).values, e.pct_change().fillna(0).values
    ye = set(pd.Series(np.arange(len(idx)), index=idx).groupby(idx.year).max().values)
    S, E, B = 100 * w, 100 * (1 - w), 100 * (1 - w)
    vals, tax_rebal = [], 0.0
    for t in range(len(idx)):
        if t > 0:
            S *= 1 + rs[t]
            E *= 1 + re_[t]
        if t in ye and t < len(idx) - 1:
            tot = S + E
            ws = S / tot
            if ws > w + band:
                x = S - w * tot
                S -= x
                E += x
                B += x
            elif ws < w - band:
                y = w * tot - S
                gain_frac = max(0.0, 1 - B / E)
                tax = 0.26 * y * gain_frac
                B *= (E - y) / E
                E -= y
                S += y - tax
                tax_rebal += tax
        vals.append(S + E)
    v = pd.Series(vals, index=idx)
    after = S * sat_ratio + E - 0.26 * max(E - B, 0)
    yrs = (idx[-1] - idx[0]).days / 365.25
    return dict(cagr=(after / 100) ** (1 / yrs) - 1, maxdd=float((v / v.cummax() - 1).min()), final=after,
                tax_rebal=tax_rebal, sat_weight_end=S / (S + E)), v


def main():
    dec = json.load(open(OUT / "FD_decision.json"))
    cur = pd.read_pickle(OUT / "FS_tranche_curves.pkl")
    ports, bcur = cur["ports"], cur["bench"]
    grid = pd.read_csv(OUT / "FS_grid_tranche.csv").set_index("config")
    bench = pd.read_csv(OUT / "FS_benchmark_tranche.csv").set_index("view")
    rows = []
    for cfg in (dec["satellite_rule"], "top1 stop35 keep", "top3 stop35 keep"):
        for w in (0.2, 0.3, 0.4, 0.5, 0.6):
            for band in (0.0, 0.05):
                rec = dict(config=cfg, weight=w, band=band)
                for v in VIEWS:
                    s = ports[(cfg, v)]
                    ratio = grid.loc[cfg, f"{v}_final"] / s.iloc[-1]
                    res, _ = simulate(s, bcur[v], w, ratio, band)
                    rec.update({f"{v}_cagr": res["cagr"], f"{v}_excess": res["cagr"] - bench.loc[v, "cagr"],
                                f"{v}_maxdd": res["maxdd"], f"{v}_dd_gap": res["maxdd"] - bench.loc[v, "maxdd"],
                                f"{v}_sat_weight_end": res["sat_weight_end"], f"{v}_tax_rebal": res["tax_rebal"]})
                rec["worst_excess"] = min(rec[f"{v}_excess"] for v in VIEWS)
                rec["worst_dd_gap"] = min(rec[f"{v}_dd_gap"] for v in VIEWS)
                rows.append(rec)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "FD_rebalanced_mix.csv", index=False)
    pd.set_option("display.width", 250)
    print(df[["config", "weight", "band", "worst_excess", "worst_dd_gap", "core_cagr", "long_cagr", "core_fy_cagr", "long_fy_cagr",
              "core_maxdd", "long_maxdd", "long_sat_weight_end"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
