"""
Annual study requested by the client (October 2026), S&P 500 only.

For every ranking year T0 = 1996..2025:
  * the three best S&P 500 members by calendar-year total return in T0 (point-in-time membership,
    survivorship patches included);
  * their total return in the following calendar year T0+1 (close of the last trading day of T0 to
    close of the last trading day of T0+1; 2026 = to 9-Oct-2026), without stop and with a 35% stop
    below the entry price (daily lows; filled at the level, or at the open if the stock gaps below it);
  * portfolio returns of: winner only, top-3 at 1/3 each (a stopped stock stays in cash, the others stay
    invested), winner with 35% of capital in LEAPS + 65% in the stock itself;
  * the S&P 500 (Total Return index, and a UCITS accumulating ETF);
  * three tax views: LORDO (no costs, no taxes), LORDISTA (costs + stamp duty, 26% only once at the end),
    NETTISTA (costs + stamp duty, 26% on every annual realisation with the 4-year loss carry-forward,
    US dividends 37.1%).
All amounts in USD (the thread's currency).
"""
from __future__ import annotations

import datetime as dt
import json
import math

import numpy as np
import pandas as pd

import patches
from benchmarks import index_tr
from config import OUT
from leaps import bs_call, realised_vol, strike_for_premium
from names import company
from panel import Panel
from signals import ranking, year_end_rows

COST = 0.001        # per side
BOLLO = 0.002       # stamp duty on the year-end value
CG = 0.26
DIV_NET = 0.371     # US dividends for an Italian resident (15% US + 26% on the net)
DIV_WRAP = 0.15     # US withholding inside a tax-deferred wrapper / fund
AMC = 0.005         # annual cost of the tax-deferred wrapper (actively managed certificate), lordista strategies only
STOP = 0.35
LEAPS_PREM = 0.35
LEAPS_W = 0.35
CARRY = 4
FIRST, LAST = 1996, 2025       # ranking years


def third_friday(y, m=1):
    d = dt.date(y, m, 15)
    while d.weekday() != 4:
        d += dt.timedelta(days=1)
    return d


def price_index(p, j):
    a = p.a[:, j]
    dy = p.div_yield[:, j]
    r = np.ones_like(a)
    r[1:] = a[1:] / a[:-1] - dy[1:]
    r = np.where(np.isfinite(r), r, 1.0)
    pi = np.cumprod(r)
    pi[np.isnan(a)] = np.nan
    return pi


def entry_price(p, j, s):
    op = p.ao[s, j]
    return float(op) if np.isfinite(op) else float(p.a[s, j])


def stock_year(p, j, d, e_year):
    """Holding-year outcome of column j: bought at the OPEN of the first trading day after the
    decision close (row d+1), sold at the close of the last trading day of the year."""
    s = d + 1
    e = min(e_year, p.last_row[j])
    entry = entry_price(p, j, s)
    ret = p.a[e, j] / entry - 1
    div = float(np.nansum(p.div_yield[s + 1:e + 1, j]))
    lvl = entry * (1 - STOP)
    lows = p.al[s:e + 1, j]
    hit = np.where(lows <= lvl)[0]
    if len(hit):
        t = s + hit[0]
        op = p.ao[t, j]
        fill = op if (np.isfinite(op) and op <= lvl and t != s) else lvl
        ret_s = fill / entry - 1
        div_s = float(np.nansum(p.div_yield[s + 1:t + 1, j]))
        stop_date = p.dates[t].date()
        gap = bool(np.isfinite(op) and op <= lvl and t != s)
    else:
        ret_s, div_s, stop_date, gap = ret, div, None, False
    delisted = p.last_row[j] < e_year
    return dict(ret=ret, div=div, ret_stop=ret_s, div_stop=div_s, stop_date=stop_date, stop_gap=gap, entry=entry,
                exit_price=float(p.a[e, j]), exit_row=e, delisted_during_year=delisted,
                last_date=p.dates[p.last_row[j]].date())


