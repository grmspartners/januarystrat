"""
Builds the deliverables from the CSV outputs of the experiment phases:
  out/charts/*.png                      figures for the thesis
  out/GRMS_JanuaryBuy_Risultati.xlsx    every table, one sheet per phase
"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

import patches
from config import OUT, WIKI_SP500, YAHOO_META
from metrics import annual_returns
from panel import Panel
from signals import ranking, year_end_rows

CH = OUT / "charts"
BENCH_CAGR = {2009: 0.140, 1997: 0.090}   # S&P 500 ETF buy & hold, net EUR, to 9-Oct-2026 (G1)
CH.mkdir(parents=True, exist_ok=True)

# GRMS identity: white surface, antracite ink, bronze accent for the hero series.
INK, INK2, GRID = "#2b2b2b", "#5a5a58", "#e6e4df"
BRONZE, BLUE, GREEN, VIOLET, RED = "#b5712a", "#2a78d6", "#138a5e", "#6250d6", "#e34948"
BENCH, BENCH2 = "#8a8a86", "#2b2b2b"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": INK2, "axes.labelcolor": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.titleweight": "bold", "axes.titlesize": 11,
    "axes.titlecolor": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150, "savefig.bbox": "tight",
    "legend.frameon": False, "lines.linewidth": 1.6,
})


def pct(ax, axis="y", dec=0):
    f = mtick.PercentFormatter(1.0, decimals=dec)
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(f)


def save(fig, name):
    fig.savefig(CH / name, facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------ charts
def chart_replication():
    curves = pd.read_pickle(OUT / "C_curves.pkl")
    # thread rule gross 1997-2026 (patched) vs S&P; from phase C keys
    k1 = ("long 1997-2026YTD", "USD", "SPX top1 stop=0.35 gross")
    k2 = ("long 1997-2026YTD", "USD", "SPX top1 stop=None gross")
    k3 = ("long 1997-2026YTD", "USD", "SPX ETF none")
    fig, ax = plt.subplots(figsize=(8.5, 4.3))
    for k, col, lab, ls in ((k1, BRONZE, "Vincitore anno prec. + stop 35%", "-"),
                            (k2, BLUE, "Vincitore anno prec., senza stop", "-"),
                            (k3, BENCH, "S&P 500 Total Return", "--")):
        s = curves[k]
        ax.plot(s.index, s.values, color=col, ls=ls, label=lab)
        ax.annotate(f"${s.iloc[-1]:,.0f}", (s.index[-1], s.iloc[-1]), xytext=(4, 0), textcoords="offset points",
                    color=INK, fontsize=8, va="center")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.set_title("Replica del thread: $100 dal 1997, lordo, USD (dati con patch survivorship)")
    ax.legend(loc="upper left")
    save(fig, "fig01_replica_thread.png")


def chart_gross_to_net(c):
    x = c[(c["sample"] == "core 2009-2026YTD") & (c.kind == "strategy") & (c.top_n == 1) & (c.stop == 0.35)]
    order = [("gross", "USD", "Lordo USD"), ("gross_cost", "USD", "+ costi\n+ T-bill"),
             ("net_it", "USD", "+ fisco IT\n(USD)"), ("net_it", "EUR", "Netto fisco IT\nin EUR"),
             ("deferred", "EUR", "Veicolo lordista\n(EUR)")]
    vals = []
    for pr, ccy, lab in order:
        r = x[(x.preset == pr) & (x.ccy == ccy)].iloc[0]
        vals.append((lab, r.cagr_after_liq if pr in ("net_it", "deferred") else r.cagr))
    b = c[(c["sample"] == "core 2009-2026YTD") & (c.name == "SPX ETF bh") & (c.ccy == "EUR")].iloc[0]
    n = c[(c["sample"] == "core 2009-2026YTD") & (c.name == "NDX ETF bh") & (c.ccy == "EUR")].iloc[0]
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    labs, v = zip(*vals)
    bars = ax.bar(labs, v, color=[BRONZE] * 4 + [GREEN], width=0.6)
    for bb, vv in zip(bars, v):
        ax.text(bb.get_x() + bb.get_width() / 2, vv + 0.006, f"{vv:.1%}", ha="center", color=INK, fontsize=8.5)
    ax.set_axisbelow(True)
    ax.axhline(b.cagr_after_liq, color=BENCH, ls="--", lw=1.2, label=f"S&P 500 ETF buy&hold, netto EUR ({b.cagr_after_liq:.1%})")
    ax.axhline(n.cagr_after_liq, color=BENCH2, ls=":", lw=1.2, label=f"Nasdaq-100 ETF buy&hold, netto EUR ({n.cagr_after_liq:.1%})")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, fontsize=8)
    ax.set_ylim(0, max(v) * 1.15)
    pct(ax)
    ax.set_ylabel("CAGR 2009-2026 YTD")
    ax.set_title("Dal lordo al netto: regola del thread (top-1, stop 35%), gen-2009 / 9-ott-2026")
    save(fig, "fig02_lordo_netto.png")


def chart_protocols(curves, sample, fname, title, keys):
    fig, ax = plt.subplots(figsize=(8.5, 4.3))
    cols = [BRONZE, BLUE, GREEN, VIOLET, RED]
    i = 0
    for k in keys:
        s = curves[(sample, k)]
        if "ETF" in k:
            ax.plot(s.index, s.values, color=BENCH if "SPX" in k else BENCH2, ls="--" if "SPX" in k else ":", label=k)
        else:
            ax.plot(s.index, s.values, color=cols[i], label=k)
            i += 1
        ax.annotate(f"€{s.iloc[-1]:,.0f}", (s.index[-1], s.iloc[-1]), xytext=(4, 0), textcoords="offset points",
                    fontsize=7.5, color=INK, va="center")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"€{v:,.0f}"))
    ax.set_title(title)
    ax.legend(loc="upper left", fontsize=8)
    save(fig, fname)
    # drawdowns
    fig, ax = plt.subplots(figsize=(8.5, 3.2))
    i = 0
    for k in keys:
        s = curves[(sample, k)]
        dd = s / s.cummax() - 1
        if "ETF" in k:
            ax.plot(dd.index, dd.values, color=BENCH if "SPX" in k else BENCH2, ls="--" if "SPX" in k else ":", lw=1.1, label=k)
        else:
            ax.plot(dd.index, dd.values, color=cols[i], lw=1.1, label=k)
            i += 1
    pct(ax)
    ax.set_title(title.replace("Valore", "Drawdown").split(":")[0] + ": drawdown dal massimo")
    ax.legend(loc="lower left", fontsize=7.5, ncol=2)
    save(fig, fname.replace(".png", "_dd.png"))


def chart_timing(tl):
    sel = ["P0 thread: top1 stop35 cash", "P2 top3 no stop", "P5 top1 stop35 regime"]
    mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6), sharey=True)
    for ax, smp in zip(axes, ("core", "long")):
        x = tl[(tl["sample"] == smp) & (tl.m != "12 tranches")]
        w = 0.27
        for i, (pname, col) in enumerate(zip(sel, (BRONZE, BLUE, GREEN))):
            y = x[x.protocol == pname].sort_values("m", key=lambda s: s.astype(int)).cagr.values
            ax.bar(np.arange(12) + (i - 1) * w, y, width=w - 0.03, color=col, label=pname)
        bench = tl[(tl["sample"] == smp) & (tl.m == "12 tranches")].bench.iloc[0]
        ax.axhline(bench, color=BENCH, ls="--", lw=1.1)
        ax.axhline(0, color=INK2, lw=0.6)
        ax.set_xticks(range(12))
        ax.set_xticklabels(mesi, fontsize=8)
        ax.set_title({"core": "2009-2026 YTD", "long": "1997-2026 YTD (con patch)"}[smp])
        pct(ax)
    axes[0].set_ylabel("CAGR netto EUR")
    axes[0].legend(fontsize=7.5, loc="lower left")
    fig.suptitle("Timing luck: stessa regola annuale, mese di partenza diverso (linea = S&P 500 ETF)", fontsize=10.5,
                 color=INK, fontweight="bold", y=1.04)
    save(fig, "fig05_timing_luck.png")


def chart_ranks():
    cal = pd.read_csv(OUT / "E_rank_tests_calendar.csv")
    mon = pd.read_csv(OUT / "E_rank_tests_monthly_SPX_1996.csv")
    c = cal[(cal["sample"] == "SPX 1996-2024") & (cal["rank"] != "1-3 avg")].copy()
    c["rank"] = c["rank"].astype(int)
    m = mon[mon.portfolio.str.match(r"r\d+")].copy()
    m["rank"] = m.portfolio.str[1:].astype(int)
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    ax.bar(c["rank"] - 0.2, c.mean_excess, width=0.38, color=BRONZE, label="Calendario (gen-dic), media 1997-2025 (anni successivi completi)")
    ax.errorbar(c["rank"] - 0.2, c.mean_excess, yerr=[c.mean_excess - c.ci95_lo, c.ci95_hi - c.mean_excess],
                fmt="none", ecolor=INK2, elinewidth=0.8, capsize=2)
    ax.bar(m["rank"] + 0.2, m.mean_excess_12m, width=0.38, color=BLUE,
           label="Tutti i mesi di formazione (sovrapposti)")
    ax.axhline(0, color=INK2, lw=0.6)
    ax.set_xticks(range(1, 11))
    ax.set_xlabel("Posizione nel ranking del rendimento a 12 mesi (1 = migliore)")
    ax.set_ylabel("Extra-rendimento 12m vs media equipesata")
    pct(ax)
    ax.set_title("S&P 500: rendimento successivo per posizione in classifica")
    ax.legend(fontsize=8)
    save(fig, "fig06_rank_excess.png")


def chart_rolling(roll):
    sel = ["P0 thread: top1 stop35 cash", "P2 top3 no stop", "P7 top3 keep-winners regime"]
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    for pname, col in zip(sel, (BRONZE, BLUE, GREEN)):
        x = roll[roll.protocol == pname]
        ax.plot(x.start, x.excess_cagr, color=col, marker="o", ms=3.5, label=pname)
    ax.axhline(0, color=INK2, lw=0.8)
    pct(ax)
    ax.set_xlabel("Anno di inizio della finestra di 10 anni")
    ax.set_ylabel("CAGR netto - CAGR S&P 500 ETF")
    ax.set_title("Finestre mobili di 10 anni: extra-rendimento netto (EUR) vs S&P 500 ETF")
    ax.legend(fontsize=8)
    save(fig, "fig07_rolling10y.png")


def chart_heatmap(d):
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4))
    for ax, (uni, fy, ttl) in zip(axes, (("SPX", 2009, "S&P 500, 2009-2026 YTD"), ("SPX", 1997, "S&P 500, 1997-2026 YTD (patch)"))):
        sub = d[d.name.str.startswith(f"D1 {uni} {fy} ")].copy()
        sub["top"] = sub.name.str.extract(r"top(\d+)").astype(int)
        sub["stop"] = sub.name.str.extract(r"stop(\S+)$")[0].replace("None", "nessuno")
        piv = sub.pivot(index="top", columns="stop", values="cagr_after_liq")
        piv = piv[["0.15", "0.25", "0.35", "0.5", "nessuno"]]
        from matplotlib.colors import TwoSlopeNorm
        bench = BENCH_CAGR[fy]
        norm = TwoSlopeNorm(vmin=0.0, vcenter=bench, vmax=0.32)
        im = ax.imshow(piv.values, cmap="BrBG", norm=norm, aspect="auto")
        for i in range(piv.shape[0]):
            for j in range(piv.shape[1]):
                v = piv.values[i, j]
                ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=8, color="white" if v > 0.26 else INK)
        ax.set_xticks(range(piv.shape[1]))
        ax.set_xticklabels(["15%", "25%", "35%", "50%", "nessuno"])
        ax.set_yticks(range(piv.shape[0]))
        ax.set_yticklabels([f"top {t}" for t in piv.index])
        ax.set_xlabel("Stop loss dal prezzo di carico")
        ax.set_title(ttl)
        ax.grid(False)
    fig.suptitle("CAGR netto EUR per numero di titoli e livello di stop (verde = sopra S&P 500 ETF, marrone = sotto)",
                 fontsize=10.5, color=INK, fontweight="bold", y=1.04)
    save(fig, "fig08_heatmap_topn_stop.png")


def chart_concentration(conc):
    fig, ax = plt.subplots(figsize=(8.5, 3.3))
    for (smp, top, stop), col in zip([("core 2009-2026YTD", 1, 0.35), ("long 1997-2026YTD", 1, 0.35),
                                      ("long 1997-2026YTD", 3, 0.35)], (BRONZE, BLUE, GREEN)):
        x = conc[(conc["sample"] == smp) & (conc.top_n == top) & (conc.stop == stop)]
        ax.plot(x.removed_best, x.share_of_full, marker="o", color=col, label=f"{smp}, top{top}, stop 35%")
    ax.set_yscale("log")
    pct(ax)
    ax.set_xlabel("Numero di anni migliori rimossi")
    ax.set_ylabel("Ricchezza finale residua (% del totale)")
    ax.set_title("Concentrazione: quanto del risultato dipende dai pochi anni migliori (lordo)")
    ax.legend(fontsize=8)
    save(fig, "fig09_concentrazione.png")


def chart_core_sat(cs):
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6))
    for ax, smp in zip(axes, ("core 2009-2026YTD", "long 1997-2026YTD")):
        for pname, col in zip(["P0 thread: top1 stop35 cash", "P2 top3 no stop", "P7 top3 keep-winners regime"],
                              (BRONZE, BLUE, GREEN)):
            x = cs[(cs["sample"] == smp) & (cs.satellite == pname)].sort_values("weight_satellite")
            ax.plot(-x.max_dd, x.cagr_after_liq, marker="o", color=col, label=pname)
            for _, r in x.iterrows():
                if r.weight_satellite in (0.2, 0.5):
                    ax.annotate(f"{int(r.weight_satellite * 100)}%", (-r.max_dd, r.cagr_after_liq), xytext=(3, -8),
                                textcoords="offset points", fontsize=7, color=INK2)
        pct(ax, "x")
        pct(ax, "y")
        ax.set_xlabel("Max drawdown")
        ax.set_title(smp)
    axes[0].set_ylabel("CAGR netto EUR")
    axes[0].legend(fontsize=7.5, loc="upper left")
    fig.suptitle("Core-satellite: S&P 500 ETF + quota momentum (0-100%)", fontsize=10.5, color=INK, fontweight="bold", y=1.03)
    save(fig, "fig10_core_satellite.png")


def chart_leaps(l, g1):
    x = l[(l.first_year == 2009) & (l.top_n == 1) & (l.alloc == 0.35)]
    piv = x.pivot(index="iv_mult", columns="half_spread", values="cagr_after_liq")
    fig, ax = plt.subplots(figsize=(8.5, 3.3))
    w = 0.26
    for i, (hs, col) in enumerate(zip(piv.columns, (GREEN, BLUE, VIOLET))):
        ax.bar(np.arange(len(piv)) + (i - 1) * w, piv[hs].values, width=w - 0.03, color=col, label=f"half-spread {hs:.0%}")
    stock = g1[(g1["sample"] == "core 2009-2026YTD") & (g1.name == "P0 thread: top1 stop35 cash")].cagr_after_liq.iat[0]
    nostop = g1[(g1["sample"] == "core 2009-2026YTD") & (g1.name == "P1 top1 no stop")].cagr_after_liq.iat[0]
    ax.axhline(stock, color=BRONZE, lw=1.4)
    ax.text(-0.45, stock, "azione + stop 35%", color=INK, fontsize=8, va="bottom", ha="left")
    ax.axhline(nostop, color=BRONZE, lw=1.0, ls="--")
    ax.text(-0.45, nostop, "azione senza stop", color=INK, fontsize=8, va="bottom", ha="left")
    ax.set_xticks(range(len(piv)))
    ax.set_xticklabels([f"IV = {m:.1f} x vol realizzata" for m in piv.index])
    pct(ax)
    ax.set_ylabel("CAGR netto EUR 2009-2026 YTD")
    ax.set_title("LEAPS (premio 35% dello spot, 35% del capitale) vs azione, top-1")
    ax.set_ylim(0, max(stock, nostop) * 1.12)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3)
    save(fig, "fig11_leaps.png")


def coverage_table(p):
    ye = year_end_rows(p)
    rows = []
    for idx, y0 in (("SPX", 1996), ("NDX", 2007)):
        for y in range(y0, 2027):
            d = ye[y]
            n_all = p.members_count(idx, p.dates[d])
            n_px = len(ranking(p, idx, d, ye[y - 1], min_days=None))
            n_px_partial = len(ranking(p, idx, d, ye[y - 1], min_days=1))
            rows.append(dict(indice=idx, anno=y, membri=n_all, con_prezzi_anno_intero=n_px,
                             con_prezzi_anche_parziali=n_px_partial, copertura=n_px_partial / n_all))
    return pd.DataFrame(rows)


def chart_coverage(cov):
    fig, ax = plt.subplots(figsize=(8.5, 3.0))
    for idx, col in (("SPX", BRONZE), ("NDX", BLUE)):
        x = cov[cov.indice == idx]
        ax.plot(x.anno, x.copertura, marker="o", ms=3, color=col, label={"SPX": "S&P 500", "NDX": "Nasdaq-100"}[idx])
    ax.axhline(0.95, color=BENCH, ls="--", lw=1)
    pct(ax)
    ax.set_ylim(0.4, 1.02)
    ax.set_title("Copertura prezzi dei membri point-in-time dell'indice (fine anno)")
    ax.legend(fontsize=8)
    save(fig, "fig12_copertura_dati.png")


def annual_table():
    curves = pd.read_pickle(OUT / "G1_curves.pkl")
    out = {}
    for (smp, name), s in curves.items():
        if smp == "core 2009-2026YTD":
            ar = annual_returns(s)
            out[name] = ar
    return pd.DataFrame(out).iloc[1:]


# ------------------------------------------------------------------ final-selection charts
MESI = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]


def chart_start_months(sl, etf, dec):
    sat = dec["satellite_rule"]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6), sharey=True)
    for ax, v, ttl in zip(axes, ("core", "long"), ("2009 - 9 ott 2026", "1997 - 9 ott 2026 (con patch)")):
        w = 0.28
        for i, (cfg, col, lab) in enumerate(((("top1 stop35"), BRONZE, "top-1 stop 35% (regola del thread)"),
                                             (sat, BLUE, f"{sat} (satellite scelto)"))):
            y = [sl.loc[cfg, f"{v}_m{m:02d}"] for m in range(1, 13)]
            ax.bar(np.arange(12) + (i - 0.5) * w, y, width=w - 0.03, color=col, label=lab)
        ax.plot(np.arange(12), etf[v].values, color=BENCH, ls="--", lw=1.2, marker="o", ms=2.5, label="S&P 500 ETF")
        ax.axhline(0, color=INK2, lw=0.6)
        ax.set_xticks(range(12))
        ax.set_xticklabels(MESI, fontsize=8)
        ax.set_title(ttl)
        pct(ax)
    axes[0].set_ylabel("CAGR netto EUR, dopo imposta finale")
    axes[0].legend(fontsize=7.5, loc="upper right")
    fig.suptitle("Stessa regola, 12 mesi di partenza: la versione di gennaio e' la piu' fortunata",
                 fontsize=10.5, color=INK, fontweight="bold", y=1.04)
    save(fig, "fig13_mesi_partenza.png")


def chart_frontier(cs, dec):
    fig, ax = plt.subplots(figsize=(8.5, 4.0))
    sel = [("top1 stop35 keep", BRONZE), (dec["satellite_rule"], BLUE), ("top3 stop35 keep", GREEN), ("top5 stop35 keep", VIOLET)]
    seen = set()
    for cfg, col in sel:
        if cfg in seen:
            continue
        seen.add(cfg)
        x = cs[cs.config == cfg].sort_values("weight_satellite")
        ax.plot(x.worst_dd_gap, x.worst_excess, marker="o", ms=3, color=col, label=cfg)
        for _, r in x.iterrows():
            lab_ok = (0.2, 0.3, 0.6, 1.0) if cfg in ("top1 stop35 keep", dec["satellite_rule"]) else (1.0,)
            if round(r.weight_satellite, 2) in lab_ok:
                ax.annotate(f"{int(round(r.weight_satellite * 100))}%", (r.worst_dd_gap, r.worst_excess), xytext=(3, 3),
                            textcoords="offset points", fontsize=7, color=INK2)
    ax.axvline(-0.05, color=RED, ls="--", lw=1)
    ax.text(-0.052, ax.get_ylim()[1] * 0.95, "budget di rischio: -5 punti\nvs drawdown dell'ETF", color=RED, fontsize=7.5,
            ha="right", va="top")
    ax.axhline(0, color=INK2, lw=0.6)
    pct(ax, "x")
    pct(ax, "y")
    ax.set_xlabel("Drawdown massimo del portafoglio meno drawdown dell'ETF (peggiore dei 4 periodi)")
    ax.set_ylabel("Extra-CAGR netto vs ETF (peggiore dei 4 periodi)")
    ax.set_title("ETF S&P 500 + satellite: quota del satellite da 5% a 100% (etichette)")
    ax.legend(fontsize=8, loc="lower left")
    save(fig, "fig14_frontiera_core_satellite.png")


def chart_recommended(dec):
    cur = pd.read_pickle(OUT / "FS_tranche_curves.pkl")
    ports, bcur = cur["ports"], cur["bench"]
    sat, w = dec["satellite_rule"], dec["weight_recommended"]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8))
    for ax, v, ttl in zip(axes, ("long", "core"), ("1997 - 9 ott 2026", "2009 - 9 ott 2026")):
        s, e = ports[(sat, v)], bcur[v]
        idx = s.index.intersection(e.index)
        s, e = s.loc[idx] / s.loc[idx].iloc[0] * 100, e.loc[idx] / e.loc[idx].iloc[0] * 100
        mix = (1 - w) * e + w * s
        ax.plot(s.index, s, color=BLUE, lw=1.1, label=f"satellite {sat}, 12 tranche")
        ax.plot(mix.index, mix, color=BRONZE, lw=1.8, label=f"{int((1 - w) * 100)}% ETF + {int(w * 100)}% satellite")
        ax.plot(e.index, e, color=BENCH, ls="--", lw=1.2, label="S&P 500 ETF")
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v_, _: f"€{v_:,.0f}"))
        import matplotlib.dates as mdates
        ax.xaxis.set_major_locator(mdates.YearLocator(4 if v == "core" else 5))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.set_title(ttl)
    axes[0].legend(fontsize=7.5, loc="upper left")
    fig.suptitle("Allocazione raccomandata: valore di €100, netto fisco IT (prima dell'imposta finale)", fontsize=10.5,
                 color=INK, fontweight="bold", y=1.03)
    save(fig, "fig15_allocazione_raccomandata.png")


def chart_concentration_now(sig):
    x = sig.groupby("ticker").tranche.nunique().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8.5, 2.8))
    ax.bar(x.index, x.values, color=[BRONZE] + [BLUE] * (len(x) - 1), width=0.6)
    for i, v in enumerate(x.values):
        ax.text(i, v + 0.15, str(v), ha="center", fontsize=8, color=INK)
    ax.set_ylabel("Tranche (su 12)")
    ax.set_title("Concentrazione al 9-10-2026: in quante delle 12 tranche compare lo stesso titolo")
    ax.set_ylim(0, 13)
    save(fig, "fig16_concentrazione_tranche.png")


# ------------------------------------------------------------------ excel
def write_excel(sheets: dict, path):
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        for name, (df, note) in sheets.items():
            df.to_excel(xw, sheet_name=name[:31], index=False, startrow=2)
            ws = xw.sheets[name[:31]]
            ws["A1"] = note
            from openpyxl.styles import Alignment, Font, PatternFill
            ws["A1"].font = Font(name="Arial", bold=True, color="2B2B2B", size=11)
            hdr = PatternFill("solid", fgColor="F3EEE6")
            for cell in ws[3]:
                cell.font = Font(name="Arial", bold=True, color="2B2B2B", size=9)
                cell.fill = hdr
                cell.alignment = Alignment(wrap_text=True, vertical="top")
            for i, col in enumerate(df.columns, start=1):
                width = min(48, max(10, len(str(col)) + 2, int(df[col].astype(str).str.len().quantile(0.9)) + 2 if len(df) else 10))
                ws.column_dimensions[ws.cell(row=3, column=i).column_letter].width = width
                lc = str(col).lower()
                fmt = None
                if any(k in lc for k in ("cagr", "return", "dd", "excess", "copertura", "coverage", "vol", "worst", "best", "pct",
                                         "hit", "share", "ret", "ci95", "mean", "median", "p_strat", "rendimento", "alpha", "next")):
                    fmt = "0.0%"
                if any(k in lc for k in ("final", "multiple", "tax_paid", "losses", "valore")):
                    fmt = "#,##0.00"
                if any(k in lc for k in ("sharpe", "sortino", "calmar", "t_stat", "nw_t", "_t", "beta", "b_", "r2", "skew", "kurt")):
                    fmt = "0.00"
                if fmt:
                    for r in range(4, 4 + len(df)):
                        c = ws.cell(row=r, column=i)
                        if isinstance(c.value, (int, float)):
                            c.number_format = fmt
            ws.freeze_panes = "A4"
            for row in ws.iter_rows(min_row=4, max_row=3 + len(df)):
                for cell in row:
                    cell.font = Font(name="Arial", size=9)


def main():
    p = patches.apply(Panel.load())
    c = pd.read_csv(OUT / "C_gross_to_net.csv")
    d = pd.read_csv(OUT / "D_variants.csv")
    l = pd.read_csv(OUT / "D_leaps.csv")
    g1 = pd.read_csv(OUT / "G1_protocols.csv")
    roll = pd.read_csv(OUT / "G2_rolling10y.csv")
    tl = pd.read_csv(OUT / "G5_timing_luck_tranches.csv")
    cs = pd.read_csv(OUT / "G4_core_satellite.csv")
    conc = pd.read_csv(OUT / "E_concentration.csv")
    curves = pd.read_pickle(OUT / "G1_curves.pkl")
    dec = json.load(open(OUT / "FD_decision.json"))
    sl = pd.read_csv(OUT / "FD_sleeves.csv").set_index("config")
    etf_sl = pd.read_csv(OUT / "FD_etf_sleeves.csv", index_col=0)
    fcs = pd.read_csv(OUT / "FD_core_satellite.csv")
    sig = pd.read_csv(OUT / "FD_segnali_tranche.csv")

    chart_replication()
    chart_gross_to_net(c)
    chart_protocols(curves, "long 1997-2026YTD", "fig03_protocolli_lungo.png",
                    "Valore del dossier, €100 netto fisco IT, 1997 - 9 ott 2026 (prima dell'imposta di liquidazione)",
                    ["P0 thread: top1 stop35 cash", "P2 top3 no stop", "P5 top1 stop35 regime", "P7 top3 keep-winners regime",
                     "SPX ETF buy&hold"])
    chart_protocols(curves, "core 2009-2026YTD", "fig04_protocolli_core.png",
                    "Valore del dossier, €100 netto fisco IT, 2009 - 9 ott 2026 (prima dell'imposta di liquidazione)",
                    ["P0 thread: top1 stop35 cash", "P2 top3 no stop", "P5 top1 stop35 regime", "P7 top3 keep-winners regime",
                     "SPX ETF buy&hold", "NDX ETF buy&hold"])
    chart_timing(tl)
    chart_ranks()
    chart_rolling(roll)
    chart_heatmap(d)
    chart_concentration(conc)
    chart_core_sat(cs)
    chart_leaps(l, g1)
    cov = pd.read_csv(OUT / "SP4_riepilogo_anno.csv")
    chart_coverage(cov)
    chart_start_months(sl, etf_sl, dec)
    chart_frontier(fcs, dec)
    chart_recommended(dec)
    chart_concentration_now(sig)

    top3 = pd.read_csv(OUT / "top3_by_year.csv")
    from names import company
    top3.insert(4, "societa", top3.label.map(company))
    top3["label"] = top3.label.str.replace("Y_", "", regex=False)
    top3 = top3.rename(columns={"index": "indice", "year": "anno", "rank": "pos", "label": "ticker_label",
                                "total_return": "rendimento_anno", "partial_year": "anno_parziale",
                                "next_year_return": "rendimento_anno_successivo", "next_year_to": "successivo_fino_al",
                                "n_ranked": "titoli_classificati", "coverage": "copertura", "quality": "qualita",
                                "universe": "universo", "verified": "verifica_fonti", "missing_known": "vincitori_mancanti_noti"})
    p_repairs = p.repairs.copy()
    ann = annual_table().reset_index().rename(columns={"index": "anno"})
    fd_ann = pd.read_csv(OUT / "FD_annual.csv", header=[0, 1], index_col=0)
    fd_ann.columns = [f"{a} | {b}" for a, b in fd_ann.columns]
    fd_ann = fd_ann.reset_index().rename(columns={"index": "anno"})
    sp3 = pd.read_csv(OUT / "SP3_vincitori_reinseriti.csv")
    sp3b = pd.read_csv(OUT / "SP3b_ancora_mancanti.csv")
    fsum = pd.DataFrame([dec]).T.reset_index()
    fsum.columns = ["voce", "valore"]
    fsum["valore"] = fsum["valore"].astype(str)

    leggimi = pd.DataFrame({"Sezione": [
        "Oggetto", "Data dei dati", "Universo", "Dati prezzi", "Survivorship / titoli spariti", "Regola base",
        "Fisco (scenario net_it)", "Benchmark", "Valuta", "Campioni", "Qualita top-3", "Protocolli P0-P8",
        "Selezione finale", "Decisione", "Codice"], "Contenuto": [
        "Backtest della regola 'compra il miglior titolo dell'anno precedente' (thread X) e delle varianti richieste, per GRMS Partners.",
        f"Prezzi fino al {dec['last_date']} compreso; il 2026 e' incluso come anno in corso (YTD).",
        "S&P 500 point-in-time dal 1996 (fja05680 / Johnbrick123); Nasdaq-100 point-in-time dal 2007 (jmccarrell/n100tickers). Anni precedenti: universo proxy (flag P).",
        "Johnbrick123/sp500-data (Yahoo + Tiingo + Quandl WIKI + Kaggle) e Yahoo Finance per Nasdaq-100 e benchmark; FRED per T-bill ed EUR/USD; Kenneth French per i fattori; Wikipedia 'Historical components of the S&P 500' per i nomi delle societa' uscite.",
        "Copertura prezzi S&P 500: 49% dei membri (1996) -> 75% (2005) -> 95%+ (dal 2010). 9 vincitori annuali mancanti nei dati gratuiti (Sprint PCS, Nextel, Reebok, Dynegy x2, Providian, Avaya, TXU, UST) reinseriti come serie ricostruite dai documenti SEC (DEF 14A, 10-K) e dalle liste S&P DJI / CNN / Forbes. Fogli 'Spariti_*'.",
        "Ranking per rendimento totale dell'anno solare tra i membri dell'indice all'ultima seduta; vendita alla chiusura dell'ultima seduta, acquisto all'apertura della prima seduta dell'anno; stop 35% sotto il prezzo di carico (minimo intraday, riempimento al livello o all'apertura se in gap).",
        "Plusvalenze 26% con zainetto minusvalenze 4 anni (art. 68 c.5 TUIR); dividendi USA 37,1% (15% USA + 26% sul netto); bollo 0,20% annuo; interessi T-bill 12,5%; costi 10 bps per lato. Valore 'after_liq' = al netto delle imposte di liquidazione.",
        "ETF UCITS ad accumulazione su S&P 500 (TER 0,07%) e Nasdaq-100 (TER 0,30%), ritenuta 15% sui dividendi a livello di fondo. Regimi: bh (imposta a scadenza), annual (vendi/ricompra ogni anno; minus ETF non compensabili con proventi ETF), annual_sym (ipotetico simmetrico).",
        "USD come nel thread; EUR per l'investitore italiano (plusvalenze calcolate in euro ai cambi storici; pre-1999 euro sintetico dal marco tedesco).",
        "core 2009-2026 YTD (copertura dati quasi completa) e long 1997-2026 YTD con patch; sensibilita' a fine 2025 (anni interi) nei fogli con 'fy' / '2025'.",
        "A = point-in-time, copertura >=95%; B = 75-95%; C = <75%; P = proxy (solo indicativo).",
        "P0 regola del thread; P1 top1 senza stop; P2 top3; P3 top3 stop 35%; P4 top3 con filtro di regime (S&P 500 TR sopra media 10 mesi); P5 top1 stop + regime; P6 top3 stop 50% + regime; P7 top3 regime + mantieni i vincitori riconfermati; P8 LEAPS top3 35/65.",
        "48 configurazioni (top 1/2/3/5 x stop nessuno/35%/50% x filtro regime si/no x mantieni vincitori si/no), ciascuna su 12 tranche mensili, 4 viste (core, long, core a fine 2025, long a fine 2025): 2.304 backtest. Fogli 'Finale_*'.",
        f"Satellite: {dec['satellite_rule']}, 12 tranche mensili; peso massimo {dec['weight_cap']:.0%}, raccomandato {dec['weight_recommended']:.0%} del portafoglio azionario; core = ETF S&P 500 UCITS ad accumulazione.",
        "Cartella code/: tutto riproducibile con python run_all.py."]})

    sheets = {
        "LEGGIMI": (leggimi, "GRMS Partners - January Buy: studio della strategia momentum 'vincitore dell'anno precedente'"),
        "Finale_decisione": (fsum, "Decisione finale: regola satellite, pesi, test statistici, walk-forward, regime corrente"),
        "Finale_griglia_48": (pd.read_csv(OUT / "FS_grid_tranche.csv"), "Selezione finale: 48 configurazioni su 12 tranche mensili, 4 viste, netto fisco IT in EUR"),
        "Finale_ETF_tranche": (pd.read_csv(OUT / "FS_benchmark_tranche.csv"), "Benchmark S&P 500 ETF buy & hold, 12 tranche, 4 viste"),
        "Finale_mesi_partenza": (sl.reset_index(), "CAGR netto per ciascuno dei 12 mesi di partenza (m01 = gennaio), mediana, peggiore, quota di mesi che batte l'ETF"),
        "Finale_ETF_mesi": (etf_sl.reset_index().rename(columns={"index": "mese"}), "CAGR netto dell'ETF S&P 500 per mese di ingresso"),
        "Finale_core_satellite": (fcs, "ETF S&P 500 + satellite (quota 0-100%): extra-rendimento e drawdown vs ETF nelle 4 viste"),
        "Finale_ribilanciamento": (pd.read_csv(OUT / "FD_rebalanced_mix.csv"), "ETF + satellite con ribilanciamento annuale al peso obiettivo (banda 0 / 5 punti)"),
        "Finale_frontiera": (pd.read_csv(OUT / "FD_frontier.csv"), "Miglior quota ammessa (drawdown <= ETF + 5 punti) per ciascuna regola"),
        "Finale_walk_forward": (pd.read_csv(OUT / "FD_walkforward.csv"), "Walk-forward 2007-2026: scelta annuale della regola con il miglior extra-rendimento storico"),
        "Finale_rendimenti_annui": (fd_ann, "Rendimenti annui: satellite (12 tranche e solo gennaio), ETF, allocazioni miste"),
        "Spariti_top3": (pd.read_csv(OUT / "SP1_top3_stato.csv"), "Titoli spariti: stato oggi di ogni top-3 (quotata / uscita dal listino, esito societario)"),
        "Spariti_reinseriti": (sp3, "Vincitori annuali assenti dai dati gratuiti e reinseriti da documenti SEC (con fonti)"),
        "Spariti_ancora_mancanti": (sp3b, "Membri noti con rendimento elevato ancora mancanti (sotto la top-3: nessun effetto sulla regola)"),
        "Spariti_membri_senza_dati": (pd.read_csv(OUT / "SP2_membri_senza_dati.csv"), "Ogni membro point-in-time non classificabile, anno per anno, con motivo e (se disponibile) nome e uscita da Wikipedia"),
        "Copertura_dati": (cov, "Copertura prezzi dei membri point-in-time dell'indice, anno per anno"),
        "Top3_per_anno": (top3, "Top-3 performer per anno (rendimento totale), S&P 500 e Nasdaq-100, dal 1990, con flag di qualita"),
        "Riparazioni_dati": (p_repairs, "Giorni con aggiustamenti societari incoerenti riparati automaticamente (vedi panel.py)"),
        "Replica_thread": (pd.read_csv(OUT / "B_replication.csv"), "Fase B - Replica del thread (lordo, USD)"),
        "Lordo_netto": (c, "Fase C - Dal lordo al netto: costi, fisco italiano, bollo, valuta, veicolo lordista; benchmark ETF"),
        "Protocolli": (g1, "Fase G1 - Protocolli candidati, netto fisco IT, EUR"),
        "Rendimenti_annui": (ann, "Rendimenti annui netti (EUR) dei protocolli e dei benchmark, 2009-2026 YTD"),
        "Varianti": (d, "Fase D - Varianti: top-N, stop, dopo-stop, lookback/ribilanciamento, mantenimento vincitori (netto EUR)"),
        "LEAPS": (l, "Fase D - LEAPS prezzate con Black-Scholes (IV = vol realizzata x moltiplicatore), netto EUR"),
        "Test_rank_calendario": (pd.read_csv(OUT / "E_rank_tests_calendar.csv"), "Fase E - Rendimento dell'anno successivo per posizione in classifica (anno solare)"),
        "Test_rank_mensile": (pd.concat([pd.read_csv(OUT / f) for f in ("E_rank_tests_monthly_SPX_1996.csv", "E_rank_tests_monthly_SPX_2008.csv", "E_rank_tests_monthly_NDX_2008.csv")]),
                              "Fase E - Test senza calendario: formazione a ogni fine mese, t di Newey-West (11 lag)"),
        "Rank_per_mese_formazione": (pd.read_csv(OUT / "E_rank_monthly_by_formation_month_SPX.csv"), "Extra-rendimento a 12 mesi del n.1 / top-3 / decile per mese di formazione (S&P 500, 1996-2025)"),
        "Timing_luck": (tl, "Fase G5 - Stessa regola annuale con 12 mesi di partenza diversi + portafoglio a 12 tranche"),
        "Finestre_10y": (roll, "Fase G2 - Finestre mobili di 10 anni (netto EUR) vs S&P 500 ETF"),
        "Bootstrap": (pd.read_csv(OUT / "E_bootstrap.csv"), "Fase E - Bootstrap dei rendimenti annui netti: esiti a 10 e 20 anni (anni interi 1997/2009-2025)"),
        "Concentrazione": (conc, "Fase E - Ricchezza residua togliendo gli anni migliori (lordo)"),
        "Placebo": (pd.read_csv(OUT / "E_placebo.csv"), "Fase E - Placebo: scelta casuale tra rank 2-10 / membri casuali / top-3 casuale"),
        "Walk_forward_F": (pd.read_csv(OUT / "F_walkforward.csv"), "Fase F - Selezione walk-forward della configurazione (miglior Calmar storico)"),
        "Griglia_F": (pd.read_csv(OUT / "F_grid_full_sample.csv"), "Fase F - Griglia 2009-2026 YTD (84 configurazioni, solo gennaio)"),
        "Core_satellite_G4": (cs, "Fase G4 - ETF S&P 500 + satellite momentum (partenza gennaio), senza ribilanciamento tra le due parti"),
        "Fattori": (pd.read_csv(OUT / "E_factor_regressions.csv"), "Regressioni CAPM e Fama-French 3 + Momentum (lordo USD, mensile, errori HAC)"),
    }
    dsr = json.load(open(OUT / "F_deflated_sharpe.json"))
    sheets["Walk_forward_F"] = (pd.read_csv(OUT / "F_walkforward.csv").assign(nota=f"Deflated Sharpe del migliore su {dsr['n_trials']} prove: {dsr['dsr']:.3f}"),
                                sheets["Walk_forward_F"][1])
    write_excel(sheets, OUT / "GRMS_JanuaryBuy_Risultati.xlsx")
    top3.to_csv(OUT / "top3_per_anno.csv", index=False)
    cov.to_csv(OUT / "copertura_dati.csv", index=False)
    print("ok")


if __name__ == "__main__":
    main()
