"""
Review of reports/02_indagine_anomalie.md: every quantitative statement is recomputed
from the evidence files (CSV, logs, patches.py docstring) and compared with the value
written in the report. Read-only; run from the repository root:

    .venv/bin/python logs/fase_1_3bis/revisione/verifica_tracciabilita.py

Prints one line per statement and the number of mismatches.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parents[3]
T = R / "outputs" / "tables"
rows = []


def chk(sec, claim, reported, value, source, tol=0.0, label="VERIFICATO"):
    if isinstance(reported, (int, float, np.floating, np.integer)) and isinstance(value, (int, float, np.floating, np.integer)):
        ok = abs(float(reported) - float(value)) <= tol
    else:
        ok = str(reported) == str(value)
    rows.append(dict(sezione=sec, affermazione=claim, valore_nel_rapporto=reported, valore_dalle_evidenze=value,
                     fonte=source, esito="OK" if ok else "DIVERSO", etichetta=label))


tr = pd.read_csv(T / "f13b_trasformazioni_pipeline.csv").iloc[0]
gs = pd.read_csv(T / "f13b_giorni_segnalati.csv")
ss = pd.read_csv(T / "f13b_serie_segnalate.csv")
rp = pd.read_csv(T / "f13b_riparazioni.csv")
cf = pd.read_csv(T / "f13b_cambi_di_fonte.csv")
sd = pd.read_csv(T / "f13b_serie_sintetiche_dettaglio.csv").set_index("label")
cl = pd.read_csv(T / "f13b_sintetiche_classifiche.csv")
sc = pd.read_csv(T / "f13b_sintetiche_scenari_documentali.csv")
qp = pd.read_csv(T / "f13b_quattro_posizioni.csv").set_index(["label", "anno_detenzione"])
s13 = pd.read_csv(T / "f13_serie_sintetiche.csv").set_index("label")
ff = pd.read_csv(T / "f13_ffill_per_anno.csv")
t3 = pd.read_csv(R / "work" / "replica_originale" / "out" / "AN_top3_anno.csv")
par = json.load(open(R / "source_original" / "results" / "AN_parametri.json"))

# ---------------------------------------------------------------- section 1
F = "f13b_trasformazioni_pipeline.csv"
for k, v in (("righe_titoli_del_pannello", 5807722), ("righe_fuori_calendario", 15131), ("di_cui_prima_del_1988_01_04", 14917),
             ("di_cui_dopo_ultimo_giorno", 2), ("di_cui_giorni_di_borsa_chiusa", 212), ("dividendi_su_righe_fuori_calendario", 147),
             ("dividendi_scartati_dentro_il_periodo", 0), ("righe_duplicate_scartate", 0)):
    chk("1.1", k, v, int(tr[k]), F)
chk("1.1", "celle riempite col valore precedente", 11231, int(ff.celle_adj_riempite.sum()),
    "f13_ffill_per_anno.csv; logs/fase_1_0/replica_data_layer.txt (filled=11231)")
chk("1.1", "giorni segnalati", 357, len(gs), "f13b_giorni_segnalati.csv")
chk("1.1", "serie segnalate", 156, len(ss), "f13b_serie_segnalate.csv")
chk("1.1", "giorni riscritti", 30, int(gs.riparazione_registrata.sum()), "f13b_giorni_segnalati.csv")
chk("1.1", "serie con riparazioni", 24, int((ss.riparazioni_registrate > 0).sum()), "f13b_serie_segnalate.csv")
nr = ss[ss.riparazioni_registrate == 0]
chk("1.2", "serie senza riparazioni", 132, len(nr), "f13b_serie_segnalate.csv")
chk("1.2", "OHLC identici nelle 132 serie", True, bool(nr.open_high_low_close_identici.all()), "f13b_serie_segnalate.csv")
chk("1.2", "celle adj diverse", 785845, int(nr.celle_adj_diverse.sum()), "f13b_serie_segnalate.csv")
chk("1.2", "celle adj nella vita", 805506, int(nr.celle_adj_vita.sum()), "f13b_serie_segnalate.csv")
chk("1.2", "scarto relativo massimo (1,6e-14)", 1.6e-14, nr.max_diff_relativa_adj.max(), "f13b_serie_segnalate.csv", tol=0.05e-14)
chk("1.2", "mediana tra le serie dello scarto massimo (6,2e-15)", 6.2e-15, nr.max_diff_relativa_adj.median(), "f13b_serie_segnalate.csv", tol=0.05e-15)
chk("1.2", "scarto assoluto massimo (8,6e-12)", 8.6e-12, nr.max_diff_assoluta_adj.max(), "f13b_serie_segnalate.csv", tol=0.05e-12)
d = gs[(gs.label == "DELL-201310") & (gs.data == "1998-03-09")].iloc[0]
for k, v in (("close_grezzo_prima", 138.50), ("close_grezzo", 63.13), ("adj_grezzo_prima", 17.3125), ("adj_grezzo", 15.7825),
             ("adj_pannello_prima", 17.3125), ("adj_pannello", 15.7825)):
    chk("1.2", f"Dell 9-3-1998 {k}", v, float(d[k]), "f13b_giorni_segnalati.csv", tol=0.005)
chk("1.2", "Dell 9-3-1998 rend. chiusura (-54,4%)", -0.544, float(d.rend_close), "f13b_giorni_segnalati.csv", tol=0.0005)
chk("1.2", "Dell 9-3-1998 rend. rettificato (-8,8%)", -0.088, float(d.rend_rettificato_fornitore), "f13b_giorni_segnalati.csv", tol=0.0005)
fr = gs[gs.categoria == "frazionamento registrato"]
chk("1.3", "giorni di frazionamento registrato", 356, len(fr), "f13b_giorni_segnalati.csv")
for src, v in (("jb:tiingo", 242), ("jb:wiki", 111), ("jb:yahoo", 3)):
    chk("1.3", f"frazionamenti fonte {src}", v, int((fr.fonte == src).sum()), "f13b_giorni_segnalati.csv")
ac = gs[gs.label == "ACAS-201701"].iloc[0]
chk("1.3", "ACAS dividendo", 1.07, float(ac.dividendo), "f13b_giorni_segnalati.csv", tol=1e-9)
chk("1.3", "ACAS prezzo precedente", 3.08, float(ac.close_grezzo_prima), "f13b_giorni_segnalati.csv", tol=1e-9)
chk("1.3", "ACAS rendimento da dividendo (34,7%)", 0.347, float(ac.rend_dividendo), "f13b_giorni_segnalati.csv", tol=0.0005)
chk("1.3", "ACAS non riscritto", False, bool(ac.riparazione_registrata), "f13b_giorni_segnalati.csv")
chk("1.3", "ACAS fuori dalla top-3", False, bool(t3.label.str.startswith("ACAS").any()), "work/replica_originale/out/AN_top3_anno.csv")
chk("1.3", "cambi di fonte tra i giorni segnalati", 0, int((gs.fonte_giorno_prima != gs.fonte).sum()), "f13b_giorni_segnalati.csv")
chk("1.4", "riparazioni riprodotte dalla regola", 30, int(rp.coincide_con_log_storico.sum()), "f13b_riparazioni.csv")
cls = rp.classe_riparazione_stimata.value_counts()
for k, v in (("riparazione coerente con il frazionamento registrato", 11),
             ("riparazione che sostituisce un rendimento coerente con il frazionamento registrato", 9),
             ("variazione marginale (< 0,5 punti)", 4), ("non determinabile (nessuna lettura con movimento ordinario)", 6)):
    chk("1.4", f"classe: {k}", v, int(cls.get(k, 0)), "f13b_riparazioni.csv", label="STIMA")
u = rp[(rp.label == "USB-200102") & (rp.data == "1997-01-16")].iloc[0]
chk("1.4", "USB 16-1-1997 rend. fornitore (+197,9%)", 1.979, float(u.rend_rettificato_fornitore), "f13b_riparazioni.csv", tol=0.0005)
chk("1.4", "USB 16-1-1997 rend. chiusura (-0,7%)", -0.007, float(u.rend_close), "f13b_riparazioni.csv", tol=0.0005)
chk("1.4", "USB 16-1-1997 frazionamento 3:1", 3.0, float(u.frazionamento_registrato), "f13b_riparazioni.csv", tol=1e-9)
pl = rp[rp.label == "PLL-201508"].iloc[0]
chk("1.4", "PLL rend. chiusura (-28,15%)", -0.2815, float(pl.rend_close), "f13b_riparazioni.csv", tol=0.00005)
chk("1.4", "PLL rend. fornitore (+7,78%)", 0.0778, float(pl.rend_rettificato_fornitore), "f13b_riparazioni.csv", tol=0.00005)
chk("1.4", "PLL valore riparato (-4,19%)", -0.0419, float(pl.valore_scelto), "f13b_riparazioni.csv", tol=0.00005)
chk("1.4", "PLL candidato scelto", "prezzo corretto x4/3", pl.candidato_scelto, "f13b_riparazioni.csv")
chk("1.4", "PLL frazionamento registrato 3:2", 1.5, float(pl.frazionamento_registrato), "f13b_riparazioni.csv", tol=1e-6)
pg = gs[(gs.label == "PLL-201508") & (gs.data == "1991-12-30")].iloc[0]
chk("1.4", "PLL 27-12-1991 adj fornitore 15,016", 15.016, float(pg.adj_grezzo_prima), "f13b_giorni_segnalati.csv", tol=0.0005)
chk("1.4", "PLL 27-12-1991 adj pannello 16,893", 16.893, float(pg.adj_pannello_prima), "f13b_giorni_segnalati.csv", tol=0.0005)
chk("1.4", "PLL livello precedente +12,5%", 0.125, float(pg.adj_pannello_prima / pg.adj_grezzo_prima - 1), "f13b_giorni_segnalati.csv", tol=0.0005)
rk = rp[rp.classificato == True]   # noqa: E712
chk("1.4", "riparazioni fuori dagli anni di classifica 1996-2025", 3, int(rp.anno_classifica.isna().sum()), "f13b_riparazioni.csv")
chk("1.4", "riparazioni in anni di classifica su titoli non classificati", 19,
    int((rp.anno_classifica.notna() & (rp.classificato == False)).sum()), "f13b_riparazioni.csv")   # noqa: E712
chk("1.4", "riparazioni nell'anno di classifica di un membro classificato", 8, len(rk), "f13b_riparazioni.csv")
chk("1.4", "baseline: migliore posizione con la riparazione (17, Citigroup 1996)", 17, int(rk.posizione_con_riparazione.min()), "f13b_riparazioni.csv")
chk("1.4", "baseline: nessuna riparazione in top-3", 0, int((rk.posizione_con_riparazione <= 3).sum()), "f13b_riparazioni.csv")
chk("1.4", "controfattuale: casi in cui la top-3 cambierebbe", 1, int((rk.posizione_con_valore_fornitore <= 3).sum()), "f13b_riparazioni.csv")
ub = rk[rk.label == "USB-200102"].set_index("anno_classifica")
chk("1.4", "USB classifica 1997 con riparazione: posizione 43", 43, int(ub.loc[1997, "posizione_con_riparazione"]), "f13b_riparazioni.csv")
chk("1.4", "USB classifica 1997 con riparazione: +66,4%", 0.664, float(ub.loc[1997, "rend_anno_con_riparazione"]), "f13b_riparazioni.csv", tol=0.0005)
chk("1.4", "USB classifica 1997 controfattuale: posizione 1", 1, int(ub.loc[1997, "posizione_con_valore_fornitore"]), "f13b_riparazioni.csv")
chk("1.4", "USB classifica 1997 controfattuale: +399,2%", 3.992, float(ub.loc[1997, "rend_anno_con_valore_fornitore"]), "f13b_riparazioni.csv", tol=0.0005)
chk("1.4", "Dell 1° nella classifica 1997 della baseline (+216,2%)", 2.162,
    float(t3[(t3.anno_T0 == 1997) & (t3.posizione == 1)].rend_T0.iat[0]), "work/replica_originale/out/AN_top3_anno.csv", tol=0.0005)
pb = rk[rk.label == "PBG-201002"].iloc[0]
chk("1.4", "PBG 2001: 80 -> 6", "80->6", f"{int(pb.posizione_con_riparazione)}->{int(pb.posizione_con_valore_fornitore)}", "f13b_riparazioni.csv")
cc = rk[rk.label == "C-199811"].iloc[0]
chk("1.4", "Citigroup 1996: 17 -> 14", "17->14", f"{int(cc.posizione_con_riparazione)}->{int(cc.posizione_con_valore_fornitore)}", "f13b_riparazioni.csv")
# counterfactual table of section 1.4: (label, ranking year) -> baseline position/return, counterfactual position/return
CF = {("USB-200102", 1997): (43, 0.664, 1, 3.992), ("PBG-201002", 2001): (80, 0.192, 6, 1.384),
      ("USB-200102", 1999): (260, -0.297, 23, 1.110), ("XTO-201006", 2004): (125, 0.250, 27, 0.563),
      ("C-199811", 1996): (17, 0.566, 14, 0.671), ("HBI", 2015): (162, 0.093, 110, 0.168),
      ("TWX-201806", 2009): (120, 0.595, 383, 0.064), ("EVHC-201810", 2016): (475, -0.188, 475, -0.186)}
for (lab, yr), (p0, r0, p1, r1) in CF.items():
    x = rk[(rk.label == lab) & (rk.anno_classifica == yr)].iloc[0]
    chk("1.4", f"controfattuale {lab} {yr}", f"{p0}|{r0:+.3f}|{p1}|{r1:+.3f}",
        f"{int(x.posizione_con_riparazione)}|{x.rend_anno_con_riparazione:+.3f}|{int(x.posizione_con_valore_fornitore)}|{x.rend_anno_con_valore_fornitore:+.3f}",
        "f13b_riparazioni.csv")
chk("1.4", "controfattuale: le 9 sostitutive non cambiano la top-3", 0,
    int(((rk.classe_riparazione_stimata == "riparazione che sostituisce un rendimento coerente con il frazionamento registrato")
         & (rk.posizione_con_valore_fornitore <= 3)).sum()), "f13b_riparazioni.csv")
chk("1.5", "giorni di cambio fonte", 90, len(cf), "f13b_cambi_di_fonte.csv")
chk("1.5", "scarto massimo nei cambi di fonte (4,72%)", 0.0472, float(cf.scarto_regola.abs().max()), "f13b_cambi_di_fonte.csv", tol=0.00005)
chk("1.5", "giorni di cambio fonte con |rend.| > 10%", 1, int((cf.rend_rettificato.abs() > 0.10).sum()), "f13b_cambi_di_fonte.csv")
v = cf[cf.label == "VNT"].iloc[0]
chk("1.5", "Vontier 9-10-2020 (-16,1%)", -0.161, float(v.rend_rettificato), "f13b_cambi_di_fonte.csv", tol=0.0005)

# ---------------------------------------------------------------- section 2
DOC = {"PATCH_PCS-2000": (3.432, -0.601, "2000-09-15"), "PATCH_NXTL-2000": (3.365, -0.520, "2000-11-10"),
       "PATCH_RBK-2001": (2.34, -0.031, ""), "PATCH_DYN-2001": (2.202, -0.542, "2001-09-17"),
       "PATCH_PVN-2003": (0.828, 0.794, ""), "PATCH_AV-2004": (4.28, 0.33, ""), "PATCH_DYN-2004": (2.626, 0.079, ""),
       "PATCH_TXU-2005": (1.78, 0.599, ""), "PATCH_UST-2009": (0.266, 0.0, "")}
for lab, (rt, ht, sdt) in DOC.items():
    x = sd.loc[lab]
    chk("2.1", f"{lab} valori del codice", f"{rt:g}|{ht:g}|{sdt}",
        f"{x.codice_rank_tr:g}|{x.codice_hold_tr:g}|{x.codice_stop_date if isinstance(x.codice_stop_date, str) else ''}",
        "f13b_serie_sintetiche_dettaglio.csv")
chk("2.1", "member_from uguale al file di composizione", 8, int(sd.member_from_uguale_al_file.sum()), "f13b_serie_sintetiche_dettaglio.csv")
chk("2.1", "eccezione member_from: Dynegy 2004", "2002-01-02|2000-10-03",
    f"{sd.loc['PATCH_DYN-2004', 'codice_member_from']}|{sd.loc['PATCH_DYN-2004', 'inizio_nel_file_composizione']}", "f13b_serie_sintetiche_dettaglio.csv")
chk("2.1", "ticker originali con prezzi", 0, int(sd.ticker_originale_con_prezzi.sum()), "f13b_serie_sintetiche_dettaglio.csv")
stp = sd[sd.codice_stop_date.notna()]
chk("2.3", "serie con prezzo di fine anno = 1,0001 x base", 3, int(np.isclose(sd.prezzo_fine_anno_classifica_su_base, 1.0001).sum()),
    "f13b_serie_sintetiche_dettaglio.csv")
chk("2.3", "serie con prezzo di fine anno = base", 6, int(np.isclose(sd.prezzo_fine_anno_classifica_su_base, 1.0).sum()),
    "f13b_serie_sintetiche_dettaglio.csv")
s3 = s13.loc[stp.index]
chk("2.3", "rend. classifica: scarto minimo (3,2e-4)", 3.2e-4, float(s3.diff_rend_classifica.min()), "f13_serie_sintetiche.csv", tol=0.05e-4)
chk("2.3", "rend. classifica: scarto massimo (4,4e-4)", 4.4e-4, float(s3.diff_rend_classifica.max()), "f13_serie_sintetiche.csv", tol=0.05e-4)
chk("2.3", "rend. detenzione: scarto (−4,0e-5 … −4,8e-5)", "-4.0e-05|-4.8e-05",
    f"{s3.diff_rend_detenzione.max():.1e}|{s3.diff_rend_detenzione.min():.1e}", "f13_serie_sintetiche.csv")
chk("2.3", "rend. con stop delle 3 serie = -35%", True,
    bool(np.allclose(t3[t3.label.isin(stp.index)].rend_T1_con_stop, -0.35, atol=1e-12)), "work/replica_originale/out/AN_top3_anno.csv")
chk("2.3", "riga x0,9999 attiva", 0, int(stp.riga_0_9999_attiva.sum()), "f13b_serie_sintetiche_dettaglio.csv")
chk("2.3", "prezzo nel giorno di stop = base x 0,65", True, bool(np.allclose(stp.a_giorno_stop_su_base_x_065, 1.0, atol=1e-12)),
    "f13b_serie_sintetiche_dettaglio.csv")
chk("2.3", "prezzo nel giorno di stop vs livello (-1e-4)", -1e-4, float(stp.a_giorno_stop_su_livello_meno_1.mean()),
    "f13b_serie_sintetiche_dettaglio.csv", tol=1e-7)
chk("2.3", "stop anche senza 1,0001 (uguaglianza)", 3, int(stp.stop_scatterebbe_senza_fattore_1_0001.sum()), "f13b_serie_sintetiche_dettaglio.csv")
chk("2.4", "dividendi delle serie sintetiche", 0.0, float(sd.dividendi_totali.sum()), "f13b_serie_sintetiche_dettaglio.csv")
chk("2.4", "massimo = minimo = chiusura = prezzo rettificato", 9, int(sd.high_low_close_uguali_adj.sum()), "f13b_serie_sintetiche_dettaglio.csv")
chk("2.4", "apertura = chiusura precedente", 9, int(sd.ingresso_uguale_chiusura_precedente.sum()), "f13b_serie_sintetiche_dettaglio.csv")
chk("2.4", "volatilita' proxy 0,526", 0.526, float(par["proxy_sigma_reconstructed"]), "source_original/results/AN_parametri.json", tol=0.0005)
fd = cl[(cl.anno_classifica == 2008) & (cl.posizione == 1)].iloc[0]
chk("2.4", "Family Dollar 1a nel 2008 (+38,6%)", "FDO-201507|0.386", f"{fd.label}|{fd.rend_anno:.3f}", "f13b_sintetiche_classifiche.csv")
for lab, low, lvl, rep in (("PATCH_RBK-2001", 18.50, 17.8, 0.039), ("PATCH_DYN-2004", 3.46, 2.8, 0.236), ("PATCH_PVN-2003", 5.25, 4.2, 0.250),
                           ("PATCH_AV-2004", 11.95, 8.4, 0.423), ("PATCH_TXU-2005", 30.22, 21.0, 0.439)):
    doc = sd.loc[lab, "doc_stop"]
    m = re.search(r"low ([\d.]+) vs ~([\d.]+)", doc)
    ok = m and float(m.group(1)) == low and float(m.group(2)) == lvl
    chk("2.4", f"{lab} margine minimo/livello dalla docstring", rep, (low / lvl - 1) if ok else f"non trovato in '{doc}'",
        "patches.py (docstring), via f13b_serie_sintetiche_dettaglio.csv doc_stop; aritmetica", tol=0.0006, label="STIMA (livelli '~')")
MG = (("PATCH_PCS-2000", 0.0153, None), ("PATCH_NXTL-2000", 0.120, "ORCL"), ("PATCH_RBK-2001", 0.0430, None),
      ("PATCH_DYN-2001", 0.0244, None), ("PATCH_PVN-2003", 0.0370, None), ("PATCH_AV-2004", 0.443, None),
      ("PATCH_DYN-2004", 0.0030, "PMCS-201601"), ("PATCH_TXU-2005", 0.407, "VLO"), ("PATCH_UST-2009", 0.0062, None))
for lab, mg, q4 in MG:
    chk("2.5", f"{lab} margine su chi segue", mg, float(sd.loc[lab, "margine_su_chi_segue"]), "f13b_serie_sintetiche_dettaglio.csv",
        tol=0.0005 if mg < 0.1 else 0.0015)
    if q4:
        chk("2.5", f"{lab} quarto classificato", q4, sd.loc[lab, "quarto_classificato"], "f13b_serie_sintetiche_dettaglio.csv")
for yr, pos, lab, val in ((1999, 4, "ORCL", 2.898), (2000, 2, "PATCH_DYN-2001", 2.202), (2000, 3, "EOG", 2.126), (2002, 2, "BSX", 0.763),
                          (2003, 3, "PATCH_DYN-2004", 2.626), (2003, 4, "PMCS-201601", 2.615), (2004, 4, "VLO", 0.976),
                          (2008, 3, "HRB", 0.258), (2008, 4, "AMGN", 0.244)):
    x = cl[(cl.anno_classifica == yr) & (cl.posizione == pos)].iloc[0]
    chk("2.5", f"classifica {yr}, posizione {pos}", f"{lab}|{val}", f"{x.label}|{x.rend_anno:.3f}", "f13b_sintetiche_classifiche.csv")
chk("2.5", "ordine invariato senza 1,0001", True, bool(sd.ordine_invariato_senza_1_0001.all()), "f13b_serie_sintetiche_dettaglio.csv")
SC = ((0, -0.511, -0.319, 0.0, 0.0), (1, -0.055, -0.055, -0.0183, -0.0183), (2, 0.017, 0.017, 0.0057, 0.0057),
      (3, 0.0, -0.319, 0.0, -0.1063), (4, 0.0, 0.0, -0.1766, -0.1430))
for i, a, b, c, dd in SC:
    x = sc.iloc[i]
    chk("2.6", f"scenario {i + 1}: {x.scenario[:60]}", f"{a:+.3f}|{b:+.3f}|{c:+.4f}|{dd:+.4f}",
        f"{x.delta_vincitore_senza_stop:+.3f}|{x.delta_vincitore_con_stop:+.3f}|{x.delta_prime_tre_senza_stop:+.4f}|{x.delta_prime_tre_con_stop:+.4f}",
        "f13b_sintetiche_scenari_documentali.csv", label="STIMA" if i == 4 else "RIPORTATO + aritmetica")
pm = sc.iloc[4]
chk("2.6", "PMC-Sierra 2004 senza stop (-45,1%)", -0.451, float(pm.rend_posizione_alternativo_senza_stop),
    "f13b_sintetiche_scenari_documentali.csv; annual_study.stock_year()", tol=0.0005, label="STIMA")
chk("2.6", "PMC-Sierra 2004 stop il 29-4-2004", True, "2004-04-29" in pm.nota, "f13b_sintetiche_scenari_documentali.csv", label="STIMA")
w = t3[(t3.posizione == 1) & t3.stop_toccato & (t3.anno_detenzione <= 2025)]
chk("2.6", "stop sul vincitore 1997-2025, tutti utili", "4|4", f"{len(w)}|{int((w.rend_T1_con_stop > w.rend_T1_senza_stop).sum())}",
    "work/replica_originale/out/AN_top3_anno.csv")

# ---------------------------------------------------------------- section 3
Q = {("DELL-201310", 1998): dict(ingresso="1998-01-02", ap=84.81, rett=10.6013, lv=6.8908, lvg=55.1265, dc="1998-09-10",
                                 o=54.88, h=55.75, l=53.00, c=54.75, fat=4, coer=2.846, mn=0.440, ex=36.595, ret=2.4520, art=-0.3529,
                                 dpos=-2.805, dv=-2.805, d3=-0.935),
     ("DELL-201310", 1999): dict(ingresso="1999-01-04", ap=74.87, rett=37.435, lv=24.3328, lvg=48.6655, dc="1999-03-08",
                                 o=44.00, h=45.50, l=43.03, c=45.38, fat=2, coer=0.768, mn=0.289, ex=51.00, ret=0.3624, art=-0.4123,
                                 dpos=-0.775, dv=-0.775, d3=-0.258),
     ("EMC-201609", 1999): dict(ingresso="1999-01-04", ap=86.75, rett=20.1447, lv=13.0941, lvg=56.3875, dc="1999-06-01",
                                o=50.94, h=50.94, l=49.00, c=49.06, fat=2, coer=0.738, mn=0.490, ex=50.762, ret=1.5199, art=-0.4128,
                                dpos=-1.933, dv=0.0, d3=-0.644),
     ("CTRA", 2012): dict(ingresso="2012-01-03", ap=78.11, rett=14.2039, lv=9.2325, lvg=50.7715, dc="2012-01-26",
                          o=33.35, h=33.95, l=31.76, c=32.44, fat=2, coer=0.251, mn=0.136, ex=18.121, ret=0.2758, art=-0.5730,
                          dpos=-0.849, dv=-0.849, d3=-0.283)}
FQ = "f13b_quattro_posizioni.csv"
for key, e in Q.items():
    x = qp.loc[key]
    tag = f"{key[0]} {key[1]}"
    chk("3.2", f"{tag} data d'ingresso", e["ingresso"], x.data_ingresso, FQ)
    for k, col, tol in (("ap", "apertura_ingresso_grezza", 0.005), ("rett", "ingresso_rettificato", 0.00005),
                        ("lv", "livello_stop_rettificato", 0.00005), ("lvg", "livello_stop_grezzo_base_ingresso", 0.00005),
                        ("o", "open_grezzo", 0.005), ("h", "high_grezzo", 0.005), ("l", "low_grezzo", 0.005), ("c", "close_grezzo", 0.005),
                        ("fat", "fattore_frazionamenti_ingresso_data", 0), ("coer", "low_coerente_su_livello", 0.0005),
                        ("mn", "minimo_anno_su_livello_rett", 0.0005), ("ex", "codice_prezzo_uscita_rett", 0.0005),
                        ("ret", "codice_rend", 0.00005), ("art", "controllo_errato_rend_artefatto", 0.00005),
                        ("dpos", "diff_posizione_errato_meno_codice", 0.0005), ("dv", "diff_vincitore_errato", 0.0005),
                        ("d3", "diff_prime_tre_errato", 0.0005)):
        chk("3.2", f"{tag} {col}", e[k], float(x[col]), FQ, tol=tol)
    chk("3.2", f"{tag} data contestata", e["dc"], x.data_contestata, FQ)
    chk("3.2", f"{tag} uscita codice = controllo corretto", True,
        bool(x.codice_data_uscita == x.controllo_corretto_data_uscita and abs(x.diff_posizione_corretto_meno_codice) < 1e-15), FQ)
x = qp.loc[("CTRA", 2012)]
chk("3.2", "Coterra: 4 dividendi (0,17%)", "4|0.0017", f"{int(x.dividendi_in_detenzione)}|{x.rend_dividendi_in_detenzione:.4f}", FQ)
chk("3.3", "Coterra: differenza coerente/rettificato (0,04 punti)", 0.0004, float(x.low_rett_su_livello_rett - x.low_coerente_su_livello), FQ, tol=0.00005)
chk("3.3", "distanza minima dal livello: 13,6% … 49,0%", "0.136|0.490",
    f"{qp.minimo_anno_su_livello_rett.min():.3f}|{qp.minimo_anno_su_livello_rett.max():.3f}", FQ)
x = qp.loc[("DELL-201310", 1999)]
chk("3.2", "Dell 1999: prezzi rettificati = grezzi nel giorno contestato", True,
    bool(abs(x.open_rett - x.open_grezzo) < 1e-9 and abs(x.low_rett - x.low_grezzo) < 1e-9), FQ)
qd = pd.read_csv(T / "f13b_quattro_posizioni_giornaliero.csv")
dd = qd[(qd.label == "DELL-201310") & (qd.anno_detenzione == 1999)]
after = dd[dd.data >= "1999-03-08"]
chk("3.2", "Dell 1999: fattore di rettifica = 1 dall'8-3-1999 a fine anno", True,
    bool(np.allclose(after.close_rett, after.close, rtol=0, atol=1e-9)), "f13b_quattro_posizioni_giornaliero.csv")
chk("3.2", "Dell 1999: nessun dividendo nel 1999", 0, int((dd[dd.data >= "1999-01-01"].dividendo > 0).sum()),
    "f13b_quattro_posizioni_giornaliero.csv")

# ---------------------------------------------------------------- section 5
integ = (R / "logs" / "fase_1_3bis" / "integrita.txt").read_text()
chk("5", "test superati a fine fase", 20, int(re.search(r"(\d+) passed", integ).group(1)), "logs/fase_1_3bis/integrita.txt")
hl = [ln for ln in (R / "logs" / "fase_1_3bis" / "hash_file_utilizzati.txt").read_text().splitlines() if not ln.startswith("#")]
chk("5", "file con hash registrato", 20, len(hl), "logs/fase_1_3bis/hash_file_utilizzati.txt")
rp_txt = (R / "logs" / "fase_1_3bis" / "revisione" / "riproducibilita.txt").read_text()
chk("5.1", "riproducibilita': file identici / diversi", "12|0", f"{rp_txt.count('IDENTICO')}|{rp_txt.count('DIVERSO')}",
    "logs/fase_1_3bis/revisione/riproducibilita.txt")
chk("5.1", "riproduzione bit-identica della baseline (Fase 1.3)", "12/12",
    f"{int(pd.read_csv(T / 'f13_confronto_file.csv').byte_identici.sum())}/{len(pd.read_csv(T / 'f13_confronto_file.csv'))}",
    "f13_confronto_file.csv")

df = pd.DataFrame(rows)
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 70)
print(df.to_string(index=False))
bad = df[df.esito != "OK"]
print(f"\nstatements checked: {len(df)}; mismatches: {len(bad)}")
if len(bad):
    print(bad.to_string(index=False))
