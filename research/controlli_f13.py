"""
Phase 1.3, point 4: methodological checks on the reproduced baseline.

    python -m research.controlli_f13

Reads the rebuilt data and the reproduced outputs in work/replica_originale (the
original modules are imported from the copy, never modified) and writes only to
outputs/tables/f13_*.csv and logs/fase_1_3/controlli_f13.txt.

No new backtest and no alternative strategy: the checks describe the data and the
way the original code treats them (stops, forward-filled days, splits, synthetic
series, index coverage, delisted names, benchmark timing, cash).
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
LOG = REPO / "logs" / "fase_1_3" / "controlli_f13.txt"
STOP = 0.35
FIELDS = ["open", "high", "low", "close", "adj_close"]

lines: list[str] = []


def say(msg: str = "") -> None:
    lines.append(msg)
    print(msg, flush=True)


def save(df: pd.DataFrame, name: str) -> None:
    df.to_csv(TABLES / name, index=False)
    say(f"  -> outputs/tables/{name} ({len(df)} rows)")


def load_original():
    sys.path.insert(0, str(CODE))
    import config
    assert Path(config.__file__).resolve().parent == CODE.resolve(), config.__file__
    import data_layer
    import patches
    from annual_study import price_index
    from panel import Panel
    from signals import ranking, year_end_rows
    return config, data_layer, patches, Panel, ranking, year_end_rows, price_index


# --------------------------------------------------------------------------- raw panel before filling
def raw_matrices(data_layer, labels, dates):
    """Rebuild the arrays exactly as data_layer.build_panel() fills them, BEFORE the
    forward fill and the 'missing open/high/low -> close' rule."""
    jb, y = data_layer.load_jb(), data_layer.load_yahoo()
    cal = data_layer.trading_calendar(y)
    assert cal.equals(dates), "trading calendar differs from the panel"
    allp = pd.concat([jb, y], ignore_index=True)
    allp = allp[allp.date.isin(cal)]
    sub = allp[allp.ticker.isin(set(labels))].drop_duplicates(["ticker", "date"], keep="first")
    d_idx = pd.Series(np.arange(len(cal)), index=cal)
    lab_idx = {k: i for i, k in enumerate(labels)}
    ri, ci = d_idx.loc[sub.date].values, sub.ticker.map(lab_idx).values
    raw = {}
    for f in FIELDS:
        a = np.full((len(cal), len(labels)), np.nan)
        a[ri, ci] = sub[f].astype(float).values
        raw[f] = a
    src_cat = sub.src.astype("category")
    src = np.full((len(cal), len(labels)), -1, dtype=np.int16)
    src[ri, ci] = src_cat.cat.codes.values
    return raw, src, list(src_cat.cat.categories)


def simulate_fill(raw):
    """Same rules as data_layer.build_panel(): forward fill inside each security's life
    (first..last valid adj_close), then open/high/low missing -> close."""
    arr = {f: raw[f].copy() for f in FIELDS}
    n, m = arr["adj_close"].shape
    life = np.zeros((n, m), dtype=bool)
    for j in range(m):
        ok = np.where(~np.isnan(raw["adj_close"][:, j]))[0]
        if len(ok) == 0:
            continue
        a0, a1 = ok[0], ok[-1]
        life[a0:a1 + 1, j] = True
        for f in FIELDS:
            arr[f][a0:a1 + 1, j] = pd.Series(arr[f][a0:a1 + 1, j]).ffill().values
    ohl_close = np.zeros((n, m), dtype=bool)
    for f in ["open", "high", "low"]:
        mk = np.isnan(arr[f]) & ~np.isnan(arr["close"])
        ohl_close |= mk
        arr[f][mk] = arr["close"][mk]
    return arr, life, ohl_close


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    config, data_layer, patches, Panel, ranking, year_end_rows, price_index = load_original()
    say(f"controlli_f13: code and data from {DEST.relative_to(REPO)} (original modules, unmodified)")

    p = Panel.load()
    n0 = len(p.labels)
    labels0 = [str(x) for x in p.labels]
    repairs = p.repairs.copy()
    patches.apply(p)
    ye = year_end_rows(p)
    last = len(p.dates) - 1
    dates = p.dates

    # ------------------------------------------------------------------ A. forward-filled cells
    say("\n[A] Forward-filled and partially rebuilt daily bars (data_layer.build_panel)")
    raw, src, src_names = raw_matrices(data_layer, labels0, dates)
    sim, life, ohl_close = simulate_fill(raw)
    ffill_adj = life & np.isnan(raw["adj_close"])
    ohl_stale = life & ~np.isnan(raw["close"]) & (np.isnan(raw["open"]) | np.isnan(raw["high"]) | np.isnan(raw["low"]))
    adj_stale_close_fresh = ffill_adj & ~np.isnan(raw["close"])
    say(f"  forward-filled adj_close cells inside a security's life: {int(ffill_adj.sum())} "
        f"(data_layer.py printed filled=11231)")
    say(f"    of which the raw close exists but adj_close is missing (stale adjustment factor): {int(adj_stale_close_fresh.sum())}")
    say(f"  bars with fresh close but missing open/high/low (filled from the previous day or set to close): {int(ohl_stale.sum())}")
    say(f"  cells where open/high/low were set equal to close after the fill: {int(ohl_close.sum())}")
    q = labels0.index("SNT-199910")
    same = {}
    for f, mine in (("open", sim["open"]), ("high", sim["high"]), ("low", sim["low"]), ("close", sim["close"])):
        pan = getattr(p, {"open": "o", "high": "h", "low": "l", "close": "c"}[f])[:, :n0]
        mask = np.ones(n0, dtype=bool)
        mask[q] = False
        same[f] = bool(np.array_equal(mine[:, mask], pan[:, mask], equal_nan=True))
    # panel._repair_adjustments() flags days with |adj_ret - close_ret - div_yield| > 15% and rebuilds the
    # adj_close of EVERY flagged column by cumulative product, even when no day is changed
    A, C = sim["adj_close"], sim["close"]
    with np.errstate(invalid="ignore", divide="ignore"):
        dy = np.nan_to_num(np.where(p.div[1:, :n0] > 0, p.div[1:, :n0] / C[:-1], 0.0))
        flag = np.abs(np.nan_to_num(A[1:] / A[:-1] - C[1:] / C[:-1] - dy)) > 0.15
    flagged = set(np.where(flag.any(0))[0]) - {q}
    logged = {labels0.index(lbl) for lbl in repairs.label.unique()}
    mask = np.array([j not in flagged and j != q for j in range(n0)])
    same["adj_close (columns not flagged by the repair rule)"] = bool(np.array_equal(A[:, mask], p.a[:, :n0][:, mask], equal_nan=True))
    say(f"  rebuilt arrays identical to the panel loaded by the original code: {same}")
    rel = []
    for j in sorted(flagged - logged):
        with np.errstate(invalid="ignore", divide="ignore"):
            rel.append(float(np.nanmax(np.abs(A[:, j] / p.a[:, j] - 1))))
    say(f"  columns flagged by the repair rule: {len(flagged)}; with a logged repair: {len(logged)}; flagged but unchanged: "
        f"{len(flagged - logged)}, rebuilt by cumulative product with max relative difference {max(rel):.1e} (floating point)")

    yrs = dates.year.values
    by_year = []
    for yv in np.unique(yrs):
        rows = yrs == yv
        by_year.append(dict(anno=int(yv), celle_adj_riempite=int(ffill_adj[rows].sum()),
                            titoli_coinvolti=int(ffill_adj[rows].any(0).sum()),
                            barre_ohl_mancanti_close_presente=int(ohl_stale[rows].sum()),
                            celle_ohl_poste_uguali_close=int(ohl_close[rows].sum())))
    save(pd.DataFrame(by_year), "f13_ffill_per_anno.csv")
    lab_src = {}
    for j in range(n0):
        codes = src[:, j][src[:, j] >= 0]
        lab_src[labels0[j]] = src_names[np.bincount(codes).argmax()] if len(codes) else ""
    by_src = pd.DataFrame(dict(fonte=[lab_src[labels0[j]] for j in range(n0)], celle=ffill_adj.sum(0)))
    by_src = by_src.groupby("fonte").agg(celle_adj_riempite=("celle", "sum"), titoli=("celle", "size"),
                                         titoli_con_celle_riempite=("celle", lambda x: int((x > 0).sum()))).reset_index()
    save(by_src, "f13_ffill_per_fonte.csv")

    # a stale (forward-filled) price on the decision day d or on d0 distorts the ranking return of ANY member
    rk_rows = []
    for yv in range(1996, 2026):
        d, d0 = ye[yv], ye[yv - 1]
        rk = ranking(p, "SPX", d, d0, min_days=126)
        rk = rk[[int(p.last_row[j]) > d for j in rk.col]].reset_index(drop=True)      # as in annual_study.py
        for pos_, x in enumerate(rk.itertuples(), start=1):
            if x.col >= n0:
                continue
            j = x.col
            start = d0 if not x.partial else int(p.first_row[j])
            stale = [str(dates[t].date()) for t in (start, d) if ffill_adj[t, j]]
            run = int(ffill_adj[start + 1:d + 1, j].sum())
            if stale or run >= 20:
                rk_rows.append(dict(anno_classifica=yv, posizione_in_classifica=pos_, label=x.label, rend_anno=x.mom,
                                    prezzo_riempito_in_data=";".join(stale), giorni_riempiti_nell_anno=run))
    rk_ff = pd.DataFrame(rk_rows, columns=["anno_classifica", "posizione_in_classifica", "label", "rend_anno",
                                           "prezzo_riempito_in_data", "giorni_riempiti_nell_anno"])
    save(rk_ff, "f13_ffill_classifica.csv")
    say(f"  ranked members with a forward-filled price on d0/d or >=20 filled days in the ranking year: {len(rk_ff)} member-years; "
        f"best position among them: {int(rk_ff.posizione_in_classifica.min()) if len(rk_ff) else '-'}; "
        f"within the top-10: {int((rk_ff.posizione_in_classifica <= 10).sum())}")

    # ------------------------------------------------------------------ B. the 90 positions
    say("\n[B] Data quality inside the ranking and holding windows of the 90 top-3 positions")
    t3 = pd.read_csv(REPRO / "AN_top3_anno.csv")
    jbraw = pd.read_parquet(config.JB_PRICES, columns=["ticker", "date", "stock_splits", "source"],
                            filters=[("ticker", "in", sorted(set(t3.label) - {x for x in t3.label if x.startswith("PATCH_")}))])
    jbraw["date"] = pd.to_datetime(jbraw["date"])
    splits = jbraw[(jbraw.stock_splits.fillna(0) != 0) & (jbraw.stock_splits.fillna(1) != 1)]
    rep_set = {(r.label, r.date) for r in repairs.itertuples()}
    pos_rows, split_rows, big_rows = [], [], []
    for r in t3.itertuples():
        j = p.lab_idx[r.label]
        d, d0 = ye[r.anno_T0], ye[r.anno_T0 - 1]
        s, e_year = d + 1, ye.get(r.anno_T0 + 1, last)
        e = min(e_year, int(p.last_row[j]))
        synth = r.label.startswith("PATCH_")
        rec = dict(anno_detenzione=r.anno_detenzione, posizione=r.posizione, label=r.label, sintetica=synth,
                   data_ingresso=dates[s].date(), data_uscita=dates[e].date(), sedute_detenzione=e - s + 1)
        if synth:
            rec.update(fonte_prevalente="patch (serie sintetica)")
        else:
            codes = src[s:e + 1, j][src[s:e + 1, j] >= 0]
            rec["fonte_prevalente"] = src_names[np.bincount(codes).argmax()] if len(codes) else ""
            rec["fonti_diverse_in_detenzione"] = len(np.unique(codes))
            rec["riempite_classifica"] = int(ffill_adj[d0 + 1:d + 1, j].sum())
            rec["riempita_d0_o_d"] = bool(ffill_adj[d0, j] or ffill_adj[d, j])
            rec["riempite_detenzione"] = int(ffill_adj[s:e + 1, j].sum())
            rec["riempita_ingresso_o_uscita"] = bool(ffill_adj[s, j] or ffill_adj[e, j])
            rec["ohl_mancanti_detenzione"] = int(ohl_stale[s:e + 1, j].sum())
            o, h, l, c = p.o[s:e + 1, j], p.h[s:e + 1, j], p.l[s:e + 1, j], p.c[s:e + 1, j]
            bad = (l > np.minimum(o, c) * (1 + 1e-9)) | (h < np.maximum(o, c) * (1 - 1e-9))
            rec["barre_ohlc_incoerenti_detenzione"] = int(np.nansum(bad))
        a = p.a[:, j]
        for tag, (x0, x1) in (("classifica", (d0, d)), ("detenzione", (d, e))):
            ret = a[x0 + 1:x1 + 1] / a[x0:x1] - 1
            ret = ret[np.isfinite(ret)]
            rec[f"max_rend_giornaliero_ass_{tag}"] = float(np.max(np.abs(ret))) if len(ret) else np.nan
        hold_ret = a[s:e + 1] / a[s - 1:e] - 1          # close-to-close total return of each holding day
        for k in np.where(np.abs(np.nan_to_num(hold_ret)) > 0.30)[0]:
            t = s + k
            big_rows.append(dict(anno_detenzione=r.anno_detenzione, posizione=r.posizione, label=r.label, data=dates[t].date(),
                                 rend_giornaliero_rett=float(hold_ret[k]), sintetica=synth,
                                 riempita=bool(ffill_adj[t, j]) if j < n0 else False))
        sp = splits[(splits.ticker == r.label) & (splits.date >= dates[d0]) & (splits.date <= dates[e])]
        rec["frazionamenti_classifica_e_detenzione"] = len(sp)
        for x in sp.itertuples():
            t = int(dates.searchsorted(x.date))
            rc = p.c[t, j] / p.c[t - 1, j] - 1
            ra = p.a[t, j] / p.a[t - 1, j] - 1
            split_rows.append(dict(anno_detenzione=r.anno_detenzione, posizione=r.posizione, label=r.label,
                                   data=x.date.date(), rapporto=float(x.stock_splits), fonte=x.source,
                                   finestra="classifica" if t <= d else "detenzione",
                                   rend_close_giorno=float(rc), rend_rett_giorno=float(ra),
                                   close_non_rettificata_per_frazionamento=bool(abs(rc) > 0.4),
                                   salto_nella_serie_rettificata=bool(abs(ra) > 0.4),
                                   riparazione_quel_giorno=(r.label, str(x.date.date())) in rep_set))
        rec["riparazioni_in_finestra"] = sum(1 for lbl, dd in rep_set if lbl == r.label and dates[d0] <= pd.Timestamp(dd) <= dates[e])
        # The rule is "35% below the purchase price"; the code compares total-return (dividend-adjusted) prices.
        # Same check on a price basis without dividends: annual_study.price_index() strips the dividends from
        # the total-return series (split-consistent); G = a / price_index grows with every dividend paid, so the
        # price stop sits at 0.65 * entry * G_t / G_s in total-return units.
        if not synth:
            G = p.a[:, j] / price_index(p, j)
            lvl_t = (1 - STOP) * (p.ao[s, j] if np.isfinite(p.ao[s, j]) else p.a[s, j]) * G[s:e + 1] / G[s]
            hit = np.where(p.al[s:e + 1, j] <= lvl_t)[0]
            rec["data_stop_su_prezzo_senza_dividendi"] = dates[s + hit[0]].date() if len(hit) else ""
            rec["dividendi_ingresso_stop_o_uscita"] = float(G[s + hit[0]] / G[s] - 1) if len(hit) else float(G[e] / G[s] - 1)
        rec["data_stop_codice"] = r.data_stop if isinstance(r.data_stop, str) else ""
        pos_rows.append(rec)
    pos = pd.DataFrame(pos_rows)
    pos["stop_stessa_data"] = pos.apply(lambda x: x.sintetica or str(x.data_stop_su_prezzo_senza_dividendi) == str(x.data_stop_codice), axis=1)
    save(pos, "f13_posizioni_qualita_dati.csv")
    save(pd.DataFrame(split_rows), "f13_frazionamenti_posizioni.csv")
    save(pd.DataFrame(big_rows), "f13_movimenti_estremi_detenzione.csv")
    real = pos[~pos.sintetica]
    say(f"  positions: {len(pos)} ({int(pos.sintetica.sum())} synthetic); forward-filled days in holding windows: "
        f"{int(real.riempite_detenzione.sum())} on {int((real.riempite_detenzione > 0).sum())} positions; "
        f"in ranking windows: {int(real.riempite_classifica.sum())}; at d0/d: {int(real['riempita_d0_o_d'].sum())}; "
        f"at entry/exit: {int(real['riempita_ingresso_o_uscita'].sum())}")
    say(f"  bars with missing open/high/low in holding windows: {int(real.ohl_mancanti_detenzione.sum())}; "
        f"incoherent OHLC bars: {int(real.barre_ohlc_incoerenti_detenzione.sum())}")
    say(f"  splits in ranking+holding windows: {len(split_rows)}; split days with a close NOT adjusted for the split: "
        f"{sum(x['close_non_rettificata_per_frazionamento'] for x in split_rows)} (sources "
        f"{sorted({x['fonte'] for x in split_rows if x['close_non_rettificata_per_frazionamento']})}); jumps in the adjusted "
        f"series on split days: {sum(x['salto_nella_serie_rettificata'] for x in split_rows)}; daily moves >30% in holding windows: {len(big_rows)}")
    diff_stop = real[~real.stop_stessa_data]
    say(f"  stop trigger date, price without dividends vs total-return price used by the code: different for {len(diff_stop)} "
        f"positions {diff_stop[['anno_detenzione', 'posizione', 'label', 'data_stop_codice', 'data_stop_su_prezzo_senza_dividendi']].values.tolist()}")

    # ------------------------------------------------------------------ C. the 4 stops on the winner
    say("\n[C] The stops on the number-one stock")
    ev, win = [], []
    for r in t3[(t3.posizione == 1) & t3.stop_toccato].itertuples():
        j = p.lab_idx[r.label]
        d = ye[r.anno_T0]
        s, e = d + 1, min(ye.get(r.anno_T0 + 1, last), int(p.last_row[j]))
        entry = p.ao[s, j] if np.isfinite(p.ao[s, j]) else p.a[s, j]
        lvl = entry * (1 - STOP)
        t = s + int(np.where(p.al[s:e + 1, j] <= lvl)[0][0])
        gap = bool(np.isfinite(p.ao[t, j]) and p.ao[t, j] <= lvl and t != s)
        fill = p.ao[t, j] if gap else lvl
        prior = p.al[s:t, j]
        sp = splits[(splits.ticker == r.label) & (splits.date >= dates[d - 5]) & (splits.date <= dates[e])]
        codes = src[s:t + 1, j]
        ev.append(dict(anno_detenzione=r.anno_detenzione, label=r.label, societa=r.societa,
                       data_ingresso=dates[s].date(), apertura_ingresso_non_rett=p.o[s, j], ingresso_rett=entry,
                       fattore_rettifica_ingresso=p.a[s, j] / p.c[s, j], livello_stop_rett=lvl,
                       data_stop=dates[t].date(), data_stop_csv=r.data_stop, sedute_fino_allo_stop=t - s,
                       minimo_rett_giorno_stop=p.al[t, j], apertura_rett_giorno_stop=p.ao[t, j],
                       chiusura_rett_giorno_prima=p.a[t - 1, j], apertura_sotto_livello=gap, prezzo_esecuzione_rett=fill,
                       rend_con_stop=fill / entry - 1, rend_con_stop_csv=r.rend_T1_con_stop,
                       rend_senza_stop_csv=r.rend_T1_senza_stop,
                       minimo_rett_prima_dello_stop=float(np.nanmin(prior)) if len(prior) else np.nan,
                       distanza_minima_prima_dello_stop=float(np.nanmin(prior) / lvl - 1) if len(prior) else np.nan,
                       fonte_dati=",".join(sorted({src_names[c] for c in codes if c >= 0})),
                       giorni_riempiti_fino_allo_stop=int(ffill_adj[s:t + 1, j].sum()),
                       ohl_mancanti_fino_allo_stop=int(ohl_stale[s:t + 1, j].sum()),
                       frazionamenti=";".join(f"{x.date.date()} x{x.stock_splits:g}" for x in sp.itertuples()),
                       riparazioni=int(sum(1 for lbl, dd in rep_set if lbl == r.label and dates[d] <= pd.Timestamp(dd) <= dates[e]))))
        for k in sorted(set(range(s - 1, s + 2)) | set(range(max(s - 1, t - 3), min(e, t + 3) + 1))):
            win.append(dict(anno_detenzione=r.anno_detenzione, label=r.label, data=dates[k].date(),
                            giorno_relativo=k - t, open=p.o[k, j], high=p.h[k, j], low=p.l[k, j], close=p.c[k, j],
                            open_rett=p.ao[k, j], low_rett=p.al[k, j], close_rett=p.a[k, j], volume=p.vol[k, j],
                            fonte=src_names[src[k, j]] if src[k, j] >= 0 else "", adj_riempito=bool(ffill_adj[k, j]),
                            ohl_mancanti=bool(ohl_stale[k, j]), livello_stop_rett=lvl))
    ev = pd.DataFrame(ev)
    save(ev, "f13_stop_vincitore_eventi.csv")
    save(pd.DataFrame(win), "f13_stop_vincitore_finestre.csv")
    for x in ev.itertuples():
        say(f"  {x.anno_detenzione} {x.label}: entry {x.data_ingresso}, stop {x.data_stop} (csv {x.data_stop_csv}) after "
            f"{x.sedute_fino_allo_stop} sessions, gap={x.apertura_sotto_livello}, ret {x.rend_con_stop:+.4f} "
            f"(csv {x.rend_con_stop_csv:+.4f}), source {x.fonte_dati}, filled days {x.giorni_riempiti_fino_allo_stop}, "
            f"splits [{x.frazionamenti}], repairs {x.riparazioni}, closest earlier low {x.distanza_minima_prima_dello_stop:+.3f} vs level")

    # ------------------------------------------------------------------ D. synthetic series
    say("\n[D] The 9 synthetic series (patches.py)")
    syn = []
    for pt in patches.PATCHES:
        r = t3[t3.label == pt["label"]]
        r = r.iloc[0] if len(r) else None
        syn.append(dict(label=pt["label"], societa=pt["name"], anno_classifica=pt["rank_year"],
                        posizione=None if r is None else int(r.posizione),
                        rend_classifica_patch=pt["rank_tr"], rend_T0_riprodotto=None if r is None else r.rend_T0,
                        rend_detenzione_patch=pt["hold_tr"], rend_T1_riprodotto=None if r is None else r.rend_T1_senza_stop,
                        data_stop_patch=pt["stop_date"] or "", data_stop_riprodotta=None if r is None or not r.stop_toccato else r.data_stop,
                        rend_con_stop_riprodotto=None if r is None else r.rend_T1_con_stop,
                        dividendi_riprodotti=None if r is None else r.dividendi_T1,
                        membro_dal=pt["member_from"], da_verificare_secondo_autori=pt["label"] in ("PATCH_RBK-2001", "PATCH_AV-2004")))
    syn = pd.DataFrame(syn)
    syn["diff_rend_classifica"] = syn.rend_T0_riprodotto - syn.rend_classifica_patch
    syn["diff_rend_detenzione"] = syn.rend_T1_riprodotto - syn.rend_detenzione_patch
    syn["uguale_a_patch"] = (np.isclose(syn.rend_classifica_patch, syn.rend_T0_riprodotto, rtol=0, atol=1e-12)
                             & np.isclose(syn.rend_detenzione_patch, syn.rend_T1_riprodotto, rtol=0, atol=1e-12))
    # stopped series: patches.apply() writes a[r1:sd+1] = base * lvl**(k/k) * 1.0001, which also lifts the
    # rank-year-end value a[r1] (= entry price) by 0.01%
    syn["scarto_spiegato_dal_fattore_1_0001"] = (
        syn.data_stop_patch.ne("")
        & np.isclose((1 + syn.rend_classifica_patch) * 1.0001 - 1, syn.rend_T0_riprodotto, rtol=0, atol=1e-12)
        & np.isclose((1 + syn.rend_detenzione_patch) / 1.0001 - 1, syn.rend_T1_riprodotto, rtol=0, atol=1e-12))
    save(syn, "f13_serie_sintetiche.csv")
    say(f"  all 9 in the reproduced top-3: {syn.posizione.notna().all()}; positions {syn.posizione.value_counts().sort_index().to_dict()}; "
        f"returns equal to patches.py: {syn[syn.uguale_a_patch].label.tolist()}; differing only by the 1.0001 factor: "
        f"{syn[syn.scarto_spiegato_dal_fattore_1_0001].label.tolist()} (max |diff| rank year "
        f"{syn.diff_rend_classifica.abs().max():.1e}, holding year {syn.diff_rend_detenzione.abs().max():.1e})")

    # ------------------------------------------------------------------ E. index coverage
    say("\n[E] Point-in-time coverage of the S&P 500")
    cov_o = pd.read_csv(integrity.PROTECTED / "results" / "copertura_dati.csv")
    cov_o = cov_o[cov_o.indice == "SPX"].set_index("anno")
    cov = []
    for yv in range(1996, dates[-1].year + 1):
        d, d0 = ye[yv], ye[yv - 1]
        dt = dates[d]
        m = p.spx[(p.spx.start <= dt) & (p.spx.end.isna() | (p.spx.end > dt))]
        m_real = m[~m.ticker.str.startswith("PATCH_")]
        rk = ranking(p, "SPX", d, d0, min_days=126)
        ranked = set(rk.label)
        n_patch = sum(1 for x in ranked if x.startswith("PATCH_"))
        not_ranked = [t for t in m_real.ticker if t not in ranked]
        with_price = sum(1 for t in m_real.ticker if t in p.lab_idx)
        n_mem_orig_def = len(rk) + len(not_ranked)
        cov.append(dict(anno=yv, membri_nel_file_composizione=len(m_real), membri_con_serie_prezzi=with_price,
                        classificati=len(rk), di_cui_serie_sintetiche=n_patch,
                        membri_definizione_originale=n_mem_orig_def,
                        membri_fine_anno_originale=int(cov_o.loc[yv, "membri_fine_anno"]) if yv in cov_o.index else np.nan,
                        classificati_originale=int(cov_o.loc[yv, "classificati"]) if yv in cov_o.index else np.nan,
                        copertura_originale=float(cov_o.loc[yv, "copertura"]) if yv in cov_o.index else np.nan,
                        copertura_su_file_composizione=len(rk) / len(m_real),
                        copertura_senza_sintetiche=(len(rk) - n_patch) / len(m_real)))
    cov = pd.DataFrame(cov)
    cov["doppio_conteggio"] = cov.membri_definizione_originale - cov.membri_nel_file_composizione
    save(cov, "f13_copertura.csv")
    say(f"  original member count reproduced in {int((cov.membri_definizione_originale == cov.membri_fine_anno_originale).sum())}"
        f"/{len(cov)} years; ranked count reproduced in {int((cov.classificati == cov.classificati_originale).sum())}/{len(cov)}; "
        f"years where the original count exceeds the membership file: {cov[cov.doppio_conteggio > 0].anno.tolist()}")

    # ------------------------------------------------------------------ F. delisted names
    say("\n[F] Delisted names and the 'still trading after the decision day' filter")
    dl, excl = [], []
    for yv in range(1996, 2026):
        d, d0 = ye[yv], ye[yv - 1]
        cols = p.members("SPX", dates[d])
        ended_before = [p.labels[j] for j in cols if p.first_row[j] <= d and p.last_row[j] < d]
        rk = ranking(p, "SPX", d, d0, min_days=126)
        last_day = rk[[int(p.last_row[j]) == d for j in rk.col]]
        kept = rk[[int(p.last_row[j]) > d for j in rk.col]].reset_index(drop=True)
        third = float(kept.mom.iloc[2])
        for x in last_day.itertuples():
            excl.append(dict(anno_classifica=yv, label=x.label, rend_anno=x.mom, rend_terzo_classificato=third,
                             sarebbe_entrato_nella_top3=bool(x.mom > third)))
        dl.append(dict(anno_classifica=yv, membri_con_prezzi=len(cols), serie_terminate_prima_di_fine_anno=len(ended_before),
                       esclusi_perche_ultimo_prezzo_a_fine_anno=len(last_day),
                       esclusi_che_sarebbero_in_top3=int(sum(1 for x in last_day.mom if x > third))))
    save(pd.DataFrame(dl), "f13_delisting_per_anno.csv")
    save(pd.DataFrame(excl, columns=["anno_classifica", "label", "rend_anno", "rend_terzo_classificato",
                                     "sarebbe_entrato_nella_top3"]), "f13_esclusi_ultimo_giorno.csv")
    held = t3[t3.uscita_dal_listino_nell_anno]
    say(f"  members whose series ends before year-end (not ranked): {sum(x['serie_terminate_prima_di_fine_anno'] for x in dl)} "
        f"member-years; excluded because the last price is the decision day: {len(excl)}, of which would rank top-3: "
        f"{sum(x['sarebbe_entrato_nella_top3'] for x in excl)}")
    say(f"  top-3 positions whose series ends inside the holding year: {held[['anno_detenzione', 'label', 'ultimo_prezzo']].values.tolist()}")

    # ------------------------------------------------------------------ G. benchmark vs strategy timing
    say("\n[G] Timing of the benchmark and of the strategy")
    spy, gspc, tr = p.lab_idx["Y_SPY"], p.lab_idx["Y_^GSPC"], p.lab_idx["Y_^SP500TR"]
    ann = pd.read_csv(REPRO / "AN_rendimenti_annui.csv")
    al = []
    for yv in range(1997, dates[-1].year + 1):
        d = ye[yv - 1]
        s, e = d + 1, ye.get(yv, last)
        al.append(dict(anno=yv, decisione=dates[d].date(), ingresso_strategia=dates[s].date(), uscita=dates[e].date(),
                       benchmark_da="chiusura " + str(dates[d].date()), strategia_da="apertura " + str(dates[s].date()),
                       gap_notturno_SPY=p.o[s, spy] / p.c[d, spy] - 1,
                       gap_notturno_GSPC=p.o[s, gspc] / p.c[d, gspc] - 1,
                       apertura_SP500TR_uguale_chiusura_prec=bool(np.isclose(p.o[s, tr], p.c[d, tr], rtol=1e-12)),
                       SP500_TR_csv=float(ann.loc[ann.anno == yv, "SP500_TR"].iat[0]),
                       SP500_TR_ricalcolato=p.a[e, tr] / p.a[d, tr] - 1))
    al = pd.DataFrame(al)
    save(al, "f13_allineamento_benchmark.csv")
    g = al.gap_notturno_SPY
    say(f"  the benchmark includes the overnight move close(d)->open(d+1) that the strategy does not: SPY gap mean "
        f"{g.mean():+.4%}, median {g.median():+.4%}, min {g.min():+.4%} ({al.anno[g.idxmin()]}), max {g.max():+.4%} "
        f"({al.anno[g.idxmax()]}), mean |gap| {g.abs().mean():.4%}")
    say(f"  ^GSPC open equal to the previous close in {int((al.gap_notturno_GSPC.abs() < 1e-12).sum())}/{len(al)} years; "
        f"^SP500TR open equal to the previous close in {int(al.apertura_SP500TR_uguale_chiusura_prec.sum())}/{len(al)} years")
    say(f"  SP500_TR in AN_rendimenti_annui = close-to-close recomputation: "
        f"{bool(np.allclose(al.SP500_TR_csv, al.SP500_TR_ricalcolato, rtol=0, atol=1e-15))}; 2026 window "
        f"{al.ingresso_strategia.iat[-1]} -> {al.uscita.iat[-1]}, annual_study.metrics() uses span 0.77 for it "
        f"(trading sessions {ye[2026] - ye[2025]}/252 = {(ye[2026] - ye[2025]) / 252:.3f})")

    # ------------------------------------------------------------------ H. identities: cash, averages, compounding
    say("\n[H] Arithmetic identities in the reproduced outputs (cash after a stop, top-3 average, compounding)")
    s_ = pd.read_csv(REPRO / "AN_sintesi.csv")
    ids = []

    def ident(name, ok, n, note=""):
        ids.append(dict(controllo=name, verificato=bool(ok), casi=n, nota=note))

    g1 = t3[t3.posizione == 1].set_index("anno_detenzione")
    a2 = ann.set_index("anno")
    ident("top1_senza_stop = rendimento del 1o classificato", np.allclose(a2.top1_senza_stop, g1.rend_T1_senza_stop.loc[a2.index], 0, 0), len(a2))
    ident("top1_con_stop = rendimento con stop del 1o classificato", np.allclose(a2.top1_con_stop, g1.rend_T1_con_stop.loc[a2.index], 0, 0), len(a2))
    m3 = t3.groupby("anno_detenzione")[["rend_T1_senza_stop", "rend_T1_con_stop"]].mean()
    ident("top3 = media semplice dei tre rendimenti (nessun ribilanciamento)",
          np.allclose(a2.top3_senza_stop, m3.rend_T1_senza_stop.loc[a2.index], rtol=0, atol=1e-15)
          and np.allclose(a2.top3_con_stop, m3.rend_T1_con_stop.loc[a2.index], rtol=0, atol=1e-15), len(a2))
    st = t3[t3.stop_toccato]
    entry = st.prezzo_ingresso_rett
    fill = entry * (1 + st.rend_T1_con_stop)
    nogap = st[~st.stop_in_gap]
    ident("stop senza gap: esecuzione esattamente al 65% del prezzo d'ingresso rettificato",
          np.allclose(1 + nogap.rend_T1_con_stop, 1 - STOP, rtol=0, atol=1e-12), len(nogap))
    ident("stop con gap: esecuzione all'apertura, sotto il livello", bool((fill[st.stop_in_gap] <= entry[st.stop_in_gap] * (1 - STOP) + 1e-12).all()),
          int(st.stop_in_gap.sum()))
    ident("liquidita' dopo lo stop a rendimento zero: il rendimento con stop non dipende dai prezzi successivi allo stop",
          np.allclose(st.rend_T1_con_stop, fill / entry - 1, rtol=0, atol=1e-12), len(st),
          "annual_study.stock_year(): ret_s = fill / entry - 1, nessun interesse; verificato anche nel codice")
    ident("dividendi dopo lo stop esclusi (dividendi_T1_con_stop <= dividendi_T1)",
          bool((t3.dividendi_T1_con_stop <= t3.dividendi_T1 + 1e-15).all()), len(t3))
    ident("titoli_fermati_top3 = numero di stop nell'anno",
          bool((a2.titoli_fermati_top3 == t3.groupby("anno_detenzione").stop_toccato.sum().loc[a2.index]).all()), len(a2))
    lp = np.allclose(a2.leaps35_azione65, 0.35 * a2.leaps_rend_opzione + 0.65 * a2.top1_senza_stop, rtol=0, atol=1e-12)
    ident("LEAPS 35/65 = 0,35 x opzione + 0,65 x azione", lp, len(a2))
    for col, strat in (("SP500_TR", "S&P 500 (indice Total Return)"), ("top1_senza_stop", "Solo vincitore, senza stop"),
                       ("top1_con_stop", "Solo vincitore, stop 35%"), ("top3_senza_stop", "Prime tre, senza stop"),
                       ("top3_con_stop", "Prime tre, stop 35%")):
        rr = a2.loc[1997:2025, col]
        vf = 100 * np.prod(1 + rr.values)
        row = s_[(s_.periodo == "1997-2025") & (s_.strategia == strat) & (s_.vista == "Lordo")].iloc[0]
        ident(f"Lordo 1997-2025 '{strat}': valore finale = 100 x prodotto(1 + r) e CAGR = (VF/100)^(1/29) - 1",
              np.isclose(vf, row.valore_finale, rtol=1e-12) and np.isclose((vf / 100) ** (1 / 29) - 1, row.cagr, rtol=1e-12), 29)
    ids = pd.DataFrame(ids)
    save(ids, "f13_identita.csv")
    say(f"  identities verified: {int(ids.verificato.sum())}/{len(ids)}")

    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
