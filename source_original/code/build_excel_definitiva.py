"""
Excel deliverable: definitive version of the strategy (decision of final_decision.py).

out/GRMS_JanuaryBuy_Strategia_Definitiva.xlsx
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment
from openpyxl.worksheet.datavalidation import DataValidation

import patches
from config import OUT
from names import company
from panel import Panel
from signals import ranking, year_end_rows
from xlsx_style import (BOX, F_BOLD, F_INPUT, F_NOTE, F_SUB, INPUT_FILL, para, sheet_from_df, title, write_table)

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre",
        "novembre", "dicembre"]


def main():
    p = patches.apply(Panel.load())
    dec = json.load(open(OUT / "FD_decision.json"))
    sat, w_rec, w_max = dec["satellite_rule"], dec["weight_recommended"], dec["weight_cap"]
    kw = dec["satellite_kwargs"]
    N, STOP = int(kw["top_n"]), kw["stop"]
    grid = pd.read_csv(OUT / "FS_grid_tranche.csv").set_index("config")
    bench = pd.read_csv(OUT / "FS_benchmark_tranche.csv").set_index("view")
    cs = pd.read_csv(OUT / "FD_core_satellite.csv")
    sl = pd.read_csv(OUT / "FD_sleeves.csv").set_index("config")
    etf_sl = pd.read_csv(OUT / "FD_etf_sleeves.csv", index_col=0)
    sig = pd.read_csv(OUT / "FD_segnali_tranche.csv")
    trades = pd.read_csv(OUT / "FD_trade_log_tranche.csv")
    tax = pd.read_csv(OUT / "FD_zainetto_tranche.csv")
    wf = pd.read_csv(OUT / "FD_walkforward.csv")
    ann = pd.read_csv(OUT / "FD_annual.csv", header=[0, 1], index_col=0)
    views = {"core": "2009 - 9 ott 2026", "long": "1997 - 9 ott 2026", "core_fy": "2009 - 2025", "long_fy": "1997 - 2025"}

    def mixrow(cfg, w):
        x = cs[(cs.config == cfg) & (np.isclose(cs.weight_satellite, w))].iloc[0]
        return x

    m_rec = mixrow(sat, w_rec)
    m_max = mixrow(sat, w_max)
    sat100 = mixrow(sat, 1.0)
    thr = mixrow("top1 stop35", 1.0) if "top1 stop35" in set(cs.config) else None
    comp = []
    for v, lab in views.items():
        comp.append({"periodo": lab, "S&P 500 ETF: CAGR": bench.loc[v, "cagr"], "S&P 500 ETF: max drawdown": bench.loc[v, "maxdd"],
                     f"{int((1 - w_rec) * 100)}/{int(w_rec * 100)} raccomandato: CAGR": m_rec[f"{v}_cagr"],
                     f"{int((1 - w_rec) * 100)}/{int(w_rec * 100)} raccomandato: max drawdown": m_rec[f"{v}_maxdd"],
                     f"{int((1 - w_max) * 100)}/{int(w_max * 100)} tetto: CAGR": m_max[f"{v}_cagr"],
                     f"{int((1 - w_max) * 100)}/{int(w_max * 100)} tetto: max drawdown": m_max[f"{v}_maxdd"],
                     "satellite 100%: CAGR": sat100[f"{v}_cagr"], "satellite 100%: max drawdown": sat100[f"{v}_maxdd"],
                     "regola del thread (top-1 stop 35%, 12 tranche): CAGR": grid.loc["top1 stop35", f"{v}_cagr"],
                     "regola del thread, solo gennaio: CAGR": grid.loc["top1 stop35", f"{v}_jan_cagr"]})
    comp = pd.DataFrame(comp)

    wb = Workbook()
    # ------------------------------------------------------------------ Decisione
    ws = wb.active
    ws.title = "Decisione"
    r = title(ws, "GRMS Partners - January Buy: versione definitiva",
              f"Dati fino al {dec['last_date']}. Netto fisco italiano (persona fisica, regime amministrato), in EUR, dopo l'imposta sulla liquidazione finale.")
    lines = [
        ("Decisione", f"Core: {int((1 - w_rec) * 100)}% ETF UCITS S&P 500 ad accumulazione. Satellite: {int(w_rec * 100)}% regola 'January Buy' in versione top-{N}, "
                      f"stop {int(STOP * 100)}% dal prezzo di carico, mantenimento dei titoli riconfermati, ripartita in 12 tranche mensili. "
                      f"Tetto massimo del satellite secondo il criterio dichiarato: {int(w_max * 100)}%."),
        ("Perche' non la regola del thread pura", "La regola del thread (top-1, partenza a gennaio) e' la piu' fortunata delle 12 partenze possibili: con partenza ad aprile la stessa regola "
                                                 "perde denaro dal 2009 a oggi. Il risultato di gennaio non e' quindi una stima affidabile di cio' che un investitore otterrebbe."),
        ("Criterio", "Tra 48 regole x quote di satellite dal 5% al 100%, e' stata scelta la coppia con il miglior extra-rendimento sull'ETF nel peggiore dei 4 periodi, "
                     "a condizione che il drawdown massimo del portafoglio non superi quello dell'ETF di oltre 5 punti in nessun periodo. "
                     "La quota raccomandata e' meta' del tetto, per l'incertezza statistica del vantaggio storico."),
        ("Statistica", f"Probabilita' che lo Sharpe vero del satellite superi quello dell'ETF (PSR, 1997-2026): {dec['psr_vs_etf']:.0%}. "
                       f"Selezione walk-forward 2007-2026 (scelta ogni gennaio con i soli dati noti): CAGR {dec['wf_cagr']:.1%} contro {dec['wf_etf_cagr']:.1%} dell'ETF."),
        ("Rischio principale", f"Concentrazione: con top-{N} per tranche lo stesso titolo puo' comparire in molte tranche contemporaneamente (al {dec['last_date']} "
                              f"{company(sig.groupby('ticker').tranche.nunique().idxmax())} e' in {sig.groupby('ticker').tranche.nunique().max()} tranche su 12). "
                              "Il satellite e' quindi esposto a ribassi improvvisi di singoli titoli; lo stop non protegge dai gap di apertura."),
    ]
    for k, v in lines:
        ws.cell(row=r, column=1, value=k).font = F_BOLD
        para(ws, r, v, col=2, merge_to=12, height=max(30, 15 * (len(v) // 120 + 1)))
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="Confronto nei 4 periodi (CAGR netti dopo imposta finale; drawdown sul valore del dossier)").font = F_SUB
    r += 1
    write_table(ws, comp, r)
    ws.column_dimensions["A"].width = 26

    # ------------------------------------------------------------------ Regole
    ws = wb.create_sheet("Regole_operative")
    r = title(ws, "Regole operative del satellite (da applicare ogni mese)",
              "Il satellite e' diviso in 12 tranche uguali; la tranche k si ribilancia una volta l'anno, nel mese k.")
    rules = [
        ("Universo", "Titoli membri dell'S&P 500 alla data della classifica (lista ufficiale S&P DJI)."),
        ("Classifica", "All'ultima seduta del mese precedente il ribilanciamento: rendimento totale a 12 mesi (dividendi inclusi) da fine mese a fine mese. "
                       "I titoli quotati da meno di 12 mesi entrano con il rendimento dalla quotazione se hanno almeno 126 sedute di storia."),
        ("Selezione", f"I primi {N} titoli della classifica (se un titolo non e' acquistabile - es. delisting per acquisizione - si prende il successivo)."),
        ("Vendita", "Alla chiusura dell'ultima seduta del mese precedente: si vendono i titoli della tranche che NON sono tra i nuovi selezionati. "
                    "I titoli riconfermati restano in portafoglio (nessuna imposta realizzata) e il loro stop viene ricalcolato dal prezzo di quel giorno."),
        ("Acquisto", f"All'apertura della prima seduta del mese: i nuovi titoli, in parti uguali (1/{N} della tranche ciascuno)."),
        ("Stop", f"Ordine stop a -{int(STOP * 100)}% dal prezzo di carico, valido fino al prossimo ribilanciamento della tranche. "
                 "Se scatta, la quota resta in liquidita' (T-bill / monetario) fino al ribilanciamento successivo della stessa tranche."),
        ("Liquidita' iniziale", "Le tranche non ancora avviate restano in liquidita' remunerata: il satellite e' pienamente investito dopo 12 mesi (come nel backtest)."),
        ("Core", "ETF UCITS ad accumulazione sull'S&P 500, comprato e tenuto."),
        ("Ribilanciamento", "Una volta l'anno (fine dicembre) si riporta il satellite al peso obiettivo se si e' scostato di oltre 5 punti. "
                            "Se il satellite e' sovrappesato, l'eccesso si preleva dai proventi delle tranche che si ribilanciano (nessuna imposta aggiuntiva: "
                            "le plusvalenze sono gia' realizzate) e si investe nell'ETF. Se e' sottopesato, si vende ETF (imposta 26% sulla plusvalenza dell'ETF venduto). "
                            "Senza ribilanciamento il peso del satellite tende a crescere molto (foglio 'Ribilanciamento')."),
        ("Fisco", "Regime amministrato: imposta 26% su ogni plusvalenza realizzata; minusvalenze nello zainetto per 4 anni; dividendi USA tassati 15% alla fonte (W-8BEN) + 26% sul netto; "
                  "bollo 0,20%. Attenzione: per azioni uguali acquistate in tranche diverse l'intermediario usa il costo medio ponderato."),
        ("Governo (proposta)", "Regole di governo proposte dallo Studio e NON incluse nel backtest: revisione straordinaria del satellite se il suo drawdown supera il -60% "
                               "o se i dati di classifica non sono verificabili; valutazione caso per caso quando lo stesso titolo e' presente in oltre 8 tranche su 12."),
    ]
    for k, v in rules:
        ws.cell(row=r, column=1, value=k).font = F_BOLD
        para(ws, r, v, col=2, merge_to=12, height=max(30, 15 * (len(v) // 120 + 1)))
        r += 1
    ws.column_dimensions["A"].width = 18

    # ------------------------------------------------------------------ Calcolatore (formule)
    ws = wb.create_sheet("Calcolatore")
    r = title(ws, "Calcolatore operativo", "Celle gialle = input (testo blu). Le altre celle sono formule.")
    ws.cell(row=r, column=1, value="Allocazione").font = F_SUB
    r += 1
    inp = {}
    for k, v, fmt, note in [("Patrimonio azionario da allocare (EUR)", 1000000, "#,##0", "Inserire l'importo del cliente."),
                            ("Quota satellite", w_rec, "0%", f"Raccomandata {w_rec:.0%}; tetto del criterio {w_max:.0%}."),
                            ("Numero di tranche", 12, "0", "12 = una tranche per mese."),
                            ("Titoli per tranche", N, "0", "Regola scelta: top-2."),
                            ("Stop dal prezzo di carico", STOP, "0%", "Regola scelta: 35%.")]:
        ws.cell(row=r, column=1, value=k).font = F_BOLD
        c = ws.cell(row=r, column=2, value=v)
        c.font, c.fill, c.border, c.number_format = F_INPUT, INPUT_FILL, BOX, fmt
        c.comment = Comment(note, "GRMS")
        inp[k] = f"$B${r}"
        r += 1
    P, Wq, T, Nn, St = (inp[k] for k in ["Patrimonio azionario da allocare (EUR)", "Quota satellite", "Numero di tranche",
                                         "Titoli per tranche", "Stop dal prezzo di carico"])
    out_rows = [("Core ETF S&P 500 (EUR)", f"={P}*(1-{Wq})", "#,##0"), ("Satellite (EUR)", f"={P}*{Wq}", "#,##0"),
                ("Importo per tranche (EUR)", f"={P}*{Wq}/{T}", "#,##0"),
                ("Importo per titolo in una tranche (EUR)", f"={P}*{Wq}/{T}/{Nn}", "#,##0"),
                ("Peso di un titolo di una tranche sul patrimonio", f"={Wq}/{T}/{Nn}", "0.00%"),
                ("Peso massimo di un titolo presente in tutte le tranche", f"={Wq}", "0.0%")]
    out_addr = {}
    for k, f_, fmt in out_rows:
        ws.cell(row=r, column=1, value=k).font = F_BOLD
        c = ws.cell(row=r, column=2, value=f_)
        c.number_format, c.border = fmt, BOX
        out_addr[k] = f"$B${r}"
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="Ordine e stop per un acquisto").font = F_SUB
    r += 1
    o = {}
    for k, v, fmt in [("Prezzo di acquisto (USD)", 100.0, "#,##0.00"), ("Cambio EUR/USD (USD per 1 EUR)", 1.17, "0.0000")]:
        ws.cell(row=r, column=1, value=k).font = F_BOLD
        c = ws.cell(row=r, column=2, value=v)
        c.font, c.fill, c.border, c.number_format = F_INPUT, INPUT_FILL, BOX, fmt
        o[k] = f"$B${r}"
        r += 1
    ws[o["Cambio EUR/USD (USD per 1 EUR)"].replace("$", "")].comment = Comment("Valore di esempio: usare il cambio del giorno.", "GRMS")
    for k, f_, fmt in [("Numero di azioni da comprare", f"=ROUNDDOWN({out_addr['Importo per titolo in una tranche (EUR)']}*{o['Cambio EUR/USD (USD per 1 EUR)']}/{o['Prezzo di acquisto (USD)']},0)", "#,##0"),
                       ("Livello di stop (USD)", f"={o['Prezzo di acquisto (USD)']}*(1-{St})", "#,##0.00")]:
        ws.cell(row=r, column=1, value=k).font = F_BOLD
        c = ws.cell(row=r, column=2, value=f_)
        c.number_format, c.border = fmt, BOX
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="Stima dell'imposta su una vendita (regime amministrato)").font = F_SUB
    r += 1
    t = {}
    for k, v, fmt in [("Azioni vendute", 100, "#,##0"), ("Costo medio di carico (USD)", 100.0, "#,##0.00"),
                      ("Cambio EUR/USD all'acquisto", 1.10, "0.0000"), ("Prezzo di vendita (USD)", 150.0, "#,##0.00"),
                      ("Cambio EUR/USD alla vendita", 1.17, "0.0000"), ("Minusvalenze disponibili nello zainetto (EUR)", 0, "#,##0"),
                      ("Aliquota", 0.26, "0%")]:
        ws.cell(row=r, column=1, value=k).font = F_BOLD
        c = ws.cell(row=r, column=2, value=v)
        c.font, c.fill, c.border, c.number_format = F_INPUT, INPUT_FILL, BOX, fmt
        t[k] = f"$B${r}"
        r += 1
    ws[t["Cambio EUR/USD all'acquisto"].replace("$", "")].comment = Comment("Valori di esempio.", "GRMS")
    q_, c_, fa, s_, fv, z, al = (t[k] for k in t)
    for k, f_, fmt in [("Costo fiscale (EUR)", f"={q_}*{c_}/{fa}", "#,##0.00"), ("Corrispettivo (EUR)", f"={q_}*{s_}/{fv}", "#,##0.00"),
                       ("Plus/minusvalenza (EUR)", f"=B{r + 1}-B{r}", "#,##0.00;(#,##0.00)"),
                       ("Minusvalenze utilizzate (EUR)", f"=IF(B{r + 2}>0,MIN(B{r + 2},{z}),0)", "#,##0.00"),
                       ("Imponibile (EUR)", f"=MAX(B{r + 2}-B{r + 3},0)", "#,##0.00"),
                       ("Imposta sostitutiva (EUR)", f"=B{r + 4}*{al}", "#,##0.00"),
                       ("Nuova minusvalenza nello zainetto (EUR)", f"=IF(B{r + 2}<0,-B{r + 2},0)", "#,##0.00")]:
        ws.cell(row=r, column=1, value=k).font = F_BOLD
        c = ws.cell(row=r, column=2, value=f_)
        c.number_format, c.border = fmt, BOX
        r += 1
    r += 1
    para(ws, r, "Calcolo indicativo: la plusvalenza in euro si determina convertendo costo e corrispettivo ai cambi delle rispettive date; "
                "l'intermediario applica il costo medio ponderato per titoli uguali acquistati in momenti diversi.", font=F_NOTE, merge_to=6, height=30)
    ws.column_dimensions["A"].width = 52
    ws.column_dimensions["B"].width = 18

    # ------------------------------------------------------------------ Segnali
    ye = year_end_rows(p)
    last = len(p.dates) - 1
    me = p.month_end_rows()
    oct25 = [x for x in me if p.dates[x].year == 2025 and p.dates[x].month == 10][0]
    rk_nov = ranking(p, "SPX", last, oct25, min_days=126).head(10)
    rk_nov.insert(0, "posizione", range(1, len(rk_nov) + 1))
    rk_nov["societa"] = rk_nov.label.map(company)
    rk_nov = rk_nov[["posizione", "label", "societa", "mom"]].rename(columns={"label": "ticker", "mom": "rendimento_dal_31ott2025"})
    rk_jan = pd.read_csv(OUT / "FD_classifica_2026YTD.csv").head(10)
    rk_jan.insert(0, "posizione", range(1, len(rk_jan) + 1))
    rk_jan = rk_jan[["posizione", "label", "societa", "mom"]].rename(columns={"label": "ticker", "mom": "rendimento_2026_ytd"})
    ws = wb.create_sheet("Segnali_oggi")
    r = title(ws, f"Segnali al {dec['last_date']}", "Le classifiche definitive si fissano all'ultima seduta del mese; queste sono provvisorie.")
    ws.cell(row=r, column=1, value="Classifica provvisoria per la tranche di NOVEMBRE 2026 (finestra 31-10-2025 -> 30-10-2026, dati al 9-10-2026)").font = F_SUB
    r = write_table(ws, rk_nov, r + 1)
    ws.cell(row=r, column=1, value="Classifica provvisoria per la tranche di GENNAIO 2027 = anno solare 2026 (regola del thread)").font = F_SUB
    r = write_table(ws, rk_jan, r + 1)
    reg = dec["regime"]
    para(ws, r, f"Indicatore di regime (solo informativo, la regola scelta non lo usa): S&P 500 TR {'sopra' if reg['risk_on'] else 'sotto'} la media a 10 mesi al {reg['date']}.",
         font=F_NOTE, merge_to=8)
    r += 2
    ws.cell(row=r, column=1, value="Posizioni che il satellite avrebbe oggi se fosse stato avviato nel 2009 (simulazione)").font = F_SUB
    sig2 = sig.copy()
    sig2["mese_ribilanciamento"] = sig2.tranche.map(lambda m: MESI[m - 1])
    sig2 = sig2[["tranche", "mese_ribilanciamento", "periodo_dal", "ticker", "societa", "momentum_alla_selezione",
                 "rendimento_da_ingresso", "stato"]]
    r = write_table(ws, sig2, r + 1)
    conc = sig.groupby("ticker").tranche.nunique().sort_values(ascending=False).rename("tranche_con_il_titolo").reset_index()
    ws.cell(row=r, column=1, value="Concentrazione: numero di tranche (su 12) che contengono lo stesso titolo").font = F_SUB
    write_table(ws, conc, r + 1)

    # ------------------------------------------------------------------ Calendario di avvio
    ws = wb.create_sheet("Piano_di_avvio")
    r = title(ws, "Piano di avvio del satellite (12 tranche)", "Una tranche al mese; le tranche non avviate restano in liquidita' remunerata.")
    ws.cell(row=r, column=1, value="Quota satellite").font = F_BOLD
    ws.cell(row=r, column=2, value="=Calcolatore!" + Wq).number_format = "0%"
    ws.cell(row=r + 1, column=1, value="Importo per tranche (EUR)").font = F_BOLD
    ws.cell(row=r + 1, column=2, value="=Calcolatore!" + out_addr["Importo per tranche (EUR)"]).number_format = "#,##0"
    r += 3
    hdr = ["Tranche", "Mese di avvio", "Classifica alla chiusura di", "Acquisto all'apertura di", "Importo (EUR)", "Titoli", "Satellite investito dopo l'avvio"]
    for j, h in enumerate(hdr, 1):
        c = ws.cell(row=r, column=j, value=h)
        c.font, c.border = F_BOLD, BOX
    start = pd.Timestamp("2026-11-01")
    for k in range(12):
        m = start + pd.DateOffset(months=k)
        rr = r + 1 + k
        vals = [k + 1, f"{MESI[m.month - 1]} {m.year}", f"ultima seduta NYSE di {MESI[(m - pd.DateOffset(months=1)).month - 1]}",
                f"prima seduta NYSE di {MESI[m.month - 1]} {m.year}", f"=$B${r - 2}", "=Calcolatore!" + Nn, f"=A{rr}/Calcolatore!" + T]
        for j, v in enumerate(vals, 1):
            c = ws.cell(row=rr, column=j, value=v)
            c.border = BOX
        ws.cell(row=rr, column=5).number_format = "#,##0"
        ws.cell(row=rr, column=7).number_format = "0%"
    ws.cell(row=r + 14, column=1, value="Verificare il calendario delle festivita' NYSE dell'anno prima di ogni ordine.").font = F_NOTE
    for col, wdt in zip("ABCDEFG", (9, 16, 30, 32, 14, 8, 22)):
        ws.column_dimensions[col].width = wdt

    # ------------------------------------------------------------------ Registro esecuzioni (template)
    ws = wb.create_sheet("Registro_esecuzioni")
    r = title(ws, "Registro delle esecuzioni (da compilare)",
              "Compilare le celle gialle a ogni ribilanciamento. La riga 5 e' un esempio da cancellare. Le colonne grigie sono formule.")
    hdr = ["Data", "Tranche", "Operazione (A/V)", "Ticker", "Quantita'", "Prezzo (USD)", "Cambio EUR/USD", "Controvalore (EUR)",
           "Livello di stop (USD)", "Note"]
    for j, h in enumerate(hdr, 1):
        c = ws.cell(row=r, column=j, value=h)
        c.font, c.border = F_BOLD, BOX
    dv = DataValidation(type="list", formula1='"A,V"', allow_blank=True)
    ws.add_data_validation(dv)
    for i in range(1, 61):
        rr = r + i
        for j in range(1, 11):
            c = ws.cell(row=rr, column=j)
            c.border = BOX
            if j in (1, 2, 3, 4, 5, 6, 7, 10):
                c.fill, c.font = INPUT_FILL, F_INPUT
        ws.cell(row=rr, column=8, value=f'=IF(OR(E{rr}="",F{rr}="",G{rr}=""),"",E{rr}*F{rr}/G{rr})').number_format = "#,##0.00"
        ws.cell(row=rr, column=9, value=f'=IF(OR(C{rr}<>"A",F{rr}=""),"",F{rr}*(1-Calcolatore!' + St + '))').number_format = "#,##0.00"
        ws.cell(row=rr, column=1).number_format = "dd/mm/yyyy"
        dv.add(ws.cell(row=rr, column=3))
    ex = [pd.Timestamp("2026-11-02").date(), 1, "A", "ESEMPIO", 50, 200.0, 1.17, None, None, "riga di esempio: cancellare"]
    for j, v in enumerate(ex, 1):
        if v is not None:
            ws.cell(row=r + 1, column=j, value=v)
    for col, wdt in zip("ABCDEFGHIJ", (12, 8, 14, 10, 10, 12, 13, 16, 16, 28)):
        ws.column_dimensions[col].width = wdt
    ws.freeze_panes = ws.cell(row=r + 1, column=1)

    # ------------------------------------------------------------------ data sheets
    st = sl.loc[[sat, "top1 stop35"]].copy()
    rows = []
    for cfg in (sat, "top1 stop35"):
        for v, lab in views.items():
            rec = {"regola": cfg, "periodo": lab}
            for m in range(1, 13):
                rec[MESI[m - 1]] = st.loc[cfg, f"{v}_m{m:02d}"]
            rec["mediana"] = st.loc[cfg, f"{v}_median"]
            rec["quota_mesi_sopra_ETF"] = st.loc[cfg, f"{v}_share_beating_etf"]
            rows.append(rec)
    for v, lab in views.items():
        rec = {"regola": "S&P 500 ETF", "periodo": lab}
        for m in range(1, 13):
            rec[MESI[m - 1]] = etf_sl.loc[f"m{m:02d}", v]
        rec["mediana"] = float(np.median(etf_sl[v]))
        rows.append(rec)
    sheet_from_df(wb, "Mesi_di_partenza", pd.DataFrame(rows), "CAGR netto per mese di partenza (una sola tranche)",
                  "La versione a 12 tranche e' la media delle 12 righe in termini di ricchezza finale.")
    cs_sat = cs[cs.config == sat].drop(columns=["config"])
    sheet_from_df(wb, "Quota_satellite", cs_sat, f"ETF S&P 500 + satellite {sat}: quota dallo 0% al 100%",
                  "dd_gap = drawdown del portafoglio meno drawdown dell'ETF (negativo = peggio). within_risk_budget = scostamento non oltre 5 punti in tutti i periodi.")
    rb = pd.read_csv(OUT / "FD_rebalanced_mix.csv")
    sheet_from_df(wb, "Ribilanciamento", rb, "ETF + satellite con ribilanciamento annuale al peso obiettivo (banda 0 o 5 punti)",
                  "sat_weight_end = peso del satellite alla fine del periodo (dopo l'ultimo ribilanciamento di dicembre 2025 e il 2026 in corso). "
                  "Approssimazione fiscale: trasferimenti satellite->ETF senza imposta aggiuntiva; ETF->satellite tassati al 26% sulla plusvalenza dell'ETF.")
    sheet_from_df(wb, "Frontiera_regole", pd.read_csv(OUT / "FD_frontier.csv"),
                  "Miglior quota ammessa per ciascuna regola (criterio dichiarato)", None)
    a2 = ann.copy()
    a2.columns = [f"{x} | {y}" for x, y in a2.columns]
    a2 = a2.reset_index().rename(columns={"index": "anno"})
    sheet_from_df(wb, "Rendimenti_annui", a2, "Rendimenti annui netti (EUR)", "2026 = da inizio anno al " + dec["last_date"])
    sheet_from_df(wb, "Walk_forward", wf, "Walk-forward 2007-2026: regola scelta ogni gennaio con i soli dati disponibili", None)
    tr2 = trades.copy()
    tr2.insert(1, "societa", tr2.label.map(company))
    tr2 = tr2.rename(columns={"label": "ticker", "kind": "strumento", "entry": "data_acquisto", "exit": "data_vendita", "reason": "motivo",
                              "ret": "rendimento", "gain_taxccy": "plus_minus_eur", "tax_taxccy": "imposta_eur"})
    sheet_from_df(wb, "Trade_log_backtest", tr2, f"Operazioni simulate del satellite {sat}, 12 tranche, 2009-2026 (per EUR 100 per tranche)",
                  "motivo: rebalance = ribilanciamento annuale della tranche; stop = stop 35%; delisted = titolo uscito (es. acquisizione).")
    tax2 = tax.copy()
    agg = tax2.groupby("year").agg(plusvalenze=("gain", lambda x: x[x > 0].sum()), minusvalenze=("gain", lambda x: -x[x < 0].sum()),
                                   compensate=("offset", "sum"), imponibile=("taxable", "sum"), imposta=("tax", "sum"),
                                   scadute=("expired", "sum")).reset_index().rename(columns={"year": "anno"})
    sheet_from_df(wb, "Zainetto_fiscale", agg, "Zainetto fiscale del satellite (somma delle 12 tranche, EUR per 100 EUR per tranche)",
                  "Ogni tranche e' trattata come un dossier separato (ipotesi prudente: in un unico dossier le minusvalenze di una tranche compensano le plusvalenze delle altre).")
    wb.save(OUT / "GRMS_JanuaryBuy_Strategia_Definitiva.xlsx")
    print("saved")


if __name__ == "__main__":
    main()