def leaps_year(p, j, d, e, label, iv_mult=1.10, hs=0.03, proxy_sigma=None, exp_years=2):
    """Return of a LEAPS bought at the close of row d (premium = 35% of spot, expiry 3rd Friday of
    January of the year after the holding year) and sold at row e. Black-Scholes, IV = realised vol x mult."""
    pi = price_index(p, j)
    s = d + 1
    S0 = pi[s] * entry_price(p, j, s) / p.a[s, j]      # price index at the open of the first trading day
    S1 = pi[e]
    d0, d1 = p.dates[s].date(), p.dates[e].date()
    exp = third_friday(p.dates[d].year + exp_years)    # default: January of the year after the holding year
    T0 = (exp - d0).days / 365.0
    T1 = max((exp - d1).days / 365.0, 1e-6)
    synthetic = label.startswith("PATCH_")
    if synthetic:
        s_in = s_out = proxy_sigma
    else:
        s_in = realised_vol(p.a[:, j], d, 252)
        if not np.isfinite(s_in):
            s_in = realised_vol(p.a[:, j], d, 63, min_obs=20)
        s_in = float(np.clip(s_in * iv_mult, 0.20, 2.0))
        s_out = realised_vol(p.a[:, j], e, 63, min_obs=20)
        s_out = float(np.clip(s_out * iv_mult, 0.20, 2.0)) if np.isfinite(s_out) else s_in
    q = float(np.nansum(p.div_yield[max(0, d - 252):d + 1, j]))
    r = float(np.nan_to_num(p.rate_1y[d], nan=0.03))
    K = strike_for_premium(S0, T0, r, q, s_in, LEAPS_PREM)
    mid0 = float(bs_call(S0, K, T0, r, q, s_in))
    mid1 = float(bs_call(S1, K, T1, r, q, s_out))
    ask, bid = mid0 * (1 + hs), mid1 * (1 - hs)
    return dict(K_over_S=K / S0, iv_entry=s_in, iv_exit=s_out, T_entry=T0, T_exit=T1, rate=r, div_yield=q,
                premium_mid_over_S=mid0 / S0, S_change=S1 / S0 - 1, intrinsic_exit_over_S0=max(S1 - K, 0) / S0,
                value_exit_over_S0=mid1 / S0, ret_option=bid / ask - 1, expiry=exp, sigma_proxy=synthetic)


# ---------------------------------------------------------------------------------- tax engines
def run_lordo(rets):
    w, path = 100.0, []
    for r in rets:
        w *= 1 + r
        path.append(w)
    return path


def run_lordista(rets, divs, n_sides=2):
    """Costs, AMC wrapper fee, stamp duty, 15% US withholding on dividends; 26% only on the final gain."""
    w, path = 100.0, []
    for r, dv in zip(rets, divs):
        w = w * (1 - COST) * (1 + r - DIV_WRAP * dv) * (1 - COST) * (1 - AMC) * (1 - BOLLO)
        path.append(w)
    final_after = w - CG * max(w - 100.0, 0.0)
    return path, final_after


def run_nettista(rets, divs, years, extra_cg=None):
    """Annual realisation. Capital gains/losses (redditi diversi) through the 4-year 'zainetto';
    dividends taxed 37.1% with no offset. Returns year-end path and a ledger."""
    w, losses, path, ledger = 100.0, [], [], []
    for k, (r, dv, y) in enumerate(zip(rets, divs, years)):
        invested = w * (1 - COST)
        value = invested * (1 + r)
        proceeds = value * (1 - COST)
        div_amt = invested * dv
        cg = proceeds - w - div_amt
        # expire old losses
        expired = sum(a for a, e in losses if e < y)
        losses = [[a, e] for a, e in losses if e >= y]
        used = 0.0
        if cg > 0:
            losses.sort(key=lambda x: x[1])
            rem = cg
            for item in losses:
                u = min(item[0], rem)
                item[0] -= u
                rem -= u
                used += u
                if rem <= 0:
                    break
            losses = [x for x in losses if x[0] > 1e-12]
            tax_cg = CG * (cg - used)
        else:
            if cg < 0:
                losses.append([-cg, y + CARRY])
            tax_cg = 0.0
        tax_div = DIV_NET * div_amt
        after = proceeds - tax_cg - tax_div
        w = after * (1 - BOLLO)
        path.append(w)
        ledger.append(dict(anno=y, valore_inizio=invested / (1 - COST), plus_minus=cg, dividendi=div_amt,
                           minus_usate=used, imponibile=max(cg - used, 0.0) if cg > 0 else 0.0,
                           imposta_plus=tax_cg, imposta_dividendi=tax_div, minus_scadute=expired,
                           zainetto_fine=sum(a for a, _ in losses), bollo=after * BOLLO, valore_fine=w))
    return path, pd.DataFrame(ledger)


