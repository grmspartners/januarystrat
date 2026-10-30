"""Markdown tables for the board paper, generated from the output CSVs (no hand transcription)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from config import OUT
from names import company


def pct(x, d=1, sign=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n.d."
    s = f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%"
    return s.replace(".", ",")


def num(x, d=0):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n.d."
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(out)


def nm(label):
    n = company(label) or label
    return n.replace(" (serie ricostruita)", "*")


def main():
    T = {}
    dec = json.load(open(OUT / "FD_decision.json"))
    # ---- T1 top-3 S&P 500
    t3 = pd.read_csv(OUT / "top3_by_year.csv")
    t3 = t3[(t3["index"] == "SPX") & (t3.year >= 1996)]
    rows = []
    for y, g in t3.groupby("year"):
        g = g.sort_values("rank")
        cells = [f"{nm(r.label)} ({pct(r.total_return, 0, True)})" for r in g.itertuples()]
        rows.append({"Anno": y, "1°": cells[0], "2°": cells[1], "3°": cells[2],
                     "Anno dopo, 1° (%)": pct(g.iloc[0].next_year_return, 1, True) if np.isfinite(g.iloc[0].next_year_return) else "in corso",
                     "Copertura prezzi, anno intero (%)": pct(g.iloc[0].coverage, 0)})
    T["top3"] = md(pd.DataFrame(rows))
    # ---- T1b NDX top-3 (point in time from 2007)
    n3 = pd.read_csv(OUT / "top3_by_year.csv")
    n3 = n3[(n3["index"] == "NDX") & (n3.year >= 2007)]
    rows = []
    for y, g in n3.groupby("year"):
        g = g.sort_values("rank")
        cells = [f"{nm(r.label)} ({pct(r.total_return, 0, True)})" for r in g.itertuples()]
        rows.append({"Anno": y, "1°": cells[0], "2°": cells[1], "3°": cells[2],
                     "Anno dopo, 1° (%)": pct(g.iloc[0].next_year_return, 1, True) if np.isfinite(g.iloc[0].next_year_return) else "in corso"})
    T["top3_ndx"] = md(pd.DataFrame(rows))
    # ---- T2 titoli spariti
    st = pd.read_csv(OUT / "SP1_top3_stato.csv")
    g = st[st.quotata_oggi == "no"].copy()
    g = g.drop_duplicates(["indice", "anno", "ticker"])
    rows = []
    for r in g.itertuples():
        rows.append({"Indice": "S&P 500" if r.indice == "SPX" else "Nasdaq-100", "Anno": r.anno, "Pos.": r.pos,
                     "Società": r.societa.replace(" (serie ricostruita)", "*"),
                     "Rend. anno (%)": pct(r.rendimento_anno, 0, True), "Anno dopo (%)": pct(r.rendimento_anno_successivo, 1, True),
                     "Esito societario": r.esito_societario})
    T["spariti"] = md(pd.DataFrame(rows))
    # ---- T3 patches
    sp3 = pd.read_csv(OUT / "SP3_vincitori_reinseriti.csv")
    rows = []
    for r in sp3.itertuples():
        rows.append({"Anno classifica": r.anno_classifica, "Società": r.societa, "Rend. anno (%)": pct(r.rendimento_anno_classifica, 1, True),
                     "Anno detenzione (%)": pct(r.rendimento_anno_detenzione, 1, True), "Stop 35%": r.stop_35_toccato,
                     "Fonti": r.fonti})
    T["patch"] = md(pd.DataFrame(rows))
    # ---- T4 replication
    b = pd.read_csv(OUT / "B_replication.csv")
    thread = {("thread 15y (2012-2026)", "winner top1 stop=None -"): "176.114", ("thread 30y (1997-2026)", "winner top1 stop=None -"): "89.418",
              ("thread 30y (1997-2026)", "winner top1 stop=0.35 intraday"): "1.514.581", ("thread 15y (2012-2026)", "S&P 500 TR (gross)"): "800",
              ("thread 30y (1997-2026)", "S&P 500 TR (gross)"): "1.752"}
    rows = []
    for r in b.itertuples():
        if r.name == "winner top1 stop=0.35 close" or (r.sample.startswith("thread 15y") and "stop=0.35" in r.name):
            continue
        if r.sample.startswith("thread 30y") and r.data == "raw" and r.name != "S&P 500 TR (gross)":
            continue
        lab = {"winner top1 stop=None -": "Vincitore anno precedente, senza stop", "winner top1 stop=0.35 intraday": "Vincitore + stop 35%",
               "S&P 500 TR (gross)": "S&P 500 Total Return"}[r.name]
        rows.append({"Periodo": "2012 - 9 ott 2026" if "15y" in r.sample else "1997 - 9 ott 2026", "Strategia": lab,
                     "Valore finale di 100 USD (studio)": num(r.final), "Valore indicato nel thread (USD)": thread.get((r.sample, r.name), "-"),
                     "CAGR (%)": pct(r.cagr), "Max drawdown (%)": pct(r.max_dd)})
    T["replica"] = md(pd.DataFrame(rows))
    # ---- T5 gross to net
    c = pd.read_csv(OUT / "C_gross_to_net.csv")
    rows = []
    for smp, lab in (("core 2009-2026YTD", "2009 - 9 ott 2026"), ("long 1997-2026YTD", "1997 - 9 ott 2026")):
        x = c[(c["sample"] == smp) & (c.kind == "strategy") & (c.top_n == 1) & (c.stop == 0.35)]
        def g_(pr, ccy, col="cagr_after_liq"):
            return x[(x.preset == pr) & (x.ccy == ccy)].iloc[0][col]
        bh = c[(c["sample"] == smp) & (c.name == "SPX ETF bh") & (c.ccy == "EUR")].iloc[0]
        rows.append({"Periodo": lab, "Lordo USD (%)": pct(g_("gross", "USD", "cagr")), "Con costi e T-bill, USD (%)": pct(g_("gross_cost", "USD", "cagr")),
                     "Netto fisco IT, USD (%)": pct(g_("net_it", "USD")), "Netto fisco IT, EUR (%)": pct(g_("net_it", "EUR")),
                     "Veicolo a imposizione differita, EUR (%)": pct(g_("deferred", "EUR")),
                     "S&P 500 ETF buy & hold, netto EUR (%)": pct(bh.cagr_after_liq)})
    T["lordo_netto"] = md(pd.DataFrame(rows))
    rows = []
    for smp, lab in (("core 2009-2026YTD", "2009 - 9 ott 2026"), ("long 1997-2026YTD", "1997 - 9 ott 2026")):
        x = c[(c["sample"] == smp) & (c.kind == "strategy") & (c.top_n == 1) & (c.stop == 0.35) & (c.ccy == "EUR")]
        gr = x[x.preset == "gross"].iloc[0].final
        nt = x[x.preset == "net_it"].iloc[0]
        df_ = x[x.preset == "deferred"].iloc[0]
        rows.append({"Periodo": lab, "Valore finale lordo (EUR)": num(gr), "Valore finale netto, regime amministrato (EUR)": num(nt.final_after_liq),
                     "Imposte pagate nel tempo (EUR)": num(nt.tax_paid), "Minusvalenze scadute inutilizzate (EUR)": num(nt.losses_wasted),
                     "Valore finale, imposizione differita (EUR)": num(df_.final_after_liq)})
    T["lordo_netto_eur"] = md(pd.DataFrame(rows))
    # ---- T6 ETF annual vs bh
    rows = []
    for smp, lab in (("core 2009-2026YTD", "2009 - 9 ott 2026"), ("long 1997-2026YTD", "1997 - 9 ott 2026")):
        for which, wl in (("SPX", "S&P 500"), ("NDX", "Nasdaq-100")):
            if which == "NDX" and smp.startswith("long"):
                continue
            x = c[(c["sample"] == smp) & (c.kind == "benchmark") & (c.ccy == "EUR") & c.name.str.startswith(which)]
            bh = x[x.name == f"{which} ETF bh"].iloc[0]
            an = x[x.name == f"{which} ETF annual"].iloc[0]
            rows.append({"Periodo": lab, "ETF": wl, "Buy & hold: valore finale netto (EUR)": num(bh.final_after_liq),
                         "Buy & hold: CAGR netto (%)": pct(bh.cagr_after_liq),
                         "Vendi e ricompra ogni anno: valore finale netto (EUR)": num(an.final_after_liq),
                         "Vendi e ricompra: CAGR netto (%)": pct(an.cagr_after_liq),
                         "Costo fiscale della rotazione (punti CAGR)": num((bh.cagr_after_liq - an.cagr_after_liq) * 100, 1)})
    T["etf_annual"] = md(pd.DataFrame(rows))
    # ---- T7 top-N x stop
    d = pd.read_csv(OUT / "D_variants.csv")
    rows = []
    for fy, lab in ((2009, "2009 - 9 ott 2026"), (1997, "1997 - 9 ott 2026")):
        for top in (1, 2, 3, 5, 10):
            rec = {"Periodo": lab, "Titoli": top}
            for stv, sl in (("None", "nessuno"), ("0.15", "15%"), ("0.25", "25%"), ("0.35", "35%"), ("0.5", "50%")):
                r = d[d.name == f"D1 SPX {fy} top{top} stop{stv}"].iloc[0]
                rec[f"Stop {sl}: CAGR (%)"] = pct(r.cagr_after_liq)
            rows.append(rec)
    T["topn_stop"] = md(pd.DataFrame(rows))
    # ---- T8 horizons
    rows = []
    for lb, hold in ((12, 12), (12, 6), (6, 6), (6, 12), (12, 3), (12, 1), (6, 1), (3, 1), (1, 1)):
        rec = {"Finestra di classifica (mesi)": lb, "Ribilanciamento (mesi)": hold}
        for top in (1, 3, 5):
            r = d[d.name == f"D4 lb{lb} hold{hold} top{top} stopNone"].iloc[0]
            rec[f"Top-{top} senza stop (%)"] = pct(r.cagr_after_liq)
        r = d[d.name == f"D4 lb{lb} hold{hold} top1 stop0.35"].iloc[0]
        rec["Top-1 stop 35% (%)"] = pct(r.cagr_after_liq)
        rows.append(rec)
    T["orizzonti"] = md(pd.DataFrame(rows))
    # ---- T9 LEAPS
    lp = pd.read_csv(OUT / "LP_sintesi.csv")
    rows = []
    for r in lp.itertuples():
        rows.append({"Periodo": r.campione.replace("core 2009-2026YTD", "2009 - 9 ott 2026").replace("long 1997-2026YTD", "1997 - 9 ott 2026"),
                     "Strategia": r.strategia.replace("buy & hold", "buy & hold"), "CAGR netto, partenza gennaio (%)": pct(r.cagr_netto),
                     "CAGR netto, 12 tranche (%)": pct(r.cagr_12_tranche) if np.isfinite(r.cagr_12_tranche) else "-",
                     "Max drawdown (%)": pct(r.max_drawdown), "Peggior anno (%)": pct(r.peggior_anno)})
    T["leaps"] = md(pd.DataFrame(rows))
    # ---- T10 rank tests
    cal = pd.read_csv(OUT / "E_rank_tests_calendar.csv")
    mon = pd.read_csv(OUT / "E_rank_tests_monthly_SPX_1996.csv")
    rows = []
    for k in list(range(1, 6)) + ["1-3 avg"]:
        rc = cal[(cal["sample"] == "SPX 1996-2024") & (cal["rank"].astype(str) == str(k))].iloc[0]
        key = f"r{k}" if k != "1-3 avg" else "top3"
        rm = mon[mon.portfolio == key].iloc[0]
        rows.append({"Posizione": "media 1°-3°" if k == "1-3 avg" else f"{k}°",
                     "Calendario: extra-rend. medio (%)": pct(rc.mean_excess, 1, True), "Calendario: mediano (%)": pct(rc.median_excess, 1, True),
                     "Calendario: t": num(rc.t_stat, 2), "Calendario: IC 95% bootstrap": f"{pct(rc.ci95_lo, 1, True)} / {pct(rc.ci95_hi, 1, True)}",
                     "Tutti i mesi: extra-rend. medio (%)": pct(rm.mean_excess_12m, 1, True), "Tutti i mesi: t Newey-West": num(rm.nw_t, 2)})
    T["rank"] = md(pd.DataFrame(rows))
    # ---- T11 start months
    sl = pd.read_csv(OUT / "FD_sleeves.csv").set_index("config")
    es = pd.read_csv(OUT / "FD_etf_sleeves.csv", index_col=0)
    mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    rows = []
    for v, lab in (("core", "2009-2026"), ("long", "1997-2026")):
        for cfg, cl in (("top1 stop35", "Top-1 stop 35%"), (dec["satellite_rule"], "Top-2 stop 35% mantieni")):
            rec = {"Periodo": lab, "Regola": cl}
            for m in range(12):
                rec[mesi[m]] = pct(sl.loc[cfg, f"{v}_m{m + 1:02d}"], 0)
            rows.append(rec)
        rec = {"Periodo": lab, "Regola": "S&P 500 ETF"}
        for m in range(12):
            rec[mesi[m]] = pct(es.iloc[m][v], 0)
        rows.append(rec)
    T["mesi"] = md(pd.DataFrame(rows))
    # ---- T12 grid top configs (standalone, 12 tranche)
    gr = pd.read_csv(OUT / "FS_grid_tranche.csv").sort_values("score_worst_excess", ascending=False)
    bench = pd.read_csv(OUT / "FS_benchmark_tranche.csv").set_index("view")
    rows = [{"Regola (12 tranche)": "S&P 500 ETF buy & hold", "2009-2026 CAGR (%)": pct(bench.loc["core", "cagr"]),
             "1997-2026 CAGR (%)": pct(bench.loc["long", "cagr"]), "2009-2025 CAGR (%)": pct(bench.loc["core_fy", "cagr"]),
             "1997-2025 CAGR (%)": pct(bench.loc["long_fy", "cagr"]), "Max DD 2009-2026 (%)": pct(bench.loc["core", "maxdd"]),
             "Max DD 1997-2026 (%)": pct(bench.loc["long", "maxdd"]), "Extra-rend. nel periodo peggiore (punti)": "-"}]
    for r in gr.head(8).itertuples():
        rows.append({"Regola (12 tranche)": r.config, "2009-2026 CAGR (%)": pct(r.core_cagr), "1997-2026 CAGR (%)": pct(r.long_cagr),
                     "2009-2025 CAGR (%)": pct(r.core_fy_cagr), "1997-2025 CAGR (%)": pct(r.long_fy_cagr),
                     "Max DD 2009-2026 (%)": pct(r.core_maxdd), "Max DD 1997-2026 (%)": pct(r.long_maxdd),
                     "Extra-rend. nel periodo peggiore (punti)": num(r.score_worst_excess * 100, 1)})
    for name in ("top1 stop35 regime keep", "top3 stop35 regime"):
        r = gr[gr.config == name].iloc[0]
        rows.append({"Regola (12 tranche)": r.config, "2009-2026 CAGR (%)": pct(r.core_cagr), "1997-2026 CAGR (%)": pct(r.long_cagr),
                     "2009-2025 CAGR (%)": pct(r.core_fy_cagr), "1997-2025 CAGR (%)": pct(r.long_fy_cagr),
                     "Max DD 2009-2026 (%)": pct(r.core_maxdd), "Max DD 1997-2026 (%)": pct(r.long_maxdd),
                     "Extra-rend. nel periodo peggiore (punti)": num(r.score_worst_excess * 100, 1)})
    T["griglia"] = md(pd.DataFrame(rows))
    # ---- T13 frontier
    fr = pd.read_csv(OUT / "FD_frontier.csv").head(10)
    rows = []
    for r in fr.itertuples():
        rows.append({"Regola satellite": r.config, "Quota massima ammessa (%)": pct(r.weight_satellite, 0),
                     "Extra-rend. nel periodo peggiore (punti)": num(r.worst_excess * 100, 2),
                     "Scostamento max DD vs ETF, periodo peggiore (punti)": num(r.worst_dd_gap * 100, 1)})
    T["frontiera"] = md(pd.DataFrame(rows))
    # ---- T14 recommended allocation 4 views
    cs = pd.read_csv(OUT / "FD_core_satellite.csv")
    sat, w = dec["satellite_rule"], dec["weight_recommended"]
    rows = []
    for v, lab in (("core", "2009 - 9 ott 2026"), ("long", "1997 - 9 ott 2026"), ("core_fy", "2009 - 2025"), ("long_fy", "1997 - 2025")):
        rec = {"Periodo": lab}
        for ww, wl in ((0.0, "ETF 100%"), (w, f"{int((1 - w) * 100)}/{int(w * 100)} raccomandato"), (dec["weight_cap"], f"{int((1 - dec['weight_cap']) * 100)}/{int(dec['weight_cap'] * 100)} tetto"), (1.0, "Satellite 100%")):
            x = cs[(cs.config == sat) & np.isclose(cs.weight_satellite, ww)].iloc[0]
            rec[f"{wl}: CAGR (%)"] = pct(x[f"{v}_cagr"])
            rec[f"{wl}: max DD (%)"] = pct(x[f"{v}_maxdd"])
        rows.append(rec)
    T["raccomandata"] = md(pd.DataFrame(rows))
    # ---- T14b rebalanced mixes
    rb = pd.read_csv(OUT / "FD_rebalanced_mix.csv")
    rows = []
    for ww in (0.2, 0.3, 0.4, 0.5):
        x = rb[(rb.config == sat) & np.isclose(rb.weight, ww) & np.isclose(rb.band, 0.05)].iloc[0]
        rows.append({"Satellite (peso obiettivo)": pct(ww, 0), "2009-2026 CAGR (%)": pct(x.core_cagr), "1997-2026 CAGR (%)": pct(x.long_cagr),
                     "2009-2025 CAGR (%)": pct(x.core_fy_cagr), "1997-2025 CAGR (%)": pct(x.long_fy_cagr),
                     "Max DD 2009-2026 (%)": pct(x.core_maxdd), "Max DD 1997-2026 (%)": pct(x.long_maxdd),
                     "Extra-rend. periodo peggiore (punti)": num(x.worst_excess * 100, 1), "Scostamento DD vs ETF (punti)": num(x.worst_dd_gap * 100, 1)})
    T["ribilanciata"] = md(pd.DataFrame(rows))
    # ---- T15 sub-periods and stress years
    a = pd.read_csv(OUT / "FD_annual.csv", header=[0, 1], index_col=0)
    rows = []
    for v, per in (("long", (1998, 2008)), ("long", (2009, 2023)), ("long", (2024, 2026))):
        sub = a.loc[per[0]:per[1], v]
        n = per[1] - per[0] + (0.77 if per[1] == 2026 else 1)
        gm = (1 + sub.fillna(0)).prod()
        lab = f"{per[0]}-{per[1]}" + (" (YTD)" if per[1] == 2026 else "")
        rows.append({"Sotto-periodo": lab, "S&P 500 ETF (% annuo)": pct(gm["S&P 500 ETF"] ** (1 / n) - 1),
                     f"{int((1 - w) * 100)}/{int(w * 100)} (% annuo)": pct(gm[f"mix {int(w * 100)}% satellite"] ** (1 / n) - 1),
                     "Satellite 12 tranche (% annuo)": pct(gm["satellite 12 tranches"] ** (1 / n) - 1),
                     "Regola del thread, solo gennaio (% annuo)": pct(gm["satellite January only"] ** (1 / n) - 1)})
    T["sottoperiodi"] = md(pd.DataFrame(rows))
    rows = []
    for y in (2000, 2001, 2002, 2008, 2011, 2015, 2018, 2022, 2024, 2025, 2026):
        v = "long"        # tranche portfolios fully invested from 1998 in the long view
        rr = a.loc[y, v]
        rows.append({"Anno": f"{y}" + (" (YTD)" if y == 2026 else ""), "S&P 500 ETF (%)": pct(rr["S&P 500 ETF"], 1, True),
                     f"{int((1 - w) * 100)}/{int(w * 100)} (%)": pct(rr[f"mix {int(w * 100)}% satellite"], 1, True),
                     "Satellite 12 tranche (%)": pct(rr["satellite 12 tranches"], 1, True),
                     "Regola del thread, gennaio (%)": pct(rr["satellite January only"], 1, True)})
    T["anni_chiave"] = md(pd.DataFrame(rows))
    # ---- T16 walk-forward summary
    wf = pd.read_csv(OUT / "FD_walkforward.csv")
    T["wf"] = (f"CAGR walk-forward {pct(dec['wf_cagr'])}, regola scelta fissa {pct(dec['wf_rule_cagr'])}, ETF {pct(dec['wf_etf_cagr'])} (2007-2026 YTD)")
    # ---- signals
    import patches as _p
    from panel import Panel
    from signals import ranking
    p = _p.apply(Panel.load())
    me = p.month_end_rows()
    last = len(p.dates) - 1
    oct25 = [x for x in me if p.dates[x].year == 2025 and p.dates[x].month == 10][0]
    rk = ranking(p, "SPX", last, oct25, min_days=126).head(5)
    rk2 = pd.read_csv(OUT / "FD_classifica_2026YTD.csv").head(5)
    rows = []
    for i in range(5):
        rows.append({"Pos.": i + 1, "Tranche di novembre 2026 (12 mesi dal 31-10-2025)": f"{company(rk.label.iloc[i])} ({pct(rk.mom.iloc[i], 0, True)})",
                     "Tranche di gennaio 2027 (anno solare 2026)": f"{rk2.societa.iloc[i]} ({pct(rk2.mom.iloc[i], 0, True)})"})
    T["segnali"] = md(pd.DataFrame(rows))
    sig = pd.read_csv(OUT / "FD_segnali_tranche.csv")
    conc = sig.groupby("ticker").tranche.nunique().sort_values(ascending=False)
    T["conc"] = ", ".join(f"{company(k)} {v}" for k, v in conc.items())
    json.dump(T, open(OUT / "paper_tables.json", "w"), ensure_ascii=False, indent=0)
    for k, v in T.items():
        print("=====", k)
        print(v[:3000])


if __name__ == "__main__":
    main()
