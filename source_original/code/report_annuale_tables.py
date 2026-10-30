"""Markdown tables for the annual-study report (generated from the CSV outputs)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from annual_study import run_lordista, run_lordo, run_nettista, LEAPS_W
from config import OUT
from paper_tables import md, num, pct

ORDER = ["Solo vincitore, senza stop", "Solo vincitore, stop 35%", "Prime tre, senza stop", "Prime tre, stop 35%",
         "Vincitore: 35% LEAPS + 65% azione", "Vincitore: 35% LEAPS + 65% azione con stop"]


def main():
    T = {}
    s = pd.read_csv(OUT / "AN_sintesi.csv")
    ann = pd.read_csv(OUT / "AN_rendimenti_annui.csv")
    t3 = pd.read_csv(OUT / "AN_top3_anno.csv")
    roll = pd.read_csv(OUT / "AN_finestre_10anni.csv")

    def g(per, strat, vista, col):
        x = s[(s.periodo == per) & (s.strategia == strat) & (s.vista == vista)]
        return x[col].iat[0] if len(x) else np.nan

    # ---- main summary per period
    for per, key in (("1997-2025", "sintesi_9725"), ("1997-2026 (YTD)", "sintesi_9726")):
        rows = [{"Strategia": "S&P 500", "Lordo: CAGR": pct(g(per, "S&P 500 (indice Total Return)", "Lordo", "cagr")),
                 "Lordista: CAGR": pct(g(per, "S&P 500 ETF, compra e tieni", "Lordista", "cagr")),
                 "Nettista: CAGR": pct(g(per, "S&P 500 ETF, compra e tieni", "Nettista", "cagr")),
                 "Nettista: 100 $ diventano": num(g(per, "S&P 500 ETF, compra e tieni", "Nettista", "valore_finale")),
                 "Peggior anno (lordo)": pct(g(per, "S&P 500 (indice Total Return)", "Lordo", "peggior_anno")),
                 "Max calo da picco, fine anno (lordo)": pct(g(per, "S&P 500 (indice Total Return)", "Lordo", "max_drawdown_fine_anno"))}]
        for st in ORDER:
            rows.append({"Strategia": st.replace("Vincitore: ", "Vincitore, "), "Lordo: CAGR": pct(g(per, st, "Lordo", "cagr")),
                         "Lordista: CAGR": pct(g(per, st, "Lordista", "cagr")), "Nettista: CAGR": pct(g(per, st, "Nettista", "cagr")),
                         "Nettista: 100 $ diventano": num(g(per, st, "Nettista", "valore_finale")),
                         "Peggior anno (lordo)": pct(g(per, st, "Lordo", "peggior_anno")),
                         "Max calo da picco, fine anno (lordo)": pct(g(per, st, "Lordo", "max_drawdown_fine_anno"))})
        T[key] = md(pd.DataFrame(rows))
    # ---- sub-periods (lordo and nettista)
    rows = []
    for st_lab, st_l, st_n in [("S&P 500", "S&P 500 (indice Total Return)", "S&P 500 ETF, compra e tieni")] + [(o.replace("Vincitore: ", "Vincitore, "), o, o) for o in ORDER]:
        rec = {"Strategia": st_lab}
        for per in ("1997-2008", "2009-2025", "2009-2026 (YTD)"):
            rec[f"{per} lordo"] = pct(g(per, st_l, "Lordo", "cagr"))
            rec[f"{per} nettista"] = pct(g(per, st_n, "Nettista", "cagr"))
        rows.append(rec)
    T["sottoperiodi"] = md(pd.DataFrame(rows))
    # ---- top-3 table
    rows = []
    for T0, gg in t3.groupby("anno_T0"):
        gg = gg.sort_values("posizione")
        cells = []
        for r in gg.itertuples():
            name = r.societa.replace(" (serie ricostruita)", "*")
            nxt = pct(r.rend_T1_senza_stop, 0, True)
            if r.stop_toccato:
                nxt += f" (stop: {pct(r.rend_T1_con_stop, 0, True)})"
            cells.append(f"{name}: {pct(r.rend_T0, 0, True)} → {nxt}")
        rows.append({"Anno T0": T0, "1° classificato": cells[0], "2° classificato": cells[1], "3° classificato": cells[2]})
    T["top3"] = md(pd.DataFrame(rows))
    # ---- annual portfolio returns
    rows = []
    for r in ann.itertuples():
        rows.append({"Anno": f"{r.anno}" + ("*" if r.anno == 2026 else ""), "S&P 500": pct(r.SP500_TR, 1, True),
                     "Vincitore": pct(r.top1_senza_stop, 1, True), "Vincitore, stop": pct(r.top1_con_stop, 1, True),
                     "Prime tre": pct(r.top3_senza_stop, 1, True), "Prime tre, stop": pct(r.top3_con_stop, 1, True),
                     "Fermati su 3": r.titoli_fermati_top3, "LEAPS 35/65": pct(r.leaps35_azione65, 1, True),
                     "LEAPS 35/65, stop": pct(r.leaps35_azione65_stop, 1, True)})
    T["annui"] = md(pd.DataFrame(rows))
    # ---- rolling windows summary
    rows = []
    for st in ORDER:
        rec = {"Strategia": st.replace("Vincitore: ", "Vincitore, ")}
        for v, base in (("lordo", roll.SP500_lordo), ("nettista", roll.SP500_ETF_nettista)):
            ex = roll[f"{st} | {v}"] - base
            rec[f"{v}: finestre sopra S&P (su 20)"] = int((ex > 0).sum())
            rec[f"{v}: extra-rend. medio (punti)"] = num(ex.mean() * 100, 1)
            rec[f"{v}: peggiore (punti)"] = num(ex.min() * 100, 1)
        rows.append(rec)
    T["finestre"] = md(pd.DataFrame(rows))
    # ---- LEAPS sensitivity (1997-2025 and 2009-2025)
    rows = []
    for tag, lab in (("_ottimista", "Ottimista (IV 0,9x, spread 1%)"), ("", "Centrale (IV 1,1x, spread 3%)"), ("_prudente", "Prudente (IV 1,3x, spread 6%)"),
                     ("_2anni", "Centrale, LEAPS a 2 anni venduta dopo 1 anno")):
        for stop in (False, True):
            col = f"leaps35_azione65{'_stop' if stop else ''}{tag}"
            base = "div_top1_stop" if stop else "div_top1"
            rec = {"Ipotesi di prezzo": lab, "Stop sull'azione": "si" if stop else "no"}
            for a, b in ((1997, 2025), (2009, 2025)):
                sub = ann[(ann.anno >= a) & (ann.anno <= b)]
                rets = sub[col].tolist()
                divs = (sub[base] * (1 - LEAPS_W)).tolist()
                lo = run_lordo(rets)[-1]
                nt, _ = run_nettista(rets, divs, sub.anno.tolist())
                yrs = b - a + 1
                rec[f"{a}-{b} lordo"] = pct((lo / 100) ** (1 / yrs) - 1)
                rec[f"{a}-{b} nettista"] = pct((nt[-1] / 100) ** (1 / yrs) - 1)
            rows.append(rec)
    for stop in (False, True):
        col = "top1_con_stop" if stop else "top1_senza_stop"
        base = "div_top1_stop" if stop else "div_top1"
        rec = {"Ipotesi di prezzo": "Solo azione (confronto)", "Stop sull'azione": "si" if stop else "no"}
        for a, b in ((1997, 2025), (2009, 2025)):
            sub = ann[(ann.anno >= a) & (ann.anno <= b)]
            lo = run_lordo(sub[col].tolist())[-1]
            nt, _ = run_nettista(sub[col].tolist(), sub[base].tolist(), sub.anno.tolist())
            yrs = b - a + 1
            rec[f"{a}-{b} lordo"] = pct((lo / 100) ** (1 / yrs) - 1)
            rec[f"{a}-{b} nettista"] = pct((nt[-1] / 100) ** (1 / yrs) - 1)
        rows.append(rec)
    T["leaps_sens"] = md(pd.DataFrame(rows))
    # LEAPS per-year compact
    rows = []
    for r in ann.itertuples():
        rows.append({"Anno": f"{r.anno}" + ("*" if r.anno == 2026 else ""),
                     "Titolo": t3[(t3.anno_T0 == r.anno - 1) & (t3.posizione == 1)].societa.iat[0].replace(" (serie ricostruita)", "*"),
                     "Strike / prezzo": num(r.leaps_K_over_S, 2), "Volatilità implicita": pct(r.leaps_iv_entry, 0),
                     "Azione": pct(r.top1_senza_stop, 1, True), "Opzione": pct(r.leaps_rend_opzione, 1, True),
                     "35/65": pct(r.leaps35_azione65, 1, True), "35/65 con stop": pct(r.leaps35_azione65_stop, 1, True)})
    T["leaps_anni"] = md(pd.DataFrame(rows))
    # taxes paid
    rows = []
    for st in ORDER:
        rows.append({"Strategia": st.replace("Vincitore: ", "Vincitore, "),
                     "Lordista: 100 $ diventano": num(g("1997-2025", st, "Lordista", "valore_finale")),
                     "Nettista: 100 $ diventano": num(g("1997-2025", st, "Nettista", "valore_finale")),
                     "Imposte pagate nel tempo, nettista ($)": num(g("1997-2025", st, "Nettista", "imposte_pagate")),
                     "Minusvalenze perse per scadenza ($)": num(g("1997-2025", st, "Nettista", "minus_scadute")),
                     "Differenza di CAGR lordista - nettista (punti)": num((g("1997-2025", st, "Lordista", "cagr") - g("1997-2025", st, "Nettista", "cagr")) * 100, 1)})
    T["fisco"] = md(pd.DataFrame(rows))
    # ---- per-year returns, lordista and nettista (from the wealth paths)
    P = pd.read_pickle(OUT / "AN_paths.pkl")["paths"]
    per = "1997-2026 (YTD)"
    years = ann.anno.tolist()
    final_s = s[s.periodo == per]
    for vista, key in (("Lordista", "annui_lordista"), ("Nettista", "annui_nettista")):
        cols = [("ETF S&P 500, compra e tieni", "S&P 500 ETF, compra e tieni")]
        if vista == "Nettista":
            cols.append(("ETF S&P 500, vendi e ricompra", "S&P 500 ETF, vendi e ricompra ogni anno"))
        cols += [("Vincitore", ORDER[0]), ("Vincitore, stop", ORDER[1]), ("Prime tre", ORDER[2]), ("Prime tre, stop", ORDER[3]),
                 ("LEAPS 35/65", ORDER[4]), ("LEAPS 35/65, stop", ORDER[5])]
        rows = []
        for i, y in enumerate(years):
            rec = {"Anno": f"{y}" + ("*" if y == 2026 else "")}
            for lab, k in cols:
                path = [100.0] + list(P[(per, k, vista)])
                rec[lab] = pct(path[i + 1] / path[i] - 1, 1, True)
            rows.append(rec)
        rec = {"Anno": "100 $ diventano (valore finale)"}
        for lab, k in cols:
            rec[lab] = num(final_s[(final_s.strategia == k) & (final_s.vista == vista)].valore_finale.iat[0])
        rows.append(rec)
        T[key] = md(pd.DataFrame(rows))
    # ---- concentration (lordo, 1997-2025)
    sub = ann[ann.anno <= 2025]
    rows = []
    for lab, col, st in [("S&P 500", "SP500_TR", None)] + [(o.replace("Vincitore: ", "Vincitore, "), c, o) for o, c in
                         zip(ORDER, ["top1_senza_stop", "top1_con_stop", "top3_senza_stop", "top3_con_stop", "leaps35_azione65", "leaps35_azione65_stop"])]:
        r = sub[col].values
        best3 = np.argsort(r)[::-1][:3]
        rest = np.delete(r, best3)
        rows.append({"Strategia": lab, "CAGR lordo 1997-2025": pct(np.prod(1 + r) ** (1 / len(r)) - 1),
                     "CAGR senza i 3 anni migliori": pct(np.prod(1 + rest) ** (1 / len(rest)) - 1),
                     "I 3 anni migliori": ", ".join(str(int(sub.anno.iat[k])) for k in sorted(best3)),
                     "Anni in perdita (su 29)": int((r < 0).sum()),
                     "Anni sopra l'S&P 500 (su 29)": "-" if st is None else int((r > sub.SP500_TR.values).sum())})
    T["concentrazione"] = md(pd.DataFrame(rows))
    # ---- stop detail
    rows = []
    for r in t3[t3.stop_toccato].sort_values(["anno_detenzione", "posizione"]).itertuples():
        rows.append({"Anno di detenzione": r.anno_detenzione, "Posizione": f"{r.posizione}°",
                     "Società": r.societa.replace(" (serie ricostruita)", "*"), "Data dello stop": pd.Timestamp(r.data_stop).strftime("%d-%m-%Y"),
                     "Senza stop": pct(r.rend_T1_senza_stop, 1, True), "Con stop": pct(r.rend_T1_con_stop, 1, True),
                     "Apertura sotto lo stop": "si" if r.stop_in_gap else "no",
                     "Effetto dello stop": "ha evitato una perdita maggiore" if r.rend_T1_con_stop > r.rend_T1_senza_stop else "ha peggiorato il risultato"})
    T["stop_dettaglio"] = md(pd.DataFrame(rows))
    st_all = t3[t3.stop_toccato]
    T["n_stop_utili"] = int((st_all.rend_T1_con_stop > st_all.rend_T1_senza_stop).sum())
    T["n_stop_utili_top1"] = int(((st_all.rend_T1_con_stop > st_all.rend_T1_senza_stop) & (st_all.posizione == 1)).sum())
    # ---- numbers quoted in the text (lordista includes the AMC cost)
    drags = [(g("1997-2025", st, "Lordista", "cagr") - g("1997-2025", st, "Nettista", "cagr")) * 100 for st in ORDER]
    T["drag_min"], T["drag_max"] = num(min(drags), 1), num(max(drags), 1)
    etf_l = g("1997-2025", "S&P 500 ETF, compra e tieni", "Lordista", "cagr")
    etf_n = g("1997-2025", "S&P 500 ETF, compra e tieni", "Nettista", "cagr")
    rows = []
    for st in ORDER:
        rows.append({"Vantaggio annuo sull'ETF S&P 500, 1997-2025": st.replace("Vincitore: ", "Vincitore, "),
                     "Lordista": num((g("1997-2025", st, "Lordista", "cagr") - etf_l) * 100, 1) + " punti",
                     "Nettista": num((g("1997-2025", st, "Nettista", "cagr") - etf_n) * 100, 1) + " punti"})
    T["vantaggio"] = md(pd.DataFrame(rows))
    T["t3s_vant_l"] = num((g("1997-2025", ORDER[3], "Lordista", "cagr") - etf_l) * 100, 1)
    T["t3s_vant_n"] = num((g("1997-2025", ORDER[3], "Nettista", "cagr") - etf_n) * 100, 1)
    wl, wn = g("1997-2025", ORDER[1], "Lordista", "valore_finale"), g("1997-2025", ORDER[1], "Nettista", "valore_finale")
    T["ws_val_l"], T["ws_val_n"], T["ws_ratio"] = num(wl), num(wn), pct(wn / wl, 0)
    stops = t3[t3.stop_toccato]
    T["n_stop_top1"] = int(stops[stops.posizione == 1].shape[0])
    T["n_stop_tot"] = int(stops.shape[0])
    T["n_gap"] = int(stops.stop_in_gap.sum())
    json.dump(T, open(OUT / "report_annuale_tables.json", "w"), ensure_ascii=False, indent=0)
    for k, v in T.items():
        print("=====", k)
        print(str(v)[:2500])


if __name__ == "__main__":
    main()
