"""
Excel deliverable: LEAPS version of the January Buy rule.

out/GRMS_JanuaryBuy_LEAPS.xlsx
  LEGGIMI            what the variant is, how it is priced, limits
  Regole_operative   step-by-step rule
  Sintesi            LEAPS vs the same rule in shares vs S&P 500 ETF (Jan start and 12 tranches, 2 samples)
  Trade_log          every LEAPS bought: S, K, K/S, IV, T, premium, exit, option return, gain and tax (EUR)
  Rendimenti_annui   year by year
  Scenari            premium/allocation/IV/spread grid (phase D)
  Calcolatore_BS     live Black-Scholes calculator and payoff table at expiry (Excel formulas)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.comments import Comment

import patches
from benchmarks import run_benchmark
from config import OUT
from engine import run
from experiments import NET_IT
from metrics import annual_returns, max_drawdown
from names import company
from panel import Panel
from xlsx_style import (F_BOLD, F_INPUT, F_NOTE, F_SUB, INPUT_FILL, BOX, para, sheet_from_df, title, write_table)

BASE = dict(universe="SPX", currency="EUR", instrument="leaps", stop=None, leaps_alloc=0.35, leaps_prem=0.35,
            leaps_iv_mult=1.10, leaps_half_spread=0.03, **NET_IT)
SAMPLES = {"core 2009-2026YTD": 2009, "long 1997-2026YTD": 1997}


def cagr_after(res):
    eq = res["equity"]
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return (res["final_after_liq"] / 100.0) ** (1 / yrs) - 1


def main():
    p = patches.apply(Panel.load())
    dec = json.load(open(OUT / "FD_decision.json"))
    rows, trades, annual = [], [], {}
    for sname, fy in SAMPLES.items():
        b = run_benchmark(p, "SPX", first_year=fy, regime="bh", currency="EUR")
        annual[(sname, "S&P 500 ETF")] = annual_returns(b["equity"])
        bc = (b["final_after_liq"] / 100) ** (1 / ((b["equity"].index[-1] - b["equity"].index[0]).days / 365.25)) - 1
        rows.append(dict(campione=sname, strategia="S&P 500 ETF buy & hold", partenza="gennaio", cagr_netto=bc,
                         valore_finale_netto=b["final_after_liq"], max_drawdown=max_drawdown(b["equity"])[0],
                         peggior_anno=annual_returns(b["equity"]).min()))
        for top in (1, 3):
            for inst, extra in (("LEAPS 35/65", {}), ("azioni, senza stop", dict(instrument="stock", stop=None)),
                                ("azioni, stop 35%", dict(instrument="stock", stop=0.35))):
                kw = dict(BASE)
                kw.update(extra)
                finals, cg = [], []
                for m in range(1, 13):
                    r = run(p, first_year=fy, first_month=m, top_n=top, **kw)
                    finals.append(r["final_after_liq"])
                    cg.append(cagr_after(r))
                    if m == 1:
                        rj = r
                yrs = (rj["equity"].index[-1] - rj["equity"].index[0]).days / 365.25
                ar = annual_returns(rj["equity"])
                annual[(sname, f"top{top} {inst}")] = ar
                rows.append(dict(campione=sname, strategia=f"top-{top} {inst}", partenza="gennaio", cagr_netto=cg[0],
                                 valore_finale_netto=finals[0], max_drawdown=max_drawdown(rj["equity"])[0],
                                 peggior_anno=ar.min(), cagr_12_tranche=(np.mean(finals) / 100) ** (1 / yrs) - 1,
                                 cagr_mese_peggiore=min(cg), cagr_mese_mediano=float(np.median(cg))))
                if inst.startswith("LEAPS"):
                    ev = rj["events"]
                    ev = ev[ev.event == "leaps_buy"].copy()
                    tr = rj["trades"]
                    tr = tr[tr.kind == "leaps"].copy()
                    ev["date"] = pd.to_datetime(ev["date"])
                    tr["entry"] = pd.to_datetime(tr["entry"])
                    mrg = ev.merge(tr, left_on=["label", "date"], right_on=["label", "entry"], how="left")
                    for x in mrg.itertuples():
                        trades.append(dict(campione=sname, regola=f"top-{top}", anno=x.date.year, ticker=x.label.replace("Y_", ""),
                                           societa=company(x.label), data_acquisto=x.date.date(),
                                           k_over_s=x.K_over_S, iv=x.sigma,
                                           anni_a_scadenza=x.T, premio_mid_su_S=x.mid_over_S,
                                           premio_pagato_su_S=x.mid_over_S * (1 + BASE["leaps_half_spread"]),
                                           data_uscita=(x.exit if isinstance(x.exit, str) or pd.notna(x.exit) else None),
                                           motivo_uscita=(x.reason if isinstance(x.reason, str) else "posizione aperta al " + str(p.dates[-1].date())),
                                           rendimento_opzione=x.ret,
                                           plus_minus_eur=x.gain_taxccy, imposta_eur=x.tax_taxccy))
    summ = pd.DataFrame(rows)
    tl = pd.DataFrame(trades)
    ann = pd.DataFrame(annual)
    ann.columns = [f"{a} | {b}" for a, b in ann.columns]
    ann = ann.reset_index().rename(columns={"index": "anno"})
    ann["anno"] = ann["anno"].astype(int)
    scen = pd.read_csv(OUT / "D_leaps.csv")
    scen = scen[["first_year", "top_n", "alloc", "iv_mult", "half_spread", "avg_K_over_S", "final_after_liq", "cagr_after_liq",
                 "max_dd", "worst_year", "sharpe"]].rename(columns={
        "first_year": "anno_inizio", "top_n": "numero_titoli", "alloc": "quota_capitale_in_premi", "iv_mult": "moltiplicatore_iv",
        "half_spread": "mezzo_spread", "avg_K_over_S": "k_over_s_medio", "final_after_liq": "valore_finale_netto",
        "cagr_after_liq": "cagr_netto", "max_dd": "max_drawdown", "worst_year": "peggior_anno"})

    wb = Workbook()
    ws = wb.active
    ws.title = "LEGGIMI"
    r = title(ws, "GRMS Partners - January Buy, versione LEAPS",
              f"Dati fino al {dec['last_date']}. Importi in EUR per un investitore persona fisica residente in Italia, regime amministrato.")
    text = [
        ("Che cosa e'", "Ogni anno, invece di comprare le azioni dei vincitori dell'anno precedente, si comprano opzioni call a lunga scadenza (LEAPS, scadenza gennaio dell'anno successivo, circa 12,5 mesi) con strike scelto in modo che il premio sia il 35% del prezzo dell'azione. Si spende in premi il 35% del capitale; il restante 65% resta in T-bill. La perdita massima dell'anno e' quindi circa il 35% del capitale (piu' spread e cambio EUR/USD)."),
        ("Come sono prezzate", "Non esistono serie storiche gratuite di prezzi di opzioni 1997-2026 (OptionMetrics/ORATS sono a pagamento). Le LEAPS sono quindi prezzate con Black-Scholes-Merton: volatilita' implicita = volatilita' realizzata a 252 giorni x 1,10 (minimo 20%), dividendi = rendimento da dividendi degli ultimi 12 mesi, tasso = rendimento T-bill/Treasury a 1 anno (FRED). Si paga un mezzo spread del 3% del premio in acquisto e in vendita."),
        ("Uscita", "Vendita all'ultima seduta dell'anno (circa 3 settimane di valore temporale residuo), cosi' l'anno fiscale coincide con quello della versione in azioni."),
        ("Fisco", "Plusvalenze e minusvalenze su opzioni = redditi diversi (art. 67 TUIR), imposta sostitutiva 26%; le minusvalenze vanno nello zainetto (4 anni, art. 68 c.5 TUIR). Interessi sui T-bill: 12,5%. Bollo 0,20% annuo sul valore del dossier."),
        ("Risultato in breve", "Con premio al 35% e 35% del capitale in premi la versione LEAPS rende meno della stessa regola in azioni in tutti gli scenari di prezzo realistici (foglio 'Sintesi' e 'Scenari'): la leva e' bassa (strike profondamente in the money, K/S medio ~0,8) e il costo implicito (volatilita' e spread) pesa ogni anno. Con il 100% del capitale in premi la versione porta all'azzeramento del capitale in quasi tutti gli scenari."),
        ("Limiti", "Prezzi modellati, non di mercato. Non e' verificato che per ogni titolo e ogni anno esistessero LEAPS quotate con scadenza gennaio successivo, ne' la loro liquidita' (soprattutto 1997-2005 e per i titoli piu' piccoli). L'IV reale dei titoli appena saliti molto e' spesso superiore alla volatilita' realizzata: lo scenario 1,3x e' il piu' prudente."),
        ("Fogli", "Regole_operative, Sintesi, Trade_log, Rendimenti_annui, Scenari, Calcolatore_BS (formule Excel vive: modificare le celle gialle)."),
    ]
    for k, v in text:
        ws.cell(row=r, column=1, value=k).font = F_BOLD
        para(ws, r, v, col=2, merge_to=10, height=max(30, 15 * (len(v) // 110 + 1)))
        r += 1
    ws.column_dimensions["A"].width = 20
    for col in "BCDEFGHIJ":
        ws.column_dimensions[col].width = 14

    ws = wb.create_sheet("Regole_operative")
    r = title(ws, "Regole operative della versione LEAPS", "Da eseguire ogni anno; la versione a 12 tranche ripete lo stesso schema ogni mese su 1/12 del capitale.")
    steps = [
        "Ultima seduta dell'anno (chiusura): classificare i membri dell'S&P 500 per rendimento totale dell'anno solare; scegliere i primi N (N = 1 o 3).",
        "Stessa seduta: vendere le LEAPS dell'anno precedente (circa 3 settimane alla scadenza) e incassare il controvalore.",
        "Prima seduta del nuovo anno: per ciascun titolo scelto, individuare la call con scadenza gennaio dell'anno successivo e strike tale che il premio sia circa il 35% del prezzo dell'azione (nella catena reale: lo strike quotato piu' vicino).",
        "Investire in premi il 35% del capitale complessivo, diviso in parti uguali tra i titoli; il 65% resta in T-bill o liquidita' remunerata.",
        "Nessuno stop: la perdita massima e' il premio pagato.",
        "Controllare liquidita' e spread della catena opzioni prima dell'ordine; usare ordini limite al prezzo medio.",
        "Fisco: la plusvalenza o minusvalenza sull'opzione e' reddito diverso; la minusvalenza alimenta lo zainetto (4 anni).",
    ]
    for i, s_ in enumerate(steps, 1):
        ws.cell(row=r, column=1, value=i).font = F_BOLD
        para(ws, r, s_, col=2, merge_to=10, height=30)
        r += 1
    ws.column_dimensions["A"].width = 5
    for col in "BCDEFGHIJ":
        ws.column_dimensions[col].width = 14

    sheet_from_df(wb, "Sintesi", summ, "LEAPS vs azioni vs S&P 500 ETF (netto fisco IT, EUR, dopo imposta finale)",
                  "cagr_12_tranche: stessa regola ripartita su 12 partenze mensili; cagr_mese_peggiore / mediano: dispersione tra le 12 partenze.")
    sheet_from_df(wb, "Trade_log", tl, "Ogni LEAPS acquistata (partenza gennaio, IV = 1,10 x volatilita' realizzata, mezzo spread 3%)",
                  "k_over_s = strike / prezzo dell'azione al momento dell'acquisto (sotto 1 = in the money). premio_pagato_su_S include il mezzo spread. Nel calcolatore il prezzo e' normalizzato a 100.")
    sheet_from_df(wb, "Rendimenti_annui", ann, "Rendimenti annui netti (EUR), partenza gennaio", "2026 = da inizio anno al " + dec["last_date"])
    sheet_from_df(wb, "Scenari", scen, "Scenari: quota in premi, moltiplicatore di IV, mezzo spread (top-1 e top-3, partenza gennaio)",
                  "Campione 2009 completo; campione 1997 solo con IV 1,1x e spread 3%.")

    # ---- live calculator
    ws = wb.create_sheet("Calcolatore_BS")
    r = title(ws, "Calcolatore LEAPS (Black-Scholes-Merton) e profilo a scadenza",
              "Celle gialle = input modificabili (blu). Tutto il resto e' calcolato con formule. Esempio iniziale: LEAPS del 2-1-2026 sul vincitore 2025 (Sandisk), prezzo normalizzato a 100.")
    ex = tl[(tl.campione == "core 2009-2026YTD") & (tl.regola == "top-1")].iloc[-1]
    inputs = [("Capitale totale (EUR)", 100000, "#,##0"), ("Quota del capitale in premi", 0.35, "0.0%"),
              ("Prezzo azione S (USD)", 100.0, "#,##0.00"),
              ("Strike K (USD)", round(100.0 * float(ex.k_over_s), 2), "#,##0.00"),
              ("Anni a scadenza T", round(float(ex.anni_a_scadenza), 4), "0.000"),
              ("Tasso privo di rischio r (cont.)", 0.035, "0.00%"), ("Rendimento da dividendi q", 0.0, "0.00%"),
              ("Volatilita' implicita sigma", round(float(ex.iv), 4), "0.0%"), ("Mezzo spread", 0.03, "0.0%"),
              ("Cambio EUR/USD (USD per 1 EUR)", 1.17, "0.0000"), ("Aliquota plusvalenze", 0.26, "0%")]
    ws.cell(row=r, column=1, value="Input").font = F_SUB
    r += 1
    cell = {}
    for k, v, fmt in inputs:
        ws.cell(row=r, column=1, value=k).font = F_BOLD
        c = ws.cell(row=r, column=2, value=v)
        c.font, c.fill, c.border, c.number_format = F_INPUT, INPUT_FILL, BOX, fmt
        cell[k] = f"B{r}"
        r += 1
    ws[cell["Cambio EUR/USD (USD per 1 EUR)"]].comment = Comment("Ipotesi di esempio, da aggiornare al cambio del giorno.", "GRMS")
    ws[cell["Tasso privo di rischio r (cont.)"]].comment = Comment("Ipotesi di esempio: usare il rendimento del Treasury a 1 anno del giorno.", "GRMS")
    S, K, T, rr, q, sg, hs, fx, tx = (cell[k] for k in ["Prezzo azione S (USD)", "Strike K (USD)", "Anni a scadenza T",
                                                       "Tasso privo di rischio r (cont.)", "Rendimento da dividendi q",
                                                       "Volatilita' implicita sigma", "Mezzo spread",
                                                       "Cambio EUR/USD (USD per 1 EUR)", "Aliquota plusvalenze"])
    cap, quota = cell["Capitale totale (EUR)"], cell["Quota del capitale in premi"]
    r += 1
    ws.cell(row=r, column=1, value="Calcolo").font = F_SUB
    r += 1
    calc = [("d1", f"=(LN({S}/{K})+({rr}-{q}+{sg}^2/2)*{T})/({sg}*SQRT({T}))", "0.0000"),
            ("d2", f"=B{r}-{sg}*SQRT({T})", "0.0000"),
            ("Prezzo call teorico (mid, USD)", f"={S}*EXP(-{q}*{T})*NORMSDIST(B{r})-{K}*EXP(-{rr}*{T})*NORMSDIST(B{r + 1})", "#,##0.00"),
            ("Premio / prezzo azione", f"=B{r + 2}/{S}", "0.0%"),
            ("Prezzo di acquisto (ask) per azione sottostante, USD", f"=B{r + 2}*(1+{hs})", "#,##0.00"),
            ("Delta", f"=EXP(-{q}*{T})*NORMSDIST(B{r})", "0.00"),
            ("Budget premi (EUR)", f"={cap}*{quota}", "#,##0"),
            ("Budget premi (USD)", f"=B{r + 6}*{fx}", "#,##0"),
            ("Contratti (1 contratto = 100 azioni)", f"=ROUNDDOWN(B{r + 7}/(B{r + 4}*100),0)", "0"),
            ("Esposizione nozionale (USD)", f"=B{r + 8}*100*{S}", "#,##0"),
            ("Leva sul capitale totale (nozionale / capitale)", f"=B{r + 9}/{fx}/{cap}", "0.00x"),
            ("Prezzo di pareggio a scadenza (USD)", f"={K}+B{r + 4}", "#,##0.00"),
            ("Aumento dell'azione necessario per il pareggio", f"=B{r + 11}/{S}-1", "0.0%")]
    for k, f_, fmt in calc:
        ws.cell(row=r, column=1, value=k).font = F_BOLD
        c = ws.cell(row=r, column=2, value=f_)
        c.number_format, c.border = fmt, BOX
        r += 1
    prem_row = r - 13 + 4    # ask row
    contr_row = r - 13 + 8
    r += 1
    ws.cell(row=r, column=1, value="Profilo a scadenza (valore intrinseco, nessun valore temporale residuo)").font = F_SUB
    r += 1
    hdr = ["Variazione dell'azione", "Prezzo a scadenza (USD)", "Valore opzioni (USD)", "Plus/minus opzioni (EUR, cambio costante)",
           "Imposta 26% (EUR, senza zainetto)", "Rendimento sul capitale totale (EUR, lordo T-bill)"]
    for j, h in enumerate(hdr, 1):
        c = ws.cell(row=r, column=j, value=h)
        c.font, c.border = F_BOLD, BOX
    r += 1
    for chg in (-0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6, 1.0, 1.5, 2.0):
        ws.cell(row=r, column=1, value=chg).number_format = "+0%;-0%;0%"
        ws.cell(row=r, column=2, value=f"={S}*(1+A{r})").number_format = "#,##0.00"
        ws.cell(row=r, column=3, value=f"=MAX(B{r}-{K},0)*100*$B${contr_row}").number_format = "#,##0"
        ws.cell(row=r, column=4, value=f"=(C{r}-$B${contr_row}*100*$B${prem_row})/{fx}").number_format = "#,##0;(#,##0)"
        ws.cell(row=r, column=5, value=f"=MAX(D{r},0)*{tx}").number_format = "#,##0"
        ws.cell(row=r, column=6, value=f"=(D{r}-E{r})/{cap}").number_format = "0.0%"
        for j in range(1, 7):
            ws.cell(row=r, column=j).border = BOX
        r += 1
    r += 1
    para(ws, r, "Nota: il calcolo usa il cambio costante; nella realta' la plus/minus fiscale si calcola in euro ai cambi delle date di acquisto e vendita. "
         "La parte in T-bill (65% nell'esempio) rende il tasso del T-bill al netto del 12,5%, non incluso nella tabella.", font=F_NOTE, merge_to=8, height=30)
    ws.column_dimensions["A"].width = 46
    for col in "BCDEF":
        ws.column_dimensions[col].width = 22
    wb.save(OUT / "GRMS_JanuaryBuy_LEAPS.xlsx")
    summ.to_csv(OUT / "LP_sintesi.csv", index=False)
    tl.to_csv(OUT / "LP_trade_log.csv", index=False)
    print(summ.round(3).to_string())


if __name__ == "__main__":
    main()