def run_etf(rets_etf, mode):
    w, path, losses_wasted = 100.0, [], 0.0
    if mode == "bh":
        w *= 1 - COST
        for r in rets_etf:
            w = w * (1 + r) * (1 - BOLLO)
            path.append(w)
        final_after = w * (1 - COST)
        final_after -= CG * max(final_after - 100.0, 0.0)
        return path, final_after
    # annual sell & rebuy: gains taxed every year, ETF losses cannot offset ETF gains (wasted)
    for r in rets_etf:
        proceeds = w * (1 - COST) * (1 + r) * (1 - COST)
        gain = proceeds - w
        tax = CG * gain if gain > 0 else 0.0
        if gain < 0:
            losses_wasted += -gain
        w = (proceeds - tax) * (1 - BOLLO)
        path.append(w)
    return path, w


def metrics(years, path, final_after=None, bench_rets=None, rets=None):
    vals = np.array([100.0] + list(path))
    n = len(path)
    span = n - 1 + (0.77 if years[-1] == 2026 else 1.0)
    fin = final_after if final_after is not None else vals[-1]
    yr = vals[1:] / vals[:-1] - 1
    dd = (vals / np.maximum.accumulate(vals) - 1).min()
    out = dict(valore_finale=fin, cagr=(fin / 100) ** (1 / span) - 1, peggior_anno=yr.min(), miglior_anno=yr.max(),
               max_drawdown_fine_anno=dd, anni_negativi=int((yr < 0).sum()), anni=n)
    if bench_rets is not None:
        out["anni_sopra_SP500"] = int((yr > np.array(bench_rets)).sum())
    return out


