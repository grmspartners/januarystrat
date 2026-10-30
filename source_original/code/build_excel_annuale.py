"""
Excel deliverable of the annual study: out/GRMS_JanuaryBuy_Analisi_Annuale.xlsx

Live formulas wherever the arithmetic can be followed by hand (returns, portfolio averages,
LORDO and LORDISTA paths, ETF rotation); NETTISTA paths of the strategies come from the
4-year loss carry-forward ledger computed in Python (shown in the 'Zainetto' sheet).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from config import OUT
from xlsx_style import (BOX, F_BOLD, F_INPUT, F_NOTE, F_SUB, INPUT_FILL, para, sheet_from_df, title, write_table)

P = "Parametri"


def main():
    t3 = pd.read_csv(OUT / "AN_top3_anno.csv")
    ann = pd.read_csv(OUT / "AN_rendimenti_annui.csv")
    res = pd.read_csv(OUT / "AN_sintesi.csv")
    roll = pd.read_csv(OUT / "AN_finestre_10anni.csv")
    prm = json.load(open(OUT / "AN_parametri.json"))
    st = pd.read_csv(OUT / "SP1_top3_stato.csv")
    st = st[st.indice == "SPX"].set_index(["anno", "pos"])
    paths = pd.read_pickle(OUT / "AN_paths.pkl")
    years = ann.anno.tolist()            # holding years 1997..2026
    n = len(years)

    wb = Workbook()
    # ------------------------------------------------------------------ LEGGIMI
    ws = wb.active
    ws.title = "LEGGIMI"
    r = title(ws, "GRMS Partners - January Buy: analisi annuale S&P 500 (vincitore, prime tre, LEAPS; lordo, lordista, nettista)",
              f"Prezzi fino al {prm['last_date']}. Importi in dollari USA per 100 dollari investiti alla fine del 1996.")
    rows = [
        ("Domanda", "Rispetto a comprare l'S&P 500, ha senso comprare ogni anno il titolo dell'S&P 500 migliore dell'anno precedente, oppure i primi tre a 1/3 ciascuno?"),
        ("Classifica", "Anno T0 = 1996...2025: rendimento totale dell'anno solare (dividendi inclusi) dei membri dell'S&P 500 all'ultima seduta di T0. "
                       "Composizione storica point-in-time; nove vincitori assenti dai dati gratuiti reinseriti da documenti SEC (colonna 'Serie ricostruita')."),
        ("Detenzione", "Anno T0+1: acquisto all'apertura della prima seduta, vendita alla chiusura dell'ultima seduta. Il 2026 e' l'anno in corso (fino al 9 ottobre)."),
        ("Stop 35%", "Prezzo di stop = 65% del prezzo d'ingresso, controllato sul minimo di ogni giorno; esecuzione al livello o all'apertura se il titolo apre gia' sotto. "
                     "Nella versione a tre titoli lo stop agisce titolo per titolo: il titolo fermato resta in liquidita' (rendimento zero) fino a fine anno, gli altri restano investiti."),
        ("Prime tre", "1/3 del capitale su ciascun titolo all'inizio dell'anno, nessun ribilanciamento durante l'anno: il rendimento del portafoglio e' la media dei tre rendimenti."),
        ("LEAPS 35/65", "Solo vincitore: 35% del capitale in opzioni call con scadenza gennaio dell'anno dopo e premio pari al 35% del prezzo dell'azione; 65% nell'azione stessa. "
                        "Prezzi delle opzioni stimati con Black-Scholes (volatilita' implicita = volatilita' realizzata a 1 anno x 1,10; mezzo spread 3%): non esistono serie storiche gratuite di prezzi di opzioni 1997-2026."),
        ("Lordo", "Rendimento puro: nessun costo, nessuna imposta (come nel thread)."),
        ("Lordista", "Strategia detenuta in un certificato a gestione attiva (AMC): costo annuo AMC 0,50%, costi 0,10% per lato, bollo 0,20% annuo, ritenuta USA 15% sui dividendi; imposta 26% una sola volta, alla fine, sul guadagno complessivo. L'ETF S&P 500 e' detenuto direttamente, senza AMC."),
        ("Nettista", "Costi e bollo come sopra; ogni anno si realizza tutto: 26% sulle plusvalenze al netto dello zainetto (minusvalenze compensabili nei 4 anni successivi), dividendi USA 37,1%. "
                     "Per l'ETF S&P 500 comprato e tenuto l'imposta e' comunque solo alla fine: lordista e nettista coincidono."),
        ("S&P 500", "Indice S&P 500 Total Return per il lordo; ETF UCITS ad accumulazione (TER 0,07%, ritenuta 15% sui dividendi a livello di fondo) per lordista e nettista."),
        ("Formule", "Fogli 'Top3_per_anno', 'Portafoglio_annuo', 'Lordo', 'Lordista' e la colonna di rotazione dell'ETF nel foglio 'Nettista' sono formule: si possono cambiare i parametri nel foglio 'Parametri'. "
                    "I valori nettisti delle strategie vengono dal registro dello zainetto calcolato in Python (foglio 'Zainetto') e non si aggiornano cambiando i parametri."),
        ("Valuta", "Dollari USA. Per un residente italiano le plusvalenze si calcolano in euro ai cambi storici: l'effetto del cambio non e' incluso qui."),
    ]
    for k, v in rows:
        ws.cell(row=r, column=1, value=k).font = F_BOLD
        para(ws, r, v, col=2, merge_to=12, height=max(30, 15 * (len(v) // 120 + 1)))
        r += 1
    ws.column_dimensions["A"].width = 14

    # ------------------------------------------------------------------ Parametri
    ws = wb.create_sheet(P)
    r = title(ws, "Parametri (celle gialle modificabili)", None)
    params = [("Costo di transazione per lato", prm["cost"], "0.00%"), ("Imposta di bollo annua", prm["bollo"], "0.00%"),
              ("Aliquota plusvalenze", prm["cg"], "0%"), ("Imposta sui dividendi USA (nettista)", prm["div_net"], "0.0%"),
              ("Ritenuta USA sui dividendi (lordista)", prm["div_wrap"], "0%"), ("Costo annuo AMC (lordista, solo strategie)", prm["amc"], "0.00%"), ("Stop dal prezzo d'ingresso", prm["stop"], "0%"),
              ("Quota del capitale in LEAPS", prm["leaps_weight"], "0%"), ("Capitale iniziale (USD)", 100, "#,##0")]
    addr = {}
    for k, v, fmt in params:
        ws.cell(row=r, column=1, value=k).font = F_BOLD
        c = ws.cell(row=r, column=2, value=v)
        c.font, c.fill, c.border, c.number_format = F_INPUT, INPUT_FILL, BOX, fmt
        addr[k] = f"{P}!$B${r}"
        r += 1
    ws.cell(row=r + 1, column=1, value="Lo stop e il premio LEAPS sono gia' applicati ai dati giornalieri: cambiarli qui non ricalcola i rendimenti con stop o delle opzioni.").font = F_NOTE
    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 14
    AMC = addr["Costo annuo AMC (lordista, solo strategie)"]
    C, B, CG, DN, DW, LW, K0 = (addr["Costo di transazione per lato"], addr["Imposta di bollo annua"], addr["Aliquota plusvalenze"],
                                addr["Imposta sui dividendi USA (nettista)"], addr["Ritenuta USA sui dividendi (lordista)"],
                                addr["Quota del capitale in LEAPS"], addr["Capitale iniziale (USD)"])

    # ------------------------------------------------------------------ Top3_per_anno
    ws = wb.create_sheet("Top3_per_anno")
    r0 = title(ws, "Le prime tre azioni dell'S&P 500 per anno: rendimento nell'anno T0 e nell'anno successivo",
               "Prezzi rettificati per dividendi e frazionamenti (per le serie ricostruite: indice sintetico). 'Rend. con stop' = uscita al livello di stop o all'apertura in gap.")
    hdr = ["Anno T0", "Pos.", "Ticker", "Societa'", "Rend. anno T0", "Anno detenzione", "Prezzo ingresso (apertura 1a seduta)",
           "Prezzo uscita (chiusura ultima seduta)", "Rend. anno successivo, senza stop", "Stop toccato", "Data stop",
           "Prezzo uscita con stop", "Rend. anno successivo, con stop 35%", "Dividendi nell'anno (stima)", "Dividendi fino allo stop (stima)",
           "Serie ricostruita", "Quotata oggi", "Esito societario se non quotata"]
    for j, h in enumerate(hdr, 1):
        c = ws.cell(row=r0, column=j, value=h)
        c.font, c.border = F_BOLD, BOX
        c.alignment = Alignment(wrap_text=True, vertical="top")
    top_row = {}
    for i, rec in enumerate(t3.sort_values(["anno_T0", "posizione"]).itertuples()):
        rr = r0 + 1 + i
        top_row[(rec.anno_T0, rec.posizione)] = rr
        sinfo = st.loc[(rec.anno_T0, rec.posizione)] if (rec.anno_T0, rec.posizione) in st.index else None
        stop_px = rec.prezzo_ingresso_rett * (1 + rec.rend_T1_con_stop) if rec.stop_toccato else None
        vals = [rec.anno_T0, rec.posizione, rec.ticker.replace("PATCH_", "").split("-")[0] if rec.serie_ricostruita else rec.ticker,
                rec.societa.replace(" (serie ricostruita)", ""), rec.rend_T0, rec.anno_detenzione, rec.prezzo_ingresso_rett,
                rec.prezzo_uscita_rett, f"=H{rr}/G{rr}-1", "si" if rec.stop_toccato else "no",
                rec.data_stop if isinstance(rec.data_stop, str) else None, stop_px,
                f'=IF(J{rr}="si",L{rr}/G{rr}-1,I{rr})', rec.dividendi_T1, rec.dividendi_T1_con_stop,
                "si" if rec.serie_ricostruita else "no",
                (sinfo["quotata_oggi"] if sinfo is not None else ""),
                (sinfo["esito_societario"] if sinfo is not None and isinstance(sinfo["esito_societario"], str) else "")]
        fmts = [None, None, None, None, "0.0%", None, "#,##0.0000", "#,##0.0000", "0.0%", None, None, "#,##0.0000", "0.0%", "0.00%", "0.00%",
                None, None, None]
        for j, (v, fmt) in enumerate(zip(vals, fmts), 1):
            c = ws.cell(row=rr, column=j, value=v)
            c.border = BOX
            c.font = Font(name="Arial", size=9)
            if fmt:
                c.number_format = fmt
    for col, wdt in zip("ABCDEFGHIJKLMNOPQR", (8, 5, 9, 30, 10, 10, 13, 13, 12, 8, 11, 12, 12, 11, 11, 9, 8, 60)):
        ws.column_dimensions[col].width = wdt
    ws.freeze_panes = ws.cell(row=r0 + 1, column=5)

    # ------------------------------------------------------------------ Portafoglio_annuo
    ws = wb.create_sheet("Portafoglio_annuo")
    r0 = title(ws, "Rendimento annuo dei portafogli (lordo) e dell'S&P 500",
               "Colonne D-H e J-K sono formule sul foglio Top3_per_anno; LEAPS: rendimento dell'opzione stimato (foglio LEAPS_dettaglio).")
    hdr = ["Anno", "S&P 500 Total Return", "S&P 500 ETF (TER, ritenuta)", "Solo vincitore, senza stop", "Solo vincitore, stop 35%",
           "Prime tre, senza stop", "Prime tre, stop 35%", "Titoli fermati (su 3)", "Rend. LEAPS (stima)", "35% LEAPS + 65% azione",
           "35% LEAPS + 65% azione con stop", "Div. vincitore", "Div. vincitore con stop", "Div. prime tre", "Div. prime tre con stop",
           "Div. LEAPS 35/65", "Div. LEAPS 35/65 con stop", "Vincitore - S&P (punti)", "Prime tre - S&P (punti)"]
    for j, h in enumerate(hdr, 1):
        c = ws.cell(row=r0, column=j, value=h)
        c.font, c.border = F_BOLD, BOX
        c.alignment = Alignment(wrap_text=True, vertical="top")
    port_row = {}
    for i, rec in enumerate(ann.itertuples()):
        rr = r0 + 1 + i
        y = rec.anno
        port_row[y] = rr
        a1, a3 = top_row[(y - 1, 1)], top_row[(y - 1, 3)]
        vals = [y, rec.SP500_TR, rec.SP500_ETF, f"=Top3_per_anno!I{a1}", f"=Top3_per_anno!M{a1}",
                f"=AVERAGE(Top3_per_anno!I{a1}:I{a3})", f"=AVERAGE(Top3_per_anno!M{a1}:M{a3})",
                f'=COUNTIF(Top3_per_anno!J{a1}:J{a3},"si")', rec.leaps_rend_opzione,
                f"={LW}*I{rr}+(1-{LW})*D{rr}", f"={LW}*I{rr}+(1-{LW})*E{rr}",
                f"=Top3_per_anno!N{a1}", f"=Top3_per_anno!O{a1}", f"=AVERAGE(Top3_per_anno!N{a1}:N{a3})",
                f"=AVERAGE(Top3_per_anno!O{a1}:O{a3})", f"=(1-{LW})*L{rr}", f"=(1-{LW})*M{rr}",
                f"=E{rr}-B{rr}", f"=G{rr}-B{rr}"]
        for j, v in enumerate(vals, 1):
            c = ws.cell(row=rr, column=j, value=v)
            c.border = BOX
            c.font = Font(name="Arial", size=9)
            c.number_format = "0" if j in (1, 8) else ("0.00%" if 12 <= j <= 17 else "0.0%")
    last_r = r0 + n
    rr = last_r + 2
    ws.cell(row=rr, column=1, value="Anni in cui la strategia batte l'S&P 500 (1997-2025)").font = F_BOLD
    r25 = port_row[2025]
    for j, col in zip(range(4, 8), "DEFG"):
        ws.cell(row=rr, column=j, value=f'=SUMPRODUCT(--({col}{r0 + 1}:{col}{r25}>$B${r0 + 1}:$B${r25}))').number_format = "0"
    for j, col in zip((10, 11), "JK"):
        ws.cell(row=rr, column=j, value=f'=SUMPRODUCT(--({col}{r0 + 1}:{col}{r25}>$B${r0 + 1}:$B${r25}))').number_format = "0"
    ws.cell(row=rr + 1, column=1, value="2026 = da inizio anno al 9-10-2026.").font = F_NOTE
    for col, wdt in zip("ABCDEFGHIJKLMNOPQRS", (7, 11, 11, 11, 11, 11, 11, 9, 11, 11, 12, 9, 9, 9, 9, 9, 9, 10, 10)):
        ws.column_dimensions[col].width = wdt
    ws.freeze_panes = ws.cell(row=r0 + 1, column=2)

    # ------------------------------------------------------------------ Lordo / Lordista / Nettista paths
    strat_cols = [("Solo vincitore, senza stop", "D", "L"), ("Solo vincitore, stop 35%", "E", "M"), ("Prime tre, senza stop", "F", "N"),
                  ("Prime tre, stop 35%", "G", "O"), ("35% LEAPS + 65% azione", "J", "P"), ("35% LEAPS + 65% azione con stop", "K", "Q")]

    def path_sheet(name, heading, note, mode):
        ws = wb.create_sheet(name)
        r0 = title(ws, heading, note)
        bench_lab = "S&P 500 Total Return" if mode == "lordo" else "S&P 500 ETF, compra e tieni"
        hdr = ["Anno", bench_lab] + [s for s, _, _ in strat_cols]
        if mode == "nettista":
            hdr.insert(2, "S&P 500 ETF, vendi e ricompra ogni anno")
        for j, h in enumerate(hdr, 1):
            c = ws.cell(row=r0, column=j, value=h)
            c.font, c.border = F_BOLD, BOX
            c.alignment = Alignment(wrap_text=True, vertical="top")
        start = r0 + 1
        ws.cell(row=start, column=1, value=1996)
        for j in range(2, len(hdr) + 1):
            c = ws.cell(row=start, column=j)
            if mode in ("lordista", "nettista") and j == 2:
                c.value = f"={K0}*(1-{C})"
            elif mode == "nettista" and j >= 4:
                c.value = 100.0
            else:
                c.value = f"={K0}"
            c.number_format = "#,##0.00"
            c.border = BOX
        net_key = {s: s if not s.startswith("35%") else ("Vincitore: 35% LEAPS + 65% azione con stop" if "stop" in s else "Vincitore: 35% LEAPS + 65% azione")
                   for s, _, _ in strat_cols}
        for i, y in enumerate(years):
            rr = start + 1 + i
            pr = port_row[y]
            ws.cell(row=rr, column=1, value=y).border = BOX
            if mode == "lordo":
                ws.cell(row=rr, column=2, value=f"={_c(2)}{rr - 1}*(1+Portafoglio_annuo!B{pr})")
                for k, (s, rc, dc) in enumerate(strat_cols):
                    col = 3 + k
                    ws.cell(row=rr, column=col, value=f"={_c(col)}{rr - 1}*(1+Portafoglio_annuo!{rc}{pr})")
            elif mode == "lordista":
                ws.cell(row=rr, column=2, value=f"={_c(2)}{rr - 1}*(1+Portafoglio_annuo!C{pr})*(1-{B})")
                for k, (s, rc, dc) in enumerate(strat_cols):
                    col = 3 + k
                    ws.cell(row=rr, column=col, value=f"={_c(col)}{rr - 1}*(1-{C})*(1+Portafoglio_annuo!{rc}{pr}-{DW}*Portafoglio_annuo!{dc}{pr})*(1-{C})*(1-{AMC})*(1-{B})")
            else:
                ws.cell(row=rr, column=2, value=f"={_c(2)}{rr - 1}*(1+Portafoglio_annuo!C{pr})*(1-{B})")
                prev = f"{_c(3)}{rr - 1}"
                ws.cell(row=rr, column=3, value=f"=({prev}*(1-{C})^2*(1+Portafoglio_annuo!C{pr})-MAX({prev}*(1-{C})^2*(1+Portafoglio_annuo!C{pr})-{prev},0)*{CG})*(1-{B})")
                for k, (s, rc, dc) in enumerate(strat_cols):
                    col = 4 + k
                    pth = paths["paths"][("1997-2026 (YTD)", net_key[s], "Nettista")]
                    ws.cell(row=rr, column=col, value=float(pth[i]))
            for j in range(2, len(hdr) + 1):
                ws.cell(row=rr, column=j).number_format = "#,##0.00"
                ws.cell(row=rr, column=j).border = BOX
        end26 = start + n
        end25 = start + n - 1
        rr = end26 + 2
        labels = []
        if mode == "lordo":
            labels = [("Valore finale 2025", lambda col: f"={col}{end25}"), ("CAGR 1997-2025", lambda col: f"=({col}{end25}/{K0})^(1/29)-1"),
                      ("Valore al 9-10-2026", lambda col: f"={col}{end26}"), ("CAGR 1997-2026 (YTD)", lambda col: f"=({col}{end26}/{K0})^(1/29.77)-1")]
        elif mode == "lordista":
            def after(col, row, etf):
                v = f"{col}{row}*(1-{C})" if etf else f"{col}{row}"
                return f"={v}-{CG}*MAX({v}-{K0},0)"
            labels = [("Valore 2025 prima dell'imposta finale", lambda col: f"={col}{end25}"),
                      ("Valore 2025 dopo l'imposta 26%", lambda col, _e=end25: None),
                      ("CAGR 1997-2025 dopo imposta", None),
                      ("Valore al 9-10-2026 dopo l'imposta 26%", None), ("CAGR 1997-2026 (YTD) dopo imposta", None)]
        else:
            labels = [("Valore 2025 (imposte gia' pagate; ETF compra e tieni: dopo imposta finale)", None),
                      ("CAGR 1997-2025", None), ("Valore al 9-10-2026", None), ("CAGR 1997-2026 (YTD)", None)]
        ncol = len(hdr)
        for k, (lab, fn) in enumerate(labels):
            ws.cell(row=rr + k, column=1, value=lab).font = F_BOLD
            for j in range(2, ncol + 1):
                col = _c(j)
                etf = (j == 2 and mode != "lordo")
                if mode == "lordo":
                    f = fn(col)
                elif mode == "lordista":
                    v25 = f"{col}{end25}*(1-{C})" if etf else f"{col}{end25}"
                    v26 = f"{col}{end26}*(1-{C})" if etf else f"{col}{end26}"
                    f = [f"={col}{end25}", f"={v25}-{CG}*MAX({v25}-{K0},0)", f"=({_c(j)}{rr + 1}/{K0})^(1/29)-1",
                         f"={v26}-{CG}*MAX({v26}-{K0},0)", f"=({_c(j)}{rr + 3}/{K0})^(1/29.77)-1"][k]
                else:
                    if j == 2:      # ETF buy & hold: tax only at the end
                        v25, v26 = f"{col}{end25}*(1-{C})", f"{col}{end26}*(1-{C})"
                        f = [f"={v25}-{CG}*MAX({v25}-{K0},0)", f"=({col}{rr}/{K0})^(1/29)-1",
                             f"={v26}-{CG}*MAX({v26}-{K0},0)", f"=({col}{rr + 2}/{K0})^(1/29.77)-1"][k]
                    else:
                        f = [f"={col}{end25}", f"=({col}{rr}/{K0})^(1/29)-1", f"={col}{end26}", f"=({col}{rr + 2}/{K0})^(1/29.77)-1"][k]
                c = ws.cell(row=rr + k, column=j, value=f)
                c.number_format = "0.0%" if "CAGR" in lab else "#,##0"
                c.border = BOX
                c.font = F_BOLD
        ws.column_dimensions["A"].width = 30
        for j in range(2, ncol + 1):
            ws.column_dimensions[_c(j)].width = 15
        ws.freeze_panes = ws.cell(row=start, column=2)
        return ws

    path_sheet("Lordo", "Valore di 100 dollari - LORDO (nessun costo, nessuna imposta)", "Formule: valore anno precedente x (1 + rendimento dell'anno).", "lordo")
    path_sheet("Lordista", "Valore di 100 dollari - LORDISTA (AMC 0,50% annuo, costi, bollo, ritenuta USA sui dividendi; 26% solo alla fine)",
               "Formule. Strategie dentro un AMC (costo annuo nel foglio Parametri). ETF detenuto direttamente: TER e ritenuta gia' nel rendimento; costo d'acquisto all'inizio e di vendita alla fine.", "lordista")
    path_sheet("Nettista", "Valore di 100 dollari - NETTISTA (26% ogni anno con zainetto, dividendi 37,1%, costi, bollo)",
               "Strategie: valori dal registro dello zainetto (foglio 'Zainetto'). ETF compra e tieni: imposta solo alla fine (riga di sintesi). "
               "ETF vendi e ricompra: formula, le minusvalenze su ETF non compensano i proventi futuri di ETF.", "nettista")

    # ------------------------------------------------------------------ Zainetto
    ws = wb.create_sheet("Zainetto")
    r = title(ws, "Registro fiscale nettista: plusvalenze, zainetto (4 anni), imposte - per 100 dollari iniziali",
              "plus_minus = plusvalenza o minusvalenza dell'anno (redditi diversi); minus_usate = minusvalenze pregresse compensate; minus_scadute = perse per decorrenza dei 4 anni.")
    for s, led in paths["ledgers"].items():
        ws.cell(row=r, column=1, value=s).font = F_SUB
        r = write_table(ws, led.rename(columns={"valore_inizio": "valore_inizio_anno", "valore_fine": "valore_fine_anno"}), r + 1)
    # ------------------------------------------------------------------ Sintesi
    order_s = ["S&P 500 (indice Total Return)", "S&P 500 ETF, compra e tieni", "S&P 500 ETF, vendi e ricompra ogni anno",
               "Solo vincitore, senza stop", "Solo vincitore, stop 35%", "Prime tre, senza stop", "Prime tre, stop 35%",
               "Vincitore: 35% LEAPS + 65% azione", "Vincitore: 35% LEAPS + 65% azione con stop"]
    ws = wb.create_sheet("Sintesi", 1)
    r = title(ws, "Sintesi: valore finale di 100 dollari e rendimento annuo composto (CAGR)",
              "Valori dopo tutte le imposte dovute (per il lordista: dopo l'imposta finale). Max drawdown misurato sui valori di fine anno.")
    for per in ["1997-2025", "1997-2026 (YTD)", "1997-2008", "2009-2025", "2009-2026 (YTD)"]:
        x = res[res.periodo == per].copy()
        x["o"] = x.strategia.map({k: i for i, k in enumerate(order_s)})
        x = x.sort_values(["o", "vista"])
        tab = x[["strategia", "vista", "valore_finale", "cagr", "peggior_anno", "max_drawdown_fine_anno", "anni_negativi", "anni_sopra_SP500"]].rename(
            columns={"valore_finale": "valore finale (USD)", "cagr": "CAGR", "peggior_anno": "peggior anno", "max_drawdown_fine_anno": "max drawdown fine anno",
                     "anni_negativi": "anni negativi", "anni_sopra_SP500": "anni sopra S&P 500 (lordo)"})
        ws.cell(row=r, column=1, value=f"Periodo {per}").font = F_SUB
        r = write_table(ws, tab, r + 1, formats={"valore finale (USD)": "#,##0", "CAGR": "0.0%", "peggior anno": "0.0%",
                                                 "max drawdown fine anno": "0.0%", "anni negativi": "0", "anni sopra S&P 500 (lordo)": "0"})
    ws.column_dimensions["A"].width = 42
    # ------------------------------------------------------------------ LEAPS
    lp = ann[["anno", "leaps_K_over_S", "leaps_iv_entry", "leaps_iv_exit", "leaps_T_entry", "leaps_rate", "leaps_div_yield",
              "leaps_premium_mid_over_S", "leaps_S_change", "leaps_intrinsic_exit_over_S0", "leaps_value_exit_over_S0",
              "leaps_rend_opzione", "leaps_rend_opzione_ottimista", "leaps_rend_opzione_prudente", "leaps_K_over_S_2anni", "leaps_rend_opzione_2anni",
              "top1_senza_stop", "top1_con_stop", "leaps35_azione65", "leaps35_azione65_stop", "leaps35_azione65_ottimista",
              "leaps35_azione65_prudente", "leaps35_azione65_2anni", "leaps35_azione65_stop_2anni", "leaps_sigma_proxy"]].copy()
    lp.insert(1, "titolo", [t3[(t3.anno_T0 == y - 1) & (t3.posizione == 1)].societa.iloc[0] for y in lp.anno])
    lp = lp.rename(columns={"leaps_K_over_S": "strike / prezzo", "leaps_iv_entry": "volatilita' implicita all'acquisto",
                            "leaps_iv_exit": "volatilita' implicita alla vendita", "leaps_T_entry": "anni a scadenza all'acquisto",
                            "leaps_rate": "tasso 1 anno", "leaps_div_yield": "rendimento dividendi", "leaps_premium_mid_over_S": "premio / prezzo",
                            "leaps_S_change": "variazione prezzo azione", "leaps_intrinsic_exit_over_S0": "valore intrinseco a fine anno / prezzo iniziale",
                            "leaps_value_exit_over_S0": "valore opzione a fine anno / prezzo iniziale", "leaps_rend_opzione": "rendimento opzione (centrale)",
                            "leaps_rend_opzione_ottimista": "rendimento opzione (IV 0,9x, spread 1%)", "leaps_rend_opzione_prudente": "rendimento opzione (IV 1,3x, spread 6%)",
                            "top1_senza_stop": "rendimento azione", "top1_con_stop": "rendimento azione con stop",
                            "leaps35_azione65": "35/65 senza stop", "leaps35_azione65_stop": "35/65 con stop",
                            "leaps35_azione65_ottimista": "35/65 ottimista", "leaps35_azione65_prudente": "35/65 prudente",
                            "leaps_K_over_S_2anni": "strike / prezzo (LEAPS a 2 anni)", "leaps_rend_opzione_2anni": "rendimento opzione (LEAPS a 2 anni, venduta con 1 anno residuo)",
                            "leaps35_azione65_2anni": "35/65 con LEAPS a 2 anni", "leaps35_azione65_stop_2anni": "35/65 con LEAPS a 2 anni e stop",
                            "leaps_sigma_proxy": "volatilita' stimata (serie ricostruita)"})
    sheet_from_df(wb, "LEAPS_dettaglio", lp, "LEAPS sul vincitore: parametri e rendimento anno per anno (stime Black-Scholes)",
                  f"Serie ricostruite (Reebok 2001, Providian 2003, Avaya 2004): volatilita' = mediana dei vincitori ({prm['proxy_sigma_reconstructed']:.0%}).",
                  formats={"anni a scadenza all'acquisto": "0.00", "strike / prezzo": "0.00", "strike / prezzo (LEAPS a 2 anni)": "0.00"})
    # ------------------------------------------------------------------ rolling
    sheet_from_df(wb, "Finestre_10_anni", roll, "Finestre mobili di 10 anni (anni interi): CAGR di ogni strategia e dell'S&P 500",
                  "Lordo contro S&P 500 Total Return; nettista contro ETF S&P 500 compra e tieni dopo imposta finale.")
    wb.save(OUT / "GRMS_JanuaryBuy_Analisi_Annuale.xlsx")
    print("saved")


def _c(j):
    from openpyxl.utils import get_column_letter
    return get_column_letter(j)


if __name__ == "__main__":
    main()
