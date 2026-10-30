"""
Phase 1.3: compare the outputs reproduced in work/replica_originale/out with the
original results in source_original/results (read-only), file by file and cell by cell.

    python -m research.confronto_baseline

Writes outputs/tables/f13_confronto_file.csv, f13_confronto_colonne.csv,
f13_discrepanze.csv and f13_confronto_json.csv.

Cell classes: "identico" (same text in the CSV, or both empty), "entro_tolleranza"
(numbers differing by at most 1e-12 relative), "diverso" (anything else). Every
non-identical cell is listed in f13_discrepanze.csv.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from research import integrity

REPO = integrity.REPO
ORIG = integrity.PROTECTED / "results"
REPRO = REPO / "work" / "replica_originale" / "out"
TABLES = REPO / "outputs" / "tables"
REL_TOL = 1e-12

ZAINETTI = sorted(p.name for p in ORIG.glob("AN_zainetto_*.csv"))
CSV_KEYS = {"AN_top3_anno.csv": ["anno_T0", "posizione"],
            "AN_rendimenti_annui.csv": ["anno"],
            "AN_sintesi.csv": ["periodo", "strategia", "vista"],
            "AN_finestre_10anni.csv": ["inizio", "fine"],
            **{z: ["anno"] for z in ZAINETTI}}
JSON_FILES = ["AN_parametri.json", "report_annuale_tables.json"]

# which item of the phase 1.3 checklist each column documents
TOP3_THEMES = {"ticker": "titoli selezionati", "label": "titoli selezionati", "societa": "titoli selezionati",
               "serie_ricostruita": "titoli selezionati", "rend_T0": "titoli selezionati", "parziale_T0": "titoli selezionati",
               "anno_detenzione": "titoli selezionati",
               "rend_T1_senza_stop": "rendimenti delle tre posizioni", "rend_T1_con_stop": "rendimenti delle tre posizioni",
               "stop_toccato": "date e livelli di stop", "data_stop": "date e livelli di stop", "stop_in_gap": "date e livelli di stop",
               "prezzo_ingresso_rett": "prezzi di ingresso e uscita", "prezzo_uscita_rett": "prezzi di ingresso e uscita",
               "dividendi_T1": "dividendi", "dividendi_T1_con_stop": "dividendi",
               "uscita_dal_listino_nell_anno": "titoli delistati", "ultimo_prezzo": "titoli delistati"}
SINTESI_THEMES = {"valore_finale": "rendimento cumulato e CAGR", "cagr": "rendimento cumulato e CAGR",
                  "imposte_pagate": "costi e fiscalita", "minus_scadute": "costi e fiscalita"}


def theme(file: str, col: str, vista: str | None = None) -> str:
    if file == "AN_top3_anno.csv":
        return TOP3_THEMES.get(col, "altro")
    if file == "AN_rendimenti_annui.csv":
        if col.startswith("SP500"):
            return "benchmark (rendimenti annuali)"
        if col.startswith("div_"):
            return "dividendi"
        if col == "titoli_fermati_top3":
            return "date e livelli di stop"
        if col.startswith("leaps"):
            return "LEAPS (rendimenti annuali)"
        return "rendimenti annuali delle strategie (lordo)"
    if file == "AN_sintesi.csv":
        base = SINTESI_THEMES.get(col, "metriche di rischio")
        return base + ("" if vista in (None, "Lordo") else f" - vista {vista} (con costi e fiscalita)")
    if file == "AN_finestre_10anni.csv":
        return "finestre decennali (lordo e nettista)"
    return "costi e fiscalita (registro dello zainetto)"


def _num(s: str):
    try:
        x = float(s)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def classify(a: str, b: str) -> tuple[str, float | None, float | None]:
    if a == b:
        return "identico", 0.0 if _num(a) is not None else None, 0.0 if _num(a) is not None else None
    x, y = _num(a), _num(b)
    if x is None or y is None:
        return "diverso", None, None
    d = abs(x - y)
    r = d / max(abs(x), abs(y), 1e-300)
    return ("entro_tolleranza" if r <= REL_TOL else "diverso"), d, r


def compare_csv(name: str, keys: list[str]):
    o = pd.read_csv(ORIG / name, dtype=str, keep_default_na=False)
    r = pd.read_csv(REPRO / name, dtype=str, keep_default_na=False)
    m = o.merge(r, on=keys, how="outer", suffixes=("__o", "__r"), indicator=True)
    only_o, only_r = int((m._merge == "left_only").sum()), int((m._merge == "right_only").sum())
    both = m[m._merge == "both"]
    cols = [c for c in o.columns if c not in keys and c in r.columns]
    per_col, disc = [], []
    vista = both["vista"] if "vista" in both.columns else None
    for c in cols:
        groups = [(None, both)] if vista is None else list(both.groupby("vista", sort=False))
        for v, g in groups:
            res = [classify(a, b) for a, b in zip(g[c + "__o"], g[c + "__r"])]
            n = len(res)
            cnt = {k: sum(1 for x in res if x[0] == k) for k in ("identico", "entro_tolleranza", "diverso")}
            diffs = [x[1] for x in res if x[1] is not None]
            rels = [x[2] for x in res if x[2] is not None]
            per_col.append(dict(file=name, colonna=c, vista=v or "", tema=theme(name, c, v), celle=n, **cnt,
                                max_diff_assoluta=max(diffs) if diffs else "", max_diff_relativa=max(rels) if rels else ""))
            for (_, row), (cls, d, rel) in zip(g.iterrows(), res):
                if cls != "identico":
                    disc.append(dict(file=name, chiave="|".join(str(row[k]) for k in keys), colonna=c,
                                     originale=row[c + "__o"], riprodotto=row[c + "__r"], classe=cls,
                                     diff_assoluta=d, diff_relativa=rel))
    pc = pd.DataFrame(per_col)
    summary = dict(file=name, righe_originale=len(o), righe_riprodotto=len(r), colonne_originale=len(o.columns),
                   colonne_riprodotto=len(r.columns), stesse_colonne_stesso_ordine=list(o.columns) == list(r.columns),
                   chiavi_solo_originale=only_o, chiavi_solo_riprodotto=only_r, celle_confrontate=int(pc.celle.sum()),
                   identiche=int(pc.identico.sum()), entro_tolleranza=int(pc.entro_tolleranza.sum()), diverse=int(pc.diverso.sum()))
    return summary, pc, disc


def compare_json(name: str):
    o = json.load(open(ORIG / name, encoding="utf-8"))
    r = json.load(open(REPRO / name, encoding="utf-8"))
    rows, disc = [], []
    for k in sorted(set(o) | set(r)):
        if k not in o or k not in r:
            rows.append(dict(file=name, chiave=k, esito="chiave presente solo in " + ("riprodotto" if k in r else "originale")))
            continue
        cls, d, rel = classify(str(o[k]), str(r[k]))
        rows.append(dict(file=name, chiave=k, esito=cls))
        if cls != "identico":
            disc.append(dict(file=name, chiave=k, colonna="(valore)", originale=o[k], riprodotto=r[k], classe=cls,
                             diff_assoluta=d, diff_relativa=rel))
    n = len(rows)
    ident = sum(1 for x in rows if x["esito"] == "identico")
    summary = dict(file=name, righe_originale=len(o), righe_riprodotto=len(r), colonne_originale="", colonne_riprodotto="",
                   stesse_colonne_stesso_ordine=list(o) == list(r), chiavi_solo_originale=len(set(o) - set(r)),
                   chiavi_solo_riprodotto=len(set(r) - set(o)), celle_confrontate=n, identiche=ident,
                   entro_tolleranza=sum(1 for x in rows if x["esito"] == "entro_tolleranza"),
                   diverse=n - ident - sum(1 for x in rows if x["esito"] == "entro_tolleranza"))
    return summary, rows, disc


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    files, cols, discs, jrows = [], [], [], []
    for name, keys in CSV_KEYS.items():
        s, pc, d = compare_csv(name, keys)
        files.append(s), cols.append(pc), discs.extend(d)
    for name in JSON_FILES:
        s, rows, d = compare_json(name)
        files.append(s), jrows.extend(rows), discs.extend(d)
    for s in files:
        a, b = ORIG / s["file"], REPRO / s["file"]
        s["sha256_originale"], s["sha256_riprodotto"] = integrity.sha256_file(a), integrity.sha256_file(b)
        s["byte_identici"] = s["sha256_originale"] == s["sha256_riprodotto"]
    f = pd.DataFrame(files)
    f.to_csv(TABLES / "f13_confronto_file.csv", index=False)
    pd.concat(cols, ignore_index=True).to_csv(TABLES / "f13_confronto_colonne.csv", index=False)
    pd.DataFrame(discs, columns=["file", "chiave", "colonna", "originale", "riprodotto", "classe", "diff_assoluta",
                                 "diff_relativa"]).to_csv(TABLES / "f13_discrepanze.csv", index=False)
    pd.DataFrame(jrows).to_csv(TABLES / "f13_confronto_json.csv", index=False)
    print(f[["file", "righe_originale", "celle_confrontate", "identiche", "entro_tolleranza", "diverse", "byte_identici"]]
          .to_string(index=False))
    print(f"total cells/keys compared: {int(f.celle_confrontate.sum())}, different: {int(f.diverse.sum())}, "
          f"within tolerance: {int(f.entro_tolleranza.sum())}, files byte-identical: {int(f.byte_identici.sum())}/{len(f)}")


if __name__ == "__main__":
    main()
