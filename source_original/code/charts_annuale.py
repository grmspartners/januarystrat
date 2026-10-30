"""Charts for the annual study (GRMS palette)."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

from config import OUT
from make_report import BENCH, BLUE, BRONZE, CH, GREEN, INK, INK2, RED, VIOLET, pct, save

COST, CG = 0.001, 0.26
STRATS = [("Solo vincitore, senza stop", BLUE, "--"), ("Solo vincitore, stop 35%", BRONZE, "-"),
          ("Prime tre, senza stop", GREEN, "--"), ("Prime tre, stop 35%", GREEN, "-"),
          ("Vincitore: 35% LEAPS + 65% azione con stop", VIOLET, "-")]


def main():
    d = pd.read_pickle(OUT / "AN_paths.pkl")["paths"]
    ann = pd.read_csv(OUT / "AN_rendimenti_annui.csv")
    years = [1996] + ann.anno.tolist()
    per = "1997-2026 (YTD)"
    for vista, fname, ttl in (("Lordo", "fig20_annuale_lordo.png", "LORDO: valore di 100 dollari (nessun costo, nessuna imposta)"),
                              ("Nettista", "fig21_annuale_nettista.png", "NETTISTA: valore di 100 dollari dopo le imposte italiane")):
        fig, ax = plt.subplots(figsize=(9, 4.6))
        if vista == "Lordo":
            b = [100] + d[(per, "S&P 500 (indice Total Return)", "Lordo")]
            blab = "S&P 500 Total Return"
        else:
            raw = np.array(d[(per, "S&P 500 ETF, compra e tieni", "Nettista")])
            liq = raw * (1 - COST)
            liq = liq - CG * np.maximum(liq - 100, 0)
            b = [100] + list(liq)
            blab = "ETF S&P 500 compra e tieni (valore se venduto)"
        ax.plot(years, b, color=BENCH, lw=2.0, ls="-", label=blab)
        ends = [(b[-1], BENCH)]
        for s, col, ls in STRATS:
            v = [100] + d[(per, s, vista)]
            ax.plot(years, v, color=col, ls=ls, lw=1.5, label=s.replace("Vincitore: ", "Vincitore "))
            ends.append((v[-1], col))
        # end labels without overlaps (log spacing)
        ends.sort()
        ypos, last = [], None
        for val, col in ends:
            y = val if last is None else max(val, last * 1.45)
            ypos.append((val, y, col))
            last = y
        for val, y, col in ypos:
            ax.annotate(f"${val:,.0f}", (years[-1], val), xytext=(years[-1] + 0.4, y), textcoords="data", fontsize=7.5,
                        color=col if col != BENCH else INK, va="center")
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        ax.set_xlim(1996, 2029)
        ax.set_title(ttl + ", fine 1996 - 9 ott 2026")
        ax.legend(fontsize=7.5, loc="upper left")
        save(fig, fname)

    # annual returns
    fig, ax = plt.subplots(figsize=(10, 4.2))
    x = np.arange(len(ann))
    w = 0.27
    series = [("SP500_TR", BENCH, "S&P 500"), ("top1_con_stop", BRONZE, "Solo vincitore, stop 35%"), ("top3_con_stop", GREEN, "Prime tre, stop 35%")]
    cap = 2.5
    for i, (col, c, lab) in enumerate(series):
        y = ann[col].values
        ax.bar(x + (i - 1) * w, np.clip(y, -1, cap), width=w - 0.02, color=c, label=lab)
        for k, v in enumerate(y):
            if v > cap:
                ax.text(x[k] + (i - 1) * w, cap + 0.05, f"{v:+.0%}", rotation=90, fontsize=6.5, ha="center", va="bottom", color=INK)
    ax.axhline(0, color=INK2, lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([str(a) if a != 2026 else "2026*" for a in ann.anno], rotation=90, fontsize=7.5)
    ax.set_ylim(-0.75, cap + 0.9)
    pct(ax)
    ax.set_title("Rendimento lordo di ogni anno di detenzione (asse tagliato a +250%; *2026 da inizio anno)")
    ax.legend(fontsize=8, loc="upper left", ncol=3)
    save(fig, "fig22_rendimenti_annui.png")

    # lordo / lordista / nettista CAGR 1997-2025
    s = pd.read_csv(OUT / "AN_sintesi.csv")
    s = s[s.periodo == "1997-2025"]
    names = [n for n, _, _ in STRATS[:4]] + ["Vincitore: 35% LEAPS + 65% azione", "Vincitore: 35% LEAPS + 65% azione con stop"]
    short = ["Vincitore", "Vincitore\nstop 35%", "Prime tre", "Prime tre\nstop 35%", "LEAPS 35/65", "LEAPS 35/65\nstop 35%"]
    fig, ax = plt.subplots(figsize=(9.5, 4.0))
    x = np.arange(len(names))
    for i, (v, c) in enumerate((("Lordo", "#d8b48a"), ("Lordista", BRONZE), ("Nettista", "#6e4419"))):
        vals = [s[(s.strategia == n) & (s.vista == v)].cagr.iat[0] for n in names]
        ax.bar(x + (i - 1) * 0.27, vals, width=0.25, color=c, label=v)
        for k, val in enumerate(vals):
            ax.text(x[k] + (i - 1) * 0.27, val + (0.004 if val >= 0 else -0.012), f"{val:.1%}".replace(".", ","), ha="center", fontsize=6.5, color=INK)
    spg = s[s.strategia == "S&P 500 (indice Total Return)"].cagr.iat[0]
    spn = s[(s.strategia == "S&P 500 ETF, compra e tieni") & (s.vista == "Nettista")].cagr.iat[0]
    ax.axhline(spg, color=BENCH, ls="--", lw=1.2, label=f"S&P 500 lordo ({spg:.1%})".replace(".", ","))
    ax.axhline(spn, color=INK, ls=":", lw=1.2, label=f"ETF S&P 500 netto ({spn:.1%})".replace(".", ","))
    ax.set_xticks(x)
    ax.set_xticklabels(short, fontsize=8)
    pct(ax)
    ax.set_title("CAGR 1997-2025 (anni interi): lordo, lordista, nettista")
    ax.legend(fontsize=7.5, loc="upper right", ncol=2)
    save(fig, "fig23_lordo_lordista_nettista.png")
    print("ok")


if __name__ == "__main__":
    main()
