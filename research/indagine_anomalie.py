"""
Phase 1.3-BIS: documentary investigation of three anomalies found in phase 1.3.

    python -m research.indagine_anomalie

1. adjusted prices rebuilt from the raw data vs the panel loaded by the original code;
2. the synthetic series of patches.py (origin of the values, construction, rankings, stops);
3. the four positions on which my first stop check found a stop date different from the code.

Reads the rebuilt data and the original modules in work/replica_originale (never modified)
and writes only outputs/tables/f13b_*.csv and logs/fase_1_3bis/. No backtest: no strategy is
recomputed; position- and year-level arithmetic is shown only where the authorisation asks for
it, and every alternative value is labelled as a documented scenario, not adopted.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from research import integrity

REPO = integrity.REPO
DEST = REPO / "work" / "replica_originale"
CODE = DEST / "code"
REPRO = DEST / "out"
TABLES = REPO / "outputs" / "tables"
LOGS = REPO / "logs" / "fase_1_3bis"
STOP = 0.35
FIELDS = ["open", "high", "low", "close", "adj_close"]
# ratios tried by panel._repair_adjustments()
RATIOS = np.array([1.25, 4 / 3, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 10, 15, 20, 1 / 2, 1 / 3, 1 / 4,
                   1 / 5, 1 / 8, 1 / 10, 1 / 15, 1 / 20, 1 / 25, 1 / 50, 1 / 100, 1 / 200])
RATIO_NAMES = ["x1.25", "x4/3", "x1.5", "x2", "x2.5", "x3", "x4", "x5", "x6", "x7", "x8", "x10", "x15", "x20",
               "x1/2", "x1/3", "x1/4", "x1/5", "x1/8", "x1/10", "x1/15", "x1/20", "x1/25", "x1/50", "x1/100", "x1/200"]
PLAUSIBLE = 0.15          # largest daily move accepted as an ordinary trading day by the repair-class heuristic
CONTESTED = [("DELL-201310", 1997), ("DELL-201310", 1998), ("EMC-201609", 1998), ("CTRA", 2011)]   # (label, rank year)

lines: list[str] = []


def say(msg: str = "") -> None:
    lines.append(msg)
    print(msg, flush=True)


def save(df: pd.DataFrame, name: str) -> None:
    df.to_csv(TABLES / name, index=False)
    say(f"  -> outputs/tables/{name} ({len(df)} rows)")


# ------------------------------------------------------------------ helpers (unit-tested)
def repair_choice(ra: float, rc: float, dy: float) -> tuple[float, str]:
    """The candidate panel._repair_adjustments() keeps: the smallest absolute value among the vendor's
    adjusted return, the price return + dividend yield and the price return corrected by each ratio."""
    cands = [(ra, "rendimento del fornitore"), (rc + dy, "prezzo + dividendo")]
    cands += [((1 + rc) * r - 1 + dy, f"prezzo corretto {n}") for r, n in zip(RATIOS, RATIO_NAMES)]
    return min(cands, key=lambda x: abs(x[0]) if np.isfinite(x[0]) else 9e9)


def repair_class(vendor: float, repaired: float, rc: float, dy: float, ratio: float) -> tuple[str, float | None]:
    """Heuristic class of a logged repair on a day with a REGISTERED split `ratio` (an estimate, not a proof).
    Two readings of the split day: close not adjusted for the split -> (1+rc)*ratio-1+dy; close already
    adjusted -> rc+dy. The plausible reading is the one with an ordinary move (|x| < 15%), the smaller if both."""
    if abs(repaired - vendor) < 0.005:
        return "variazione marginale (< 0,5 punti)", None
    reads = [x for x in ((1 + rc) * ratio - 1 + dy, rc + dy) if np.isfinite(x) and abs(x) < PLAUSIBLE]
    if not reads:
        return "non determinabile (nessuna lettura con movimento ordinario)", None
    truth = min(reads, key=abs)
    if abs(repaired - truth) < 0.005:
        return "riparazione coerente con il frazionamento registrato", truth
    if abs(vendor - truth) < 0.005:
        return "riparazione che sostituisce un rendimento coerente con il frazionamento registrato", truth
    return "non determinabile (nessuno dei due valori coincide)", truth


def day_category(split_ratio: float, src_prev: str, src: str, dy: float) -> str:
    if split_ratio not in (0, 1) and np.isfinite(split_ratio):
        return "frazionamento registrato"
    if src_prev != src:
        return "cambio di fonte"
    if dy > 0.05:
        return "dividendo anomalo (> 5% in un giorno)"
    return "altro"


# ------------------------------------------------------------------ loading
def load_original():
    sys.path.insert(0, str(CODE))
    import config
    assert Path(config.__file__).resolve().parent == CODE.resolve(), config.__file__
    import data_layer
    import patches
    from annual_study import price_index, stock_year
    from panel import Panel
    from signals import ranking, year_end_rows
    return config, data_layer, patches, Panel, ranking, year_end_rows, price_index, stock_year


def record_hashes(config, extra: list[Path]) -> None:
    files = [config.JB_PRICES, config.JB_MEMBERS, config.RAW / "MANIFEST.json", config.YAHOO_BATCH, config.PROC / "panel.npz",
             config.PROC / "labels.json", config.PROC / "spx_intervals.parquet", REPRO / "AN_top3_anno.csv",
             REPRO / "AN_rendimenti_annui.csv", integrity.PROTECTED / "results" / "AN_top3_anno.csv",
             integrity.PROTECTED / "results" / "GRMS_JanuaryBuy_Risultati.xlsx", integrity.PROTECTED / "code" / "patches.py"]
    files += [CODE / f for f in ("config.py", "data_layer.py", "panel.py", "patches.py", "signals.py", "annual_study.py")]
    files += extra
    out = [f"# SHA-256 of every file read by research/indagine_anomalie.py ({pd.Timestamp.now(tz='UTC'):%Y-%m-%dT%H:%M:%SZ})"]
    out += [f"{integrity.sha256_file(f)}  {f.relative_to(REPO)}  {f.stat().st_size} bytes" for f in files]
    (LOGS / "hash_file_utilizzati.txt").write_text("\n".join(out) + "\n")
    say(f"  hashes of {len(files)} input files -> logs/fase_1_3bis/hash_file_utilizzati.txt")


def pipeline_raw(data_layer, labels, dates):
    """The rows data_layer.build_panel() places in the arrays, with the counts of what it drops."""
    jb, y = data_layer.load_jb(), data_layer.load_yahoo()
    cal = data_layer.trading_calendar(y)
    assert cal.equals(dates)
    allp = pd.concat([jb, y], ignore_index=True)
    allp = allp[allp.ticker.isin(set(labels))]
    off = ~allp.date.isin(cal)
    before, after = allp.date < cal[0], allp.date > cal[-1]
    stats = dict(righe_titoli_del_pannello=len(allp), righe_fuori_calendario=int(off.sum()),
                 di_cui_prima_del_1988_01_04=int((off & before).sum()), di_cui_dopo_ultimo_giorno=int((off & after).sum()),
                 di_cui_giorni_di_borsa_chiusa=int((off & ~before & ~after).sum()),
                 dividendi_su_righe_fuori_calendario=int(((allp.dividends > 0) & off).sum()),
                 dividendi_scartati_dentro_il_periodo=int(((allp.dividends > 0) & off & ~before & ~after).sum()))
    allp = allp[~off]
    stats["righe_duplicate_scartate"] = int(allp.duplicated(["ticker", "date"]).sum())
    sub = allp.drop_duplicates(["ticker", "date"], keep="first")
    d_idx = pd.Series(np.arange(len(cal)), index=cal)
    lab_idx = {k: i for i, k in enumerate(labels)}
    ri, ci = d_idx.loc[sub.date].values, sub.ticker.map(lab_idx).values
    raw = {}
    for f in FIELDS:
        a = np.full((len(cal), len(labels)), np.nan)
        a[ri, ci] = sub[f].astype(float).values
        raw[f] = a
    cat = sub.src.astype("category")
    src = np.full((len(cal), len(labels)), -1, dtype=np.int16)
    src[ri, ci] = cat.cat.codes.values
    return raw, src, list(cat.cat.categories), stats


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    config, data_layer, patches, Panel, ranking, year_end_rows, price_index, stock_year = load_original()
    from research.controlli_f13 import simulate_fill
    say(f"indagine_anomalie: code and data from {DEST.relative_to(REPO)} (original modules, unmodified)")
    record_hashes(config, [Path(__file__).resolve(), REPO / "research" / "controlli_f13.py"])

    p = Panel.load()
    n0 = len(p.labels)
    labels = [str(x) for x in p.labels]
    dates = p.dates
    ye = year_end_rows(p)
    last = len(dates) - 1

    # ================================================================== 1. adjusted prices vs panel
    say("\n[1] Adjusted prices rebuilt from the raw data vs the panel")
    raw, src, names, stats = pipeline_raw(data_layer, labels, dates)
    say(f"  rows of panel labels: {stats['righe_titoli_del_pannello']}; dropped outside the ^GSPC calendar: "
        f"{stats['righe_fuori_calendario']} ({stats['di_cui_prima_del_1988_01_04']} before 1988-01-04, "
        f"{stats['di_cui_dopo_ultimo_giorno']} after the last day, {stats['di_cui_giorni_di_borsa_chiusa']} on exchange holidays); "
        f"with a dividend: {stats['dividendi_su_righe_fuori_calendario']}, of which inside the panel period: "
        f"{stats['dividendi_scartati_dentro_il_periodo']}; duplicates dropped: {stats['righe_duplicate_scartate']}")
    save(pd.DataFrame([stats]), "f13b_trasformazioni_pipeline.csv")
    sim, life, _ = simulate_fill(raw)
    A, C = sim["adj_close"], sim["close"]
    q = labels.index("SNT-199910")
    with np.errstate(invalid="ignore", divide="ignore"):
        ra = A[1:] / A[:-1] - 1
        rc = C[1:] / C[:-1] - 1
        dy = np.nan_to_num(np.where(p.div[1:, :n0] > 0, p.div[1:, :n0] / C[:-1], 0.0))
    gap = ra - rc - dy
    flag = np.abs(np.nan_to_num(gap)) > 0.15
    flag[:, q] = False
    jbs = pd.read_parquet(config.JB_PRICES, columns=["ticker", "date", "stock_splits"])
    ys = pd.read_parquet(config.YAHOO_BATCH, columns=["ticker", "date", "stock_splits"])
    ys["ticker"] = "Y_" + ys["ticker"]
    spl = pd.concat([jbs, ys], ignore_index=True)
    spl["date"] = pd.to_datetime(spl["date"])
    spl = spl[(spl.stock_splits.fillna(0) != 0) & (spl.stock_splits.fillna(1) != 1)]
    split_on = {(t, d): float(r) for t, d, r in zip(spl.ticker, spl.date, spl.stock_splits)}
    rep = p.repairs.copy()
    rep_map = {(r.label, r.date): (r.vendor_ret, r.repaired_ret) for r in rep.itertuples()}

    day_rows = []
    for i, j in zip(*np.where(flag)):
        t = i + 1
        lab, d = labels[j], dates[t]
        s0 = names[src[t - 1, j]] if src[t - 1, j] >= 0 else "riempito"
        s1 = names[src[t, j]] if src[t, j] >= 0 else "riempito"
        ratio = split_on.get((lab, d), 0.0)
        best, how = repair_choice(ra[i, j], rc[i, j], dy[i, j])
        logged = (lab, str(d.date())) in rep_map
        cls, truth = repair_class(ra[i, j], best, rc[i, j], dy[i, j], ratio) if logged and ratio else ("", None)
        day_rows.append(dict(label=lab, data=d.date(), fonte_giorno_prima=s0, fonte=s1, frazionamento_registrato=ratio,
                             categoria=day_category(ratio, s0, s1, dy[i, j]),
                             close_grezzo_prima=C[t - 1, j], close_grezzo=C[t, j], adj_grezzo_prima=A[t - 1, j],
                             adj_grezzo=A[t, j], adj_pannello_prima=p.a[t - 1, j], adj_pannello=p.a[t, j],
                             close_pannello=p.c[t, j], dividendo=p.div[t, j],
                             rend_rettificato_fornitore=ra[i, j], rend_close=rc[i, j], rend_dividendo=dy[i, j],
                             scarto_regola=gap[i, j], candidato_scelto=how, valore_scelto=best,
                             riparazione_registrata=logged, classe_riparazione_stimata=cls,
                             lettura_plausibile_stimata=truth))
    days = pd.DataFrame(day_rows)
    save(days, "f13b_giorni_segnalati.csv")
    say(f"  flagged days: {len(days)} on {days.label.nunique()} series; by category {days.categoria.value_counts().to_dict()}; "
        f"by source {days.fonte.value_counts().to_dict()}; logged repairs: {int(days.riparazione_registrata.sum())}")

    ser_rows = []
    for lab, g in days.groupby("label", sort=True):
        j = labels.index(lab)
        same = {f: bool(np.array_equal(sim[f][:, j], getattr(p, {"open": "o", "high": "h", "low": "l", "close": "c"}[f])[:, j],
                                       equal_nan=True)) for f in ("open", "high", "low", "close")}
        x, yv = A[:, j], p.a[:, j]
        ok = np.isfinite(x) & np.isfinite(yv)
        diff = np.abs(x[ok] - yv[ok])
        with np.errstate(invalid="ignore", divide="ignore"):
            rel = np.abs(x[ok] / yv[ok] - 1)
        ser_rows.append(dict(label=lab, fonte_prevalente=g.fonte.mode().iat[0], giorni_segnalati=len(g),
                             date_segnalate=";".join(str(v) for v in g.data), rapporti=";".join(f"{v:g}" for v in g.frazionamento_registrato),
                             riparazioni_registrate=int(g.riparazione_registrata.sum()),
                             open_high_low_close_identici=all(same.values()),
                             celle_adj_diverse=int((diff > 0).sum()), celle_adj_vita=int(ok.sum()),
                             max_diff_assoluta_adj=float(diff.max()), max_diff_relativa_adj=float(rel.max()),
                             causa=("riparazione registrata + ricostruzione" if g.riparazione_registrata.any()
                                    else "solo ricostruzione aritmetica (prodotto cumulato)")))
    ser = pd.DataFrame(ser_rows)
    save(ser, "f13b_serie_segnalate.csv")
    only = ser[ser.riparazioni_registrate == 0]
    say(f"  series without a logged repair: {len(only)}; open/high/low/close identical: {bool(only.open_high_low_close_identici.all())}; "
        f"adj cells differing: {int(only.celle_adj_diverse.sum())} of {int(only.celle_adj_vita.sum())}; "
        f"max relative difference {only.max_diff_relativa_adj.max():.2e}, max absolute {only.max_diff_assoluta_adj.max():.2e}")

    # source changes inside a series (not flagged by the rule)
    sc = []
    for j in range(n0):
        if j == q:
            continue
        s = src[:, j]
        t = np.where((s[1:] >= 0) & (s[:-1] >= 0) & (s[1:] != s[:-1]))[0] + 1
        for tt in t:
            sc.append(dict(label=labels[j], data=dates[tt].date(), da=names[s[tt - 1]], a=names[s[tt]],
                           rend_rettificato=float(ra[tt - 1, j]), rend_close=float(rc[tt - 1, j]),
                           scarto_regola=float(gap[tt - 1, j]) if np.isfinite(gap[tt - 1, j]) else np.nan))
    sc = pd.DataFrame(sc, columns=["label", "data", "da", "a", "rend_rettificato", "rend_close", "scarto_regola"])
    save(sc, "f13b_cambi_di_fonte.csv")
    say(f"  days on which a series changes source: {len(sc)}; max |gap| on those days "
        f"{sc.scarto_regola.abs().max() if len(sc) else float('nan'):.4f}; max |adjusted return| "
        f"{sc.rend_rettificato.abs().max() if len(sc) else float('nan'):.4f}; days with |adjusted return| > 10%: "
        f"{int((sc.rend_rettificato.abs() > 0.10).sum())}")

    # the 30 logged repairs
    rr = days[days.riparazione_registrata].copy()
    rr["rend_riparato_codice"] = [rep_map[(r.label, str(r.data))][1] for r in rr.itertuples()]
    rr["coincide_con_log_storico"] = np.isclose(rr.rend_riparato_codice, rr.valore_scelto, rtol=0, atol=1e-15)
    rr["effetto_sul_livello_successivo"] = (1 + rr.valore_scelto) / (1 + rr.rend_rettificato_fornitore) - 1
    # ranking impact: is the repaired day inside a ranking window, and would the vendor value change the top-3?
    patches.apply(p)
    imp = []
    for r in rr.itertuples():
        t = int(dates.searchsorted(pd.Timestamp(r.data)))
        for yv in range(1996, 2026):
            d, d0 = ye[yv], ye[yv - 1]
            if not (d0 < t <= d):
                continue
            rk = ranking(p, "SPX", d, d0, min_days=126)
            rk = rk[[int(p.last_row[c]) > d for c in rk.col]].reset_index(drop=True)
            hit = rk[rk.label == r.label]
            third = float(rk.mom.iloc[2])
            if len(hit) == 0:
                imp.append(dict(label=r.label, data=r.data, anno_classifica=yv, classificato=False))
                continue
            mom = float(hit.mom.iat[0])
            pos_now = int(hit.index[0]) + 1
            mom_v = (1 + mom) * (1 + r.rend_rettificato_fornitore) / (1 + r.valore_scelto) - 1
            others = rk[rk.label != r.label].mom.values
            pos_v = int((others > mom_v).sum()) + 1
            imp.append(dict(label=r.label, data=r.data, anno_classifica=yv, classificato=True, posizione_con_riparazione=pos_now,
                            rend_anno_con_riparazione=mom, rend_anno_con_valore_fornitore=mom_v, posizione_con_valore_fornitore=pos_v,
                            rend_terzo_classificato=third, top3_cambierebbe=bool(pos_now <= 3 or pos_v <= 3)))
    imp = pd.DataFrame(imp)
    for c in ("anno_classifica", "posizione_con_riparazione", "posizione_con_valore_fornitore"):
        imp[c] = imp[c].astype("Int64")
    rr = rr.merge(imp, how="left", left_on=["label", "data"], right_on=["label", "data"])
    save(rr[["label", "data", "fonte", "frazionamento_registrato", "rend_close", "rend_dividendo", "rend_rettificato_fornitore",
             "valore_scelto", "candidato_scelto", "rend_riparato_codice", "coincide_con_log_storico", "classe_riparazione_stimata",
             "lettura_plausibile_stimata", "effetto_sul_livello_successivo", "anno_classifica", "classificato",
             "posizione_con_riparazione", "posizione_con_valore_fornitore", "rend_anno_con_riparazione",
             "rend_anno_con_valore_fornitore", "rend_terzo_classificato", "top3_cambierebbe"]], "f13b_riparazioni.csv")
    say(f"  logged repairs reproduced by the rule: {int(rr.coincide_con_log_storico.sum())}/{len(rr)}; estimated classes "
        f"{rr.classe_riparazione_stimata.value_counts().to_dict()}")
    inwin = rr[rr.classificato.fillna(False).astype(bool)]
    say(f"  repairs inside the ranking year of a ranked S&P 500 member: {len(inwin)}; best position with the repair "
        f"{int(inwin.posizione_con_riparazione.min()) if len(inwin) else '-'}, with the vendor value "
        f"{int(inwin.posizione_con_valore_fornitore.min()) if len(inwin) else '-'}; top-3 would change: "
        f"{int(inwin.top3_cambierebbe.sum()) if len(inwin) else 0}")
    for r in inwin.sort_values("posizione_con_valore_fornitore").head(6).itertuples():
        say(f"    {r.anno_classifica} {r.label} ({r.data}): position {r.posizione_con_riparazione} with the repair "
            f"({r.rend_anno_con_riparazione:+.1%}), {r.posizione_con_valore_fornitore} with the vendor value "
            f"({r.rend_anno_con_valore_fornitore:+.1%}); 3rd place {r.rend_terzo_classificato:+.1%}; class: {r.classe_riparazione_stimata}")

    # ================================================================== 2. synthetic series
    say("\n[2] Synthetic series (patches.py)")
    doc = [ln for ln in patches.__doc__.splitlines() if ln.startswith("| 19") or ln.startswith("| 20")]
    assert len(doc) == len(patches.PATCHES)
    t3 = pd.read_csv(REPRO / "AN_top3_anno.csv")
    spx0 = pd.read_parquet(config.PROC / "spx_intervals.parquet")
    syn, neigh = [], []
    for pt, ln in zip(patches.PATCHES, doc):
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        assert int(cells[0]) == pt["rank_year"], (cells, pt["label"])
        j = p.lab_idx[pt["label"]]
        r0, r1, r2 = int(ye[pt["rank_year"] - 1]), int(ye[pt["rank_year"]]), int(ye[pt["rank_year"] + 1])
        if pt["end_date"]:
            r2 = int(dates.searchsorted(pd.Timestamp(pt["end_date"])))
        base = 1 + pt["rank_tr"]
        entry = p.o[r1 + 1, j]
        lvl = entry * (1 - STOP)
        rec = dict(label=pt["label"], societa=pt["name"], anno_classifica=pt["rank_year"],
                   doc_rend_classifica=cells[2], doc_rend_detenzione=cells[4], doc_stop=cells[5], doc_fonti=cells[6],
                   codice_rank_tr=pt["rank_tr"], codice_hold_tr=pt["hold_tr"], codice_stop_date=pt["stop_date"] or "",
                   codice_member_from=pt["member_from"], codice_end_date=pt["end_date"] or "",
                   prezzo_fine_anno_classifica_su_base=p.a[r1, j] / base, ingresso_uguale_chiusura_precedente=bool(entry == p.a[r1, j]),
                   high_low_close_uguali_adj=bool(np.array_equal(p.h[:, j], p.a[:, j], equal_nan=True)
                                                   and np.array_equal(p.l[:, j], p.a[:, j], equal_nan=True)),
                   dividendi_totali=float(p.div[:, j].sum()))
        hits = np.where(p.al[r1 + 1:r2 + 1, j] <= lvl)[0]
        rec["data_stop_calcolata"] = str(dates[r1 + 1 + hits[0]].date()) if len(hits) else ""
        if pt["stop_date"]:
            sd = int(dates.searchsorted(pd.Timestamp(pt["stop_date"])))
            rec["stop_date_giorno_di_borsa"] = bool(dates[sd] == pd.Timestamp(pt["stop_date"]))
            rec["a_giorno_stop_su_base_x_065"] = p.a[sd, j] / (base * (1 - STOP))
            rec["riga_0_9999_attiva"] = bool(np.isclose(p.a[sd, j] / (base * (1 - STOP)), 0.9999, rtol=0, atol=1e-12))
            rec["a_giorno_stop_su_livello_meno_1"] = p.a[sd, j] / lvl - 1
            rec["apertura_giorno_stop_su_livello_meno_1"] = p.o[sd, j] / lvl - 1
            rec["stop_scatterebbe_senza_fattore_1_0001"] = bool(p.a[sd, j] <= base * (1 - STOP))
        m = spx0[spx0.ticker.str.split("-").str[0] == pt["label"].split("_")[1].split("-")[0]]
        dt_ = dates[r1]
        m = m[(m.start <= dt_) & (m.end.isna() | (m.end > dt_))]
        rec["ticker_nel_file_composizione"] = ";".join(m.ticker)
        rec["inizio_nel_file_composizione"] = ";".join(str(x.date()) for x in m.start)
        rec["member_from_uguale_al_file"] = bool(len(m) and str(m.start.iat[0].date()) == pt["member_from"])
        rec["ticker_originale_con_prezzi"] = bool(len(m) and m.ticker.iat[0] in p.lab_idx)
        pos = t3[t3.label == pt["label"]]
        rec["posizione_top3"] = int(pos.posizione.iat[0]) if len(pos) else None
        # neighbours in the ranking of the rank year, as annual_study.py ranks it
        d, d0 = ye[pt["rank_year"]], ye[pt["rank_year"] - 1]
        rk = ranking(p, "SPX", d, d0, min_days=126)
        rk = rk[[int(p.last_row[c]) > d for c in rk.col]].reset_index(drop=True)
        k = int(rk.index[rk.label == pt["label"]][0])
        above = rk.mom.iat[k - 1] if k > 0 else np.nan
        below = rk.mom.iat[k + 1]
        rec["margine_su_chi_segue"] = (1 + rk.mom.iat[k]) / (1 + below) - 1
        rec["margine_da_chi_precede"] = (1 + above) / (1 + rk.mom.iat[k]) - 1 if k > 0 else np.nan
        rec["rend_quarto_classificato"] = float(rk.mom.iat[3])
        rec["quarto_classificato"] = rk.label.iat[3]
        rec["ordine_invariato_senza_1_0001"] = bool((k == 0 or pt["rank_tr"] < above) and pt["rank_tr"] > below)
        syn.append(rec)
        for kk in range(min(6, len(rk))):
            neigh.append(dict(anno_classifica=pt["rank_year"], posizione=kk + 1, label=rk.label.iat[kk],
                              sintetica=rk.label.iat[kk].startswith("PATCH_"), rend_anno=float(rk.mom.iat[kk]),
                              parziale=bool(rk.partial.iat[kk])))
    syn = pd.DataFrame(syn)
    save(syn, "f13b_serie_sintetiche_dettaglio.csv")
    save(pd.DataFrame(neigh).drop_duplicates(["anno_classifica", "posizione"]), "f13b_sintetiche_classifiche.csv")
    st = syn[syn.codice_stop_date != ""]
    say(f"  rank-year-end value / documented base: {sorted(set(syn.prezzo_fine_anno_classifica_su_base.round(6)))}; "
        f"the 0.9999 line is active in {int(st.riga_0_9999_attiva.sum())}/{len(st)} stopped series; price on the stop day "
        f"vs level: {st.a_giorno_stop_su_livello_meno_1.round(6).tolist()}; would trigger without the 1.0001 factor "
        f"(equality): {st.stop_scatterebbe_senza_fattore_1_0001.tolist()}")
    say(f"  member_from equal to the membership file: {int(syn.member_from_uguale_al_file.sum())}/{len(syn)} "
        f"(different: {syn[~syn.member_from_uguale_al_file][['label', 'codice_member_from', 'inizio_nel_file_composizione']].values.tolist()}); "
        f"original ticker with prices: {int(syn.ticker_originale_con_prezzi.sum())}; ranking order unchanged without 1.0001: "
        f"{bool(syn.ordine_invariato_senza_1_0001.all())}; dividends: {syn.dividendi_totali.sum()}")
    for r in syn.itertuples():
        say(f"    {r.label}: top-3 position {r.posizione_top3}; margin over the next {r.margine_su_chi_segue:+.2%}"
            + (f", from the previous {r.margine_da_chi_precede:+.2%}" if np.isfinite(r.margine_da_chi_precede) else "")
            + f"; 4th place {r.quarto_classificato} {r.rend_quarto_classificato:+.1%}")

    # documented alternatives: position- and year-level arithmetic only, not adopted
    ann = pd.read_csv(REPRO / "AN_rendimenti_annui.csv").set_index("anno")
    sc_rows = []

    def scen(name, source, year, pos, alt_nostop, alt_stop, cur_nostop, cur_stop, top3_changes, note,
             kind="alternativa documentata in patches.py"):
        y = ann.loc[year]
        top1 = pos == 1
        sc_rows.append(dict(tipo=kind, scenario=name, fonte=source, anno_detenzione=year, posizione=pos,
                            rend_posizione_attuale_senza_stop=cur_nostop, rend_posizione_alternativo_senza_stop=alt_nostop,
                            rend_posizione_attuale_con_stop=cur_stop, rend_posizione_alternativo_con_stop=alt_stop,
                            delta_vincitore_senza_stop=(alt_nostop - cur_nostop) if top1 else 0.0,
                            delta_vincitore_con_stop=(alt_stop - cur_stop) if top1 else 0.0,
                            delta_prime_tre_senza_stop=0.0 if not top3_changes else (alt_nostop - cur_nostop) / 3,
                            delta_prime_tre_con_stop=0.0 if not top3_changes else (alt_stop - cur_stop) / 3,
                            vincitore_senza_stop_attuale=y.top1_senza_stop, vincitore_con_stop_attuale=y.top1_con_stop,
                            prime_tre_senza_stop_attuale=y.top3_senza_stop, prime_tre_con_stop_attuale=y.top3_con_stop, nota=note))

    rbk = t3[t3.label == "PATCH_RBK-2001"].iloc[0]
    dyn = t3[t3.label == "PATCH_DYN-2001"].iloc[0]
    scen("Dynegy 2000 = +361% (S&P DJI) invece di +220,2% (TSR del proxy)", "patches.py, nota di riconciliazione Dynegy 2000",
         2001, 1, dyn.rend_T1_senza_stop, dyn.rend_T1_con_stop, rbk.rend_T1_senza_stop, rbk.rend_T1_con_stop, False,
         "Dynegy diventerebbe 1a al posto di Reebok; le prime tre restano Reebok, Dynegy, EOG (stessi titoli, cambia l'ordine)")
    for v, lab in ((-0.086, "estremo basso"), (-0.014, "estremo alto")):
        scen(f"Reebok 2001 = {v:+.1%} ({lab} dell'intervallo da verificare)", "patches.py: [TO VERIFY: -8.6%..-1.4%]",
             2001, 1, v, v, rbk.rend_T1_senza_stop, rbk.rend_T1_con_stop, True, "nessuno stop in entrambi i casi (minimo documentato 18,50)")
    scen("Reebok 2001 con stop toccato (apertura del 2-1-2001 >= 18,50 / 0,65 = 28,46)",
         "patches.py: 'not hit (low 18.50 vs ~17.8)'; soglia ricavata aritmeticamente", 2001, 1,
         rbk.rend_T1_senza_stop, -STOP, rbk.rend_T1_senza_stop, rbk.rend_T1_con_stop, True,
         "il margine documentato tra minimo e livello e' +3,9%; l'apertura effettiva non e' nel progetto")
    # thinnest margin that decides a top-3 membership: Dynegy 2003 (3rd, proxy TSR) vs PMC-Sierra (4th, price data).
    # PMC-Sierra's 2004 outcome is computed with the original annual_study.stock_year(): a sensitivity estimate.
    dyn04 = t3[t3.label == "PATCH_DYN-2004"].iloc[0]
    sy = stock_year(p, p.lab_idx["PMCS-201601"], ye[2003], ye[2004])
    scen("PMC-Sierra 3a nel 2003 al posto di Dynegy (margine 0,30% sul rendimento 2003)",
         "margine misurato in f13b_serie_sintetiche_dettaglio.csv; esito PMC-Sierra 2004 da annual_study.stock_year()",
         2004, 3, sy["ret"], sy["ret_stop"], dyn04.rend_T1_senza_stop, dyn04.rend_T1_con_stop, True,
         f"PMC-Sierra 2004: stop {'toccato il ' + str(sy['stop_date']) if sy['stop_date'] else 'non toccato'}",
         kind="stima di sensibilita' (non documentale)")
    sce = pd.DataFrame(sc_rows)
    save(sce, "f13b_sintetiche_scenari_documentali.csv")
    for r in sce.itertuples():
        say(f"    scenario '{r.scenario}': winner {r.delta_vincitore_senza_stop:+.1%} (no stop) / {r.delta_vincitore_con_stop:+.1%} "
            f"(stop); top-3 {r.delta_prime_tre_senza_stop:+.2%} / {r.delta_prime_tre_con_stop:+.2%} in {r.anno_detenzione}")

    # ================================================================== 3. the four contested positions
    say("\n[3] The four positions with a different stop date in my first check")
    summ, daily = [], []
    for lab, ry in CONTESTED:
        j = p.lab_idx[lab]
        d = ye[ry]
        s, e = d + 1, min(ye[ry + 1], int(p.last_row[j]))
        row = t3[(t3.label == lab) & (t3.anno_T0 == ry)].iloc[0]
        entry_adj = p.ao[s, j] if np.isfinite(p.ao[s, j]) else p.a[s, j]
        lvl_adj = entry_adj * (1 - STOP)
        lvl_raw = p.o[s, j] * (1 - STOP)                       # my first check: raw open, raw lows (not split-consistent)
        hit_raw = np.where(p.l[s:e + 1, j] <= lvl_raw)[0]
        t = s + int(hit_raw[0])
        gap_raw = bool(p.o[t, j] <= lvl_raw and t != s)
        fill_raw = p.o[t, j] if gap_raw else lvl_raw
        G = p.a[:, j] / price_index(p, j)                      # corrected check: price basis without dividends
        lvl_g = lvl_adj * G[s:e + 1] / G[s]
        hit_g = np.where(p.al[s:e + 1, j] <= lvl_g)[0]
        hit_c = np.where(p.al[s:e + 1, j] <= lvl_adj)[0]       # the original code
        sp = spl[(spl.ticker == lab) & (spl.date > dates[s]) & (spl.date <= dates[e])]
        cum = float(np.prod(sp[sp.date <= dates[t]].stock_splits.values)) if len(sp) else 1.0
        # the raw lows can be brought back to the entry basis with the split factors only if the close of this
        # source is NOT split-adjusted, i.e. it drops by about 1/ratio on each split day
        close_jumps = []
        for x in sp.itertuples():
            tt = int(dates.searchsorted(x.date))
            close_jumps.append(f"{x.date.date()}: close {p.c[tt, j] / p.c[tt - 1, j] - 1:+.1%} (attesa {1 / x.stock_splits - 1:+.1%})")
        ratio_al = p.al[s:e + 1, j] / lvl_adj
        kmin = int(np.nanargmin(ratio_al))
        code_ret = float(row.rend_T1_con_stop)
        flawed_ret = fill_raw / p.o[s, j] - 1
        corr_ret = float(p.a[e, j] / entry_adj - 1) if not len(hit_g) else float("nan")
        yr = ann.loc[ry + 1]
        summ.append(dict(label=lab, societa=row.societa, anno_detenzione=ry + 1, posizione=int(row.posizione),
                         data_ingresso=dates[s].date(), apertura_ingresso_grezza=p.o[s, j], ingresso_rettificato=entry_adj,
                         livello_stop_rettificato=lvl_adj, livello_stop_grezzo_base_ingresso=lvl_raw,
                         frazionamenti_in_detenzione=";".join(f"{x.date.date()} x{x.stock_splits:g}" for x in sp.itertuples()),
                         close_nei_giorni_di_frazionamento="; ".join(close_jumps),
                         fonte_dati=names[np.bincount(src[s:e + 1, j][src[s:e + 1, j] >= 0]).argmax()],
                         dividendi_in_detenzione=int((p.div[s:e + 1, j] > 0).sum()),
                         rend_dividendi_in_detenzione=float(G[e] / G[s] - 1),
                         data_contestata=dates[t].date(), open_grezzo=p.o[t, j], high_grezzo=p.h[t, j], low_grezzo=p.l[t, j],
                         close_grezzo=p.c[t, j], open_rett=p.ao[t, j], high_rett=p.ah[t, j], low_rett=p.al[t, j], close_rett=p.a[t, j],
                         fattore_frazionamenti_ingresso_data=cum, low_grezzo_x_fattore=p.l[t, j] * cum,
                         low_coerente_su_livello=p.l[t, j] * cum / lvl_raw - 1, low_rett_su_livello_rett=p.al[t, j] / lvl_adj - 1,
                         minimo_anno_su_livello_rett=float(ratio_al[kmin] - 1), data_minimo_anno=dates[s + kmin].date(),
                         codice_data_uscita=dates[e].date() if not len(hit_c) else dates[s + hit_c[0]].date(),
                         codice_prezzo_uscita_rett=float(row.prezzo_uscita_rett), codice_rend=code_ret,
                         controllo_errato_data_uscita=dates[t].date(), controllo_errato_prezzo_uscita_grezzo=fill_raw,
                         controllo_errato_apertura_sotto=gap_raw, controllo_errato_rend_artefatto=flawed_ret,
                         controllo_corretto_data_uscita=dates[e].date() if not len(hit_g) else dates[s + hit_g[0]].date(),
                         controllo_corretto_prezzo_uscita_rett=float(p.a[e, j]) if not len(hit_g) else float("nan"),
                         controllo_corretto_rend=corr_ret,
                         diff_posizione_corretto_meno_codice=corr_ret - code_ret,
                         diff_posizione_errato_meno_codice=flawed_ret - code_ret,
                         strategia_vincitore_con_stop_anno=float(yr.top1_con_stop), strategia_prime_tre_con_stop_anno=float(yr.top3_con_stop),
                         diff_strategia_corretto=0.0 if abs(corr_ret - code_ret) < 1e-15 else (corr_ret - code_ret) / (1 if row.posizione == 1 else 3),
                         diff_vincitore_errato=(flawed_ret - code_ret) if row.posizione == 1 else 0.0,
                         diff_prime_tre_errato=(flawed_ret - code_ret) / 3))
        for k in range(s - 1, e + 1):
            cumk = float(np.prod(sp[sp.date <= dates[k]].stock_splits.values)) if len(sp) else 1.0
            daily.append(dict(label=lab, anno_detenzione=ry + 1, data=dates[k].date(), giorno="ingresso" if k == s else
                              ("data contestata" if k == t else ("uscita" if k == e else "")),
                              open=p.o[k, j], high=p.h[k, j], low=p.l[k, j], close=p.c[k, j], open_rett=p.ao[k, j], low_rett=p.al[k, j],
                              close_rett=p.a[k, j], dividendo=p.div[k, j], frazionamento=split_on.get((lab, dates[k]), 0.0),
                              fonte=names[src[k, j]] if src[k, j] >= 0 else "riempito",
                              livello_stop_rett=lvl_adj, low_rett_su_livello=p.al[k, j] / lvl_adj,
                              livello_grezzo_controllo_errato=lvl_raw, low_grezzo_su_livello_grezzo=p.l[k, j] / lvl_raw,
                              fattore_frazionamenti_cumulato=cumk, low_coerente_su_livello_grezzo=p.l[k, j] * cumk / lvl_raw))
    summ = pd.DataFrame(summ)
    save(summ, "f13b_quattro_posizioni.csv")
    save(pd.DataFrame(daily), "f13b_quattro_posizioni_giornaliero.csv")
    for r in summ.itertuples():
        say(f"  {r.anno_detenzione} {r.label} (pos {r.posizione}): entry {r.data_ingresso} raw {r.apertura_ingresso_grezza:.4f} adj "
            f"{r.ingresso_rettificato:.4f}, level adj {r.livello_stop_rettificato:.4f}; splits [{r.frazionamenti_in_detenzione}]; "
            f"contested {r.data_contestata}: raw low {r.low_grezzo:.4f} vs raw level {r.livello_stop_grezzo_base_ingresso:.4f}, "
            f"split factor {r.fattore_frazionamenti_ingresso_data:g} -> consistent low {r.low_coerente_su_livello:+.1%} vs level, "
            f"adjusted low {r.low_rett_su_livello_rett:+.1%} vs adjusted level; year minimum {r.minimo_anno_su_livello_rett:+.1%} "
            f"({r.data_minimo_anno}); code exit {r.codice_data_uscita} ret {r.codice_rend:+.2%}; corrected check exit "
            f"{r.controllo_corretto_data_uscita} ret {r.controllo_corretto_rend:+.2%}; first check (artefact) {r.controllo_errato_data_uscita} "
            f"ret {r.controllo_errato_rend_artefatto:+.2%}")

    (LOGS / "indagine_anomalie.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
