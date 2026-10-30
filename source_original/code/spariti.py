"""
"Titoli spariti" - survivorship audit requested by the client.

Outputs (out/):
  SP1_top3_stato.csv          every top-3 name 1996-2026 (S&P 500) / 2007-2026 (Nasdaq-100): is the company still
                              listed today? if not, last price date and corporate outcome; next-year return.
  SP2_membri_senza_dati.csv   every point-in-time member, every year, that cannot be ranked, with the reason
                              and (where Wikipedia's change log has it) name and reason for leaving the index.
  SP3_vincitori_reinseriti.csv  the winners missing from the free data and reinserted from SEC filings, with sources;
                              plus the known members still missing below the top-3.
  SP4_riepilogo_anno.csv      per index-year: members, ranked, not ranked, coverage, verification of the top-3.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import patches
from build_top3 import KNOWN_MISSING, VERIFIED
from config import OUT, PROC
from names import company
from panel import Panel
from signals import ranking, year_end_rows

# Corporate outcome of the top-3 names that are no longer listed. Primary source: the Wikipedia change log of
# the S&P 500 (data/processed/wiki_sp500_changes.csv, which cites S&P DJI press releases); where the log has no
# entry, the outcome is the publicly announced transaction (company press releases / SEC filings).
FATE = {
    "DELL-201310": ("acquisita (LBO) da Michael Dell e Silver Lake, ott-2013; tornata in Borsa nel 2018 (ticker DELL)", "Wikipedia change log / S&P DJI"),
    "RDC": ("Rowan Companies: uscita dall'S&P 500 nel 2014; fusa con Ensco (Valaris) nel 2019", "Wikipedia change log; comunicati societari"),
    "NAV": ("Navistar: acquisita da Traton (gruppo Volkswagen) nel 2021", "comunicati societari"),
    "EMC-201609": ("EMC: acquisita da Dell, set-2016", "Wikipedia change log / S&P DJI"),
    "PATCH_PCS-2000": ("Sprint PCS (tracking stock): ricombinata nelle azioni Sprint FON nel 2004", "comunicati societari Sprint"),
    "PATCH_NXTL-2000": ("Nextel: fusa con Sprint (Sprint Nextel), ago-2005", "comunicati societari"),
    "PATCH_RBK-2001": ("Reebok: acquisita da Adidas, gen-2006", "comunicati societari"),
    "PATCH_DYN-2001": ("Dynegy: uscita dall'S&P 500 nel 2009; procedura di Chapter 11 tra il 2011 e il 2012 (un decennio dopo); fusa in Vistra nel 2018", "Wikipedia change log; comunicati societari"),
    "PATCH_DYN-2004": ("come sopra (Dynegy)", "Wikipedia change log; comunicati societari"),
    "ODP": ("Office Depot / ODP Corp.: uscita dall'S&P 500 nel 2010; acquisita da Atlas Holdings nel 2025", "Wikipedia change log; comunicati societari"),
    "JCP": ("J.C. Penney: uscita dall'S&P 500 nel 2013; Chapter 11 nel 2020 (diciannove anni dopo). Prezzi del dataset fermi al 27-3-2018", "comunicati societari"),
    "PATCH_PVN-2003": ("Providian: acquisita da Washington Mutual, ott-2005", "comunicati societari"),
    "PATCH_AV-2004": ("Avaya: acquisita (LBO Silver Lake / TPG), ott-2007", "Wikipedia change log / S&P DJI"),
    "PATCH_TXU-2005": ("TXU: acquisita (LBO KKR / TPG, poi Energy Future Holdings), ott-2007", "comunicati societari"),
    "ESRX-201812": ("Express Scripts: acquisita da Cigna, dic-2018", "Wikipedia change log / S&P DJI"),
    "FDO-201507": ("Family Dollar: acquisita da Dollar Tree, lug-2015", "Wikipedia change log / S&P DJI"),
    "PATCH_UST-2009": ("UST Inc.: acquisita da Altria per $69,50 in contanti, 6-gen-2009", "8-K Altria gen-2009; CNN 31-12-2008"),
    "XL-201809": ("XL Group: acquisita da AXA, set-2018", "Wikipedia change log / S&P DJI"),
    "CTRA": ("Coterra Energy (ex Cabot Oil & Gas): acquisita da Devon Energy, mag-2026", "Wikipedia change log / S&P DJI"),
    "S-202004": ("Sprint: uscita dall'S&P 500 nel 2013 (SoftBank); fusa con T-Mobile US, apr-2020", "Wikipedia change log; comunicati societari"),
    "EA": ("Electronic Arts: acquisita dal consorzio PIF / Silver Lake / Affinity Partners, ago-2026", "Wikipedia change log / S&P DJI"),
    "ATVI": ("Activision Blizzard: acquisita da Microsoft, ott-2023", "Wikipedia change log / S&P DJI"),
    "ABMD": ("Abiomed: acquisita da Johnson & Johnson, dic-2022", "Wikipedia change log / S&P DJI"),
    "MRO": ("Marathon Oil: acquisita da ConocoPhillips, nov-2024", "Wikipedia change log / S&P DJI"),
    "HES": ("Hess: acquisita da Chevron, lug-2025", "Wikipedia change log / S&P DJI"),
    "FWLT-201412": ("Foster Wheeler: acquisita da AMEC, nov-2014", "comunicati societari"),
    "CELG": ("Celgene: acquisita da Bristol-Myers Squibb, nov-2019", "Wikipedia change log / S&P DJI"),
    "ALXN": ("Alexion: acquisita da AstraZeneca, lug-2021", "Wikipedia change log / S&P DJI"),
}

# Real end of trading of the reconstructed names (the synthetic series stop at the end of the holding year).
PATCH_EXIT = {"PATCH_PCS-2000": "2004-04", "PATCH_NXTL-2000": "2005-08", "PATCH_RBK-2001": "2006-01",
              "PATCH_DYN-2001": "2012 (fuori S&P 500 dal 2009-12)", "PATCH_DYN-2004": "2012 (fuori S&P 500 dal 2009-12)",
              "PATCH_PVN-2003": "2005-10", "PATCH_AV-2004": "2007-10", "PATCH_TXU-2005": "2007-10",
              "PATCH_UST-2009": "2009-01-06"}

STILL_MISSING = [
    dict(anno_classifica=1999, societa="LSI Logic", rendimento_anno="+319% (S&P DJI, prezzo)", posizione_stimata="#4",
         effetto="nessuno sulla top-3 (sotto Nextel +337%)"),
    dict(anno_classifica=1999, societa="Nortel Networks", rendimento_anno="+304% (S&P DJI, prezzo)", posizione_stimata="#5",
         effetto="nessuno sulla top-3; assente dal file di membership point-in-time"),
    dict(anno_classifica=2003, societa="Novell", rendimento_anno="+215% (Forbes / S&P DJI)", posizione_stimata="#6",
         effetto="nessuno sulla top-3 (sotto Dynegy +263%)"),
]


def _reason(p: Panel, label: str, d: int, d0: int) -> str:
    if label not in p.lab_idx:
        return "nessun prezzo nel dataset gratuito"
    j = p.lab_idx[label]
    if label in getattr(p, "quarantine", set()):
        return "serie in quarantena (prezzi errati)"
    if p.first_row[j] > d:
        return "prezzi presenti solo dopo questo anno"
    if p.last_row[j] < d:
        return "prezzi terminano prima della fine dell'anno"
    if p.first_row[j] > d0:
        return "quotato da meno di 126 sedute (IPO/spin-off)"
    return "prezzo mancante a inizio anno"


def members_without_data(p: Panel, wiki: pd.DataFrame) -> pd.DataFrame:
    ye = year_end_rows(p)
    last_year = p.dates[-1].year
    rows = []
    for index, y0 in (("SPX", 1996), ("NDX", 2007)):
        for y in range(y0, last_year + 1):
            d, d0 = ye[y], ye[y - 1]
            dt = p.dates[d]
            ranked = set(ranking(p, index, d, d0, min_days=126).label)
            if index == "SPX":
                m = p.spx[(p.spx.start <= dt) & (p.spx.end.isna() | (p.spx.end > dt))]
                m = m[~m.ticker.str.startswith("PATCH_")]
                items = [(t, t, s, e) for t, s, e in zip(m.ticker, m.start, m.end)]
            else:
                m = p.ndx[(p.ndx.start <= dt) & (p.ndx.end.isna() | (p.ndx.end > dt))]
                items = [(lab if isinstance(lab, str) else None, t, s, e) for lab, t, s, e in zip(m.label, m.ticker, m.start, m.end)]
            for lab, tick, s, e in items:
                if lab in ranked:
                    continue
                patched = [pt for pt in patches.PATCHES if pt["rank_year"] == y and index == "SPX"
                           and tick.split("-")[0] in pt["label"]]
                base = tick.split("-")[0]
                # Wikipedia name only when its removal date matches the membership end (+-15 days):
                # avoids attaching the name of another company that later reused the ticker
                wk = wiki.iloc[0:0]
                if pd.notna(e):
                    wk = wiki[(wiki.removed_ticker == base) & ((wiki.date - pd.Timestamp(e)).abs().dt.days <= 15)]
                rows.append(dict(
                    indice=index, anno=y, ticker=tick, etichetta_dataset=lab or "",
                    nel_indice_dal=pd.Timestamp(s).date(), nel_indice_fino_al=(pd.Timestamp(e).date() if pd.notna(e) else ""),
                    motivo=(_reason(p, lab, d, d0) if lab else "ticker non risolto nei dati prezzi"),
                    reinserito=("si: " + patched[0]["name"]) if patched else "",
                    nome_wikipedia=wk.removed_name.iat[0] if len(wk) else "",
                    uscita_wikipedia=(wk.date.iat[0].date() if len(wk) else ""),
                    motivo_wikipedia=wk.reason.iat[0] if len(wk) else ""))
    return pd.DataFrame(rows)


def top3_status(p: Panel) -> pd.DataFrame:
    top3 = pd.read_csv(OUT / "top3_by_year.csv")
    top3 = top3[((top3["index"] == "SPX") & (top3.year >= 1996)) | ((top3["index"] == "NDX") & (top3.year >= 2007))]
    end = p.dates[-1]
    rows = []
    for r in top3.itertuples():
        j = p.lab_idx[r.label]
        last = p.dates[p.last_row[j]]
        alive = (end - last).days <= 7
        fate, src = FATE.get(r.label, ("", ""))
        exit_ = PATCH_EXIT.get(r.label, str(last.date()))
        exit_year = int(exit_[:4])
        rows.append(dict(indice=r.index, anno=r.year, pos=r.rank, ticker=r.label.replace("Y_", ""),
                         societa=company(r.label), rendimento_anno=r.total_return,
                         rendimento_anno_successivo=r.next_year_return, serie_ricostruita=r.label.startswith("PATCH_"),
                         quotata_oggi="si" if alive else "no",
                         uscita_dal_listino=("" if alive else exit_),
                         esito_societario=fate if not alive else "", fonte_esito=src if not alive else "",
                         sparita_entro_anno_successivo=("si" if (not alive and exit_year <= r.year + 1) else "no")))
    return pd.DataFrame(rows)


def verified_table() -> pd.DataFrame:
    src = {
        "PATCH_PCS-2000": "Sprint DEF 14A 2001 (tabella TSR); Sprint 10-K 2000 (min/max trimestrali)",
        "PATCH_NXTL-2000": "Nextel DEF 14A 2002 (TSR); Nextel 10-K 2000",
        "PATCH_RBK-2001": "S&P DJI, 50 migliori rendimenti a 1 anno 1980-2022 (prezzo); Reebok 10-K 2001/2002",
        "PATCH_DYN-2001": "Dynegy DEF 14A 2002 e 2005 (TSR S&P IMS); Dynegy 10-K 2001",
        "PATCH_PVN-2003": "Providian DEF 14A 2004/2005 (TSR); 10-K 2003",
        "PATCH_AV-2004": "Forbes 5-1-2004; S&P DJI; Avaya 10-K FY2004-05",
        "PATCH_DYN-2004": "Dynegy DEF 14A 2005 (TSR); 10-K 2004",
        "PATCH_TXU-2005": "TXU DEF 14A 2006 (TSR); 10-K 2005; CNN/Money",
        "PATCH_UST-2009": "CNN/Money 31-12-2008; 8-K Altria gen-2009",
    }
    caveat = {
        "PATCH_RBK-2001": "rendimento 2001 da verificare: intervallo -8,6% / -1,4% (usato -3,1%); stop non toccato",
        "PATCH_AV-2004": "rendimento 2004 ~+33% da verificare; stop non toccato",
        "PATCH_DYN-2001": "S&P DJI riporta +361% (prezzo non rettificato per il cambio 0,69 Illinova); usato +220,2% TSR",
    }
    rows = []
    for pt in patches.PATCHES:
        rows.append(dict(anno_classifica=pt["rank_year"], societa=pt["name"], ticker_sintetico=pt["label"],
                         rendimento_anno_classifica=pt["rank_tr"], anno_detenzione=pt["rank_year"] + 1,
                         rendimento_anno_detenzione=pt["hold_tr"],
                         stop_35_toccato=("si, il " + pt["stop_date"]) if pt["stop_date"] else "no",
                         fonti=src[pt["label"]], cautela=caveat.get(pt["label"], "")))
    return pd.DataFrame(rows)


def summary_by_year(p: Panel, miss: pd.DataFrame) -> pd.DataFrame:
    ye = year_end_rows(p)
    rows = []
    for index, y0 in (("SPX", 1996), ("NDX", 2007)):
        for y in range(y0, p.dates[-1].year + 1):
            d, d0 = ye[y], ye[y - 1]
            n_rank = len(ranking(p, index, d, d0, min_days=126))
            mm = miss[(miss.indice == index) & (miss.anno == y)]
            n_nodata = int((mm.motivo == "nessun prezzo nel dataset gratuito").sum()
                           + (mm.motivo == "ticker non risolto nei dati prezzi").sum())
            n_mem = n_rank + len(mm)
            rows.append(dict(indice=index, anno=y, membri_fine_anno=n_mem, classificati=n_rank,
                             non_classificati=len(mm), di_cui_senza_alcun_prezzo=n_nodata,
                             di_cui_ipo_recenti=int(mm.motivo.str.startswith("quotato da meno").sum()),
                             copertura=n_rank / n_mem if n_mem else np.nan,
                             reinseriti_da_fonti_SEC=", ".join(pt["name"] for pt in patches.PATCHES
                                                               if pt["rank_year"] == y and index == "SPX"),
                             verifica_top3=VERIFIED.get((index, y), ""), note=KNOWN_MISSING.get((index, y), "")))
    return pd.DataFrame(rows)


def main():
    p = patches.apply(Panel.load())
    p.quarantine = {"SNT-199910"}
    wiki = pd.read_csv(PROC / "wiki_sp500_changes.csv", parse_dates=["date"]).fillna("")
    st = top3_status(p)
    st.to_csv(OUT / "SP1_top3_stato.csv", index=False)
    miss = members_without_data(p, wiki)
    miss.to_csv(OUT / "SP2_membri_senza_dati.csv", index=False)
    ver = verified_table()
    ver.to_csv(OUT / "SP3_vincitori_reinseriti.csv", index=False)
    pd.DataFrame(STILL_MISSING).to_csv(OUT / "SP3b_ancora_mancanti.csv", index=False)
    sm = summary_by_year(p, miss)
    sm.to_csv(OUT / "SP4_riepilogo_anno.csv", index=False)
    gone = st[st.quotata_oggi == "no"]
    print("top-3 names no longer listed:", gone.ticker.nunique(), "of", st.ticker.nunique())
    print("disappeared within the next year:", (gone.sparita_entro_anno_successivo == "si").sum())
    print("worst next-year return:", st.rendimento_anno_successivo.min())
    print(sm[sm.indice == "SPX"][["anno", "membri_fine_anno", "classificati", "non_classificati", "di_cui_senza_alcun_prezzo", "copertura"]].to_string())
    print(miss.motivo.value_counts())
    print("wiki names found:", (miss.nome_wikipedia != "").sum(), "of", len(miss))


if __name__ == "__main__":
    main()