def main():
    p = patches.apply(Panel.load())
    ye = year_end_rows(p)
    last = len(p.dates) - 1
    sp_tr = p.series("Y_^SP500TR", "a")
    etf = index_tr(p, "SPX")
    rows, years = [], list(range(FIRST, LAST + 1))
    for T0 in years:
        d, d0 = ye[T0], ye[T0 - 1]
        e_year = ye.get(T0 + 1, last)
        rk = ranking(p, "SPX", d, d0, min_days=126)
        rk = rk[[p.last_row[j] > d for j in rk.col]].reset_index(drop=True)     # must trade after the decision day
        for k in range(3):
            j, lab = int(rk.col.iloc[k]), rk.label.iloc[k]
            sy = stock_year(p, j, d, e_year)
            rows.append(dict(anno_T0=T0, anno_detenzione=T0 + 1, posizione=k + 1, ticker=lab.replace("Y_", ""), label=lab,
                             societa=company(lab), serie_ricostruita=lab.startswith("PATCH_"),
                             rend_T0=float(rk.mom.iloc[k]), parziale_T0=bool(rk.partial.iloc[k]),
                             rend_T1_senza_stop=sy["ret"], stop_toccato=sy["stop_date"] is not None,
                             data_stop=sy["stop_date"], stop_in_gap=sy["stop_gap"], rend_T1_con_stop=sy["ret_stop"],
                             prezzo_ingresso_rett=sy["entry"], prezzo_uscita_rett=sy["exit_price"], dividendi_T1=sy["div"], dividendi_T1_con_stop=sy["div_stop"],
                             uscita_dal_listino_nell_anno=sy["delisted_during_year"], ultimo_prezzo=sy["last_date"],
                             d_row=d, e_row=sy["exit_row"], col=j))
    t3 = pd.DataFrame(rows)
    # proxy volatility for the reconstructed series: median entry IV of the genuine top-1 names
    raw = []
    for r in t3[(t3.posizione == 1) & (~t3.serie_ricostruita)].itertuples():
        s = realised_vol(p.a[:, r.col], r.d_row, 252)
        if np.isfinite(s):
            raw.append(s)
    proxy = float(np.median(raw))
    # ---- annual table
    ann = []
    for T0 in years:
        g = t3[t3.anno_T0 == T0].sort_values("posizione")
        d = ye[T0]
        e = ye.get(T0 + 1, last)
        y = T0 + 1
        rec = dict(anno=y, SP500_TR=sp_tr.iloc[e] / sp_tr.iloc[d] - 1, SP500_ETF=etf.iloc[e] / etf.iloc[d] - 1,
                   top1_senza_stop=g.rend_T1_senza_stop.iloc[0], top1_con_stop=g.rend_T1_con_stop.iloc[0],
                   top3_senza_stop=g.rend_T1_senza_stop.mean(), top3_con_stop=g.rend_T1_con_stop.mean(),
                   div_top1=g.dividendi_T1.iloc[0], div_top1_stop=g.dividendi_T1_con_stop.iloc[0],
                   div_top3=g.dividendi_T1.mean(), div_top3_stop=g.dividendi_T1_con_stop.mean(),
                   titoli_fermati_top3=int(g.stop_toccato.sum()))
        r1 = g.iloc[0]
        for mult, hs, tag, ey in ((1.10, 0.03, "", 2), (0.90, 0.01, "_ottimista", 2), (1.30, 0.06, "_prudente", 2),
                                  (1.10, 0.03, "_2anni", 3)):
            lp = leaps_year(p, int(r1.col), int(r1.d_row), int(r1.e_row), r1.label, mult, hs, proxy, ey)
            rec[f"leaps_rend_opzione{tag}"] = lp["ret_option"]
            if tag == "":
                rec.update({f"leaps_{k}": v for k, v in lp.items() if k != "ret_option"})
            if tag == "_2anni":
                rec["leaps_K_over_S_2anni"] = lp["K_over_S"]
        for tag in ("", "_ottimista", "_prudente", "_2anni"):
            ro = rec[f"leaps_rend_opzione{tag}"]
            rec[f"leaps35_azione65{tag}"] = LEAPS_W * ro + (1 - LEAPS_W) * rec["top1_senza_stop"]
            rec[f"leaps35_azione65_stop{tag}"] = LEAPS_W * ro + (1 - LEAPS_W) * rec["top1_con_stop"]
        ann.append(rec)
    ann = pd.DataFrame(ann)

    # ---- tax views
    strategies = {
        "Solo vincitore, senza stop": ("top1_senza_stop", "div_top1"),
        "Solo vincitore, stop 35%": ("top1_con_stop", "div_top1_stop"),
        "Prime tre, senza stop": ("top3_senza_stop", "div_top3"),
        "Prime tre, stop 35%": ("top3_con_stop", "div_top3_stop"),
        "Vincitore: 35% LEAPS + 65% azione": ("leaps35_azione65", None),
        "Vincitore: 35% LEAPS + 65% azione con stop": ("leaps35_azione65_stop", None),
    }
    res, paths, ledgers = [], {}, {}
    periods = {"1997-2025": (1997, 2025), "1997-2026 (YTD)": (1997, 2026), "1997-2008": (1997, 2008),
               "2009-2025": (2009, 2025), "2009-2026 (YTD)": (2009, 2026)}
    for pname, (a, b) in periods.items():
        sub = ann[(ann.anno >= a) & (ann.anno <= b)]
        yrs = sub.anno.tolist()
        sp_g = sub.SP500_TR.tolist()
        # benchmarks
        pth = run_lordo(sp_g)
        res.append(dict(periodo=pname, strategia="S&P 500 (indice Total Return)", vista="Lordo", **metrics(yrs, pth)))
        paths[(pname, "S&P 500 (indice Total Return)", "Lordo")] = pth
        pth, fa = run_etf(sub.SP500_ETF.tolist(), "bh")
        for vista in ("Lordista", "Nettista"):
            res.append(dict(periodo=pname, strategia="S&P 500 ETF, compra e tieni", vista=vista,
                            **metrics(yrs, pth, fa)))
            paths[(pname, "S&P 500 ETF, compra e tieni", vista)] = pth
        pth, fa = run_etf(sub.SP500_ETF.tolist(), "annual")
        res.append(dict(periodo=pname, strategia="S&P 500 ETF, vendi e ricompra ogni anno", vista="Nettista",
                        **metrics(yrs, pth, fa)))
        paths[(pname, "S&P 500 ETF, vendi e ricompra ogni anno", "Nettista")] = pth
        for sname, (col, dcol) in strategies.items():
            rets = sub[col].tolist()
            if dcol is None:     # LEAPS mixes: dividends only on the 65% stock sleeve
                base = "div_top1_stop" if "stop" in col else "div_top1"
                divs = (sub[base] * (1 - LEAPS_W)).tolist()
            else:
                divs = sub[dcol].tolist()
            pth = run_lordo(rets)
            res.append(dict(periodo=pname, strategia=sname, vista="Lordo", **metrics(yrs, pth, bench_rets=sp_g)))
            paths[(pname, sname, "Lordo")] = pth
            pth, fa = run_lordista(rets, divs)
            res.append(dict(periodo=pname, strategia=sname, vista="Lordista", **metrics(yrs, pth, fa)))
            paths[(pname, sname, "Lordista")] = pth
            pth, led = run_nettista(rets, divs, yrs)
            res.append(dict(periodo=pname, strategia=sname, vista="Nettista", **metrics(yrs, pth),
                            imposte_pagate=float(led.imposta_plus.sum() + led.imposta_dividendi.sum()),
                            minus_scadute=float(led.minus_scadute.sum())))
            paths[(pname, sname, "Nettista")] = pth
            if pname == "1997-2026 (YTD)":
                ledgers[sname] = led
    res = pd.DataFrame(res)

    # rolling 10-year windows (full years), lordo and nettista vs S&P
    roll = []
    for a in range(1997, 2017):
        b = a + 9
        sub = ann[(ann.anno >= a) & (ann.anno <= b)]
        yrs = sub.anno.tolist()
        sp = (np.prod(1 + sub.SP500_TR) ** 0.1) - 1
        pth, fa = run_etf(sub.SP500_ETF.tolist(), "bh")
        sp_net = (fa / 100) ** 0.1 - 1
        rec = dict(inizio=a, fine=b, SP500_lordo=sp, SP500_ETF_nettista=sp_net)
        for sname, (col, dcol) in strategies.items():
            rets = sub[col].tolist()
            divs = (sub["div_top1_stop" if "stop" in col else "div_top1"] * (1 - LEAPS_W)).tolist() if dcol is None else sub[dcol].tolist()
            rec[f"{sname} | lordo"] = np.prod(1 + np.array(rets)) ** 0.1 - 1
            pth, _ = run_nettista(rets, divs, yrs)
            rec[f"{sname} | nettista"] = (pth[-1] / 100) ** 0.1 - 1
        roll.append(rec)
    roll = pd.DataFrame(roll)

    t3.drop(columns=["d_row", "e_row", "col"]).to_csv(OUT / "AN_top3_anno.csv", index=False)
    ann.to_csv(OUT / "AN_rendimenti_annui.csv", index=False)
    res.to_csv(OUT / "AN_sintesi.csv", index=False)
    roll.to_csv(OUT / "AN_finestre_10anni.csv", index=False)
    pd.to_pickle(dict(paths=paths, ledgers=ledgers), OUT / "AN_paths.pkl")
    for k, v in ledgers.items():
        v.to_csv(OUT / f"AN_zainetto_{k.replace(' ', '_').replace(':', '').replace('%', 'pct').replace('+', 'piu')}.csv", index=False)
    json.dump(dict(proxy_sigma_reconstructed=proxy, cost=COST, amc=AMC, bollo=BOLLO, cg=CG, div_net=DIV_NET, div_wrap=DIV_WRAP,
                   stop=STOP, leaps_prem=LEAPS_PREM, leaps_weight=LEAPS_W, last_date=str(p.dates[last].date())),
              open(OUT / "AN_parametri.json", "w"), indent=1)
    pd.set_option("display.width", 250)
    show = res[res.periodo.isin(["1997-2025", "1997-2026 (YTD)", "2009-2025"])]
    print(show[["periodo", "strategia", "vista", "valore_finale", "cagr", "peggior_anno", "max_drawdown_fine_anno", "anni_sopra_SP500"]].round(3).to_string(index=False))
    print("proxy sigma", proxy)


if __name__ == "__main__":
    main()
