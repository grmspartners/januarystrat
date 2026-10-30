"""
Survivorship patches for the S&P 500, 1996-2008 ("titoli spariti").

Free data cannot price every company that later left the market (acquired,
merged, bankrupt). For the ANNUAL calendar-year rule the top-3 of every year
1996-2008 was checked against independent, citable sources:
  * S&P Dow Jones Indices list of the 50 best one-year returns 1980-2022
    (price returns; via Visual Capitalist / Voronoi);
  * year-end reviews by CNN/Money, Forbes, Plansponsor;
  * the total-shareholder-return tables (S&P IMS / Research Data Group data,
    dividends reinvested) that each company files in its proxy statement
    (Form DEF 14A), and the quarterly high/low price tables of its 10-K, on
    SEC EDGAR.
Every winner that is an index member on 31 December but has no price data is
added back as a synthetic security that reproduces (a) the ranking-year total
return and (b) the holding-year outcome, including whether a 35% stop would
have been hit (from the quarterly lows of the 10-K).

These synthetic series are exact only for the ANNUAL January rule. For other
formation months they are log-linear interpolations of the annual figures
(documented limitation).

| rank yr | company | rank-yr TR | hold yr | hold-yr TR | 35% stop in hold yr | sources |
|---|---|---|---|---|---|---|
| 1999 | Sprint PCS (PCS) | +343.2% | 2000 | -60.1% | hit in Q3-2000 (low 27.81 vs ~33.3) | Sprint DEF 14A 2001 TSR; Sprint 10-K 2000 |
| 1999 | Nextel (NXTL) | +336.5% | 2000 | -52.0% | hit in Q4-2000 (low 23.00 vs ~33.5) | Nextel DEF 14A 2002 TSR; Nextel 10-K 2000 |
| 2000 | Reebok (RBK) | +234% (price, S&P DJI) | 2001 | ~-3% [TO VERIFY: -8.6%..-1.4%] | not hit (low 18.50 vs ~17.8) | S&P DJI list; Reebok 10-K 2001/2002 |
| 2000 | Dynegy (DYN) | +220.2% | 2001 | -54.2% | hit in Q3-2001 (low 31.27 vs ~36.4) | Dynegy DEF 14A 2002/2005; 10-K 2001 |
| 2002 | Providian (PVN) | +82.8% | 2003 | +79.4% | not hit (low 5.25 vs ~4.2) | Providian DEF 14A 2004/2005; 10-K 2003 |
| 2003 | Avaya (AV) | +428% (price) | 2004 | ~+33% [TO VERIFY] | not hit (low 11.95 vs ~8.4) | Forbes 5-Jan-2004 / S&P DJI; Avaya 10-K FY2004-05 |
| 2003 | Dynegy (DYN) | +262.6% | 2004 | +7.9% | not hit (closing low 3.46 vs ~2.8) | Dynegy DEF 14A 2005; 10-K 2004 |
| 2004 | TXU Corp. (TXU) | +178% (rounded) | 2005 | +59.9% (rounded) | not hit (low 30.22 vs ~21.0, split-adj.) | TXU DEF 14A 2006; 10-K 2005 |
| 2008 | UST Inc. (UST) | +26.6% (price) | 2009 | ~0% (cash-out 6-Jan-2009 at $69.50) | n.a. | CNN 31-Dec-2008; Altria 8-K Jan-2009 |

Reconciliation note (Dynegy 2000): S&P DJI lists +361%, the company's own
S&P IMS total-return table +220.2%. The 10-K price table (adjusted for the
0.69 exchange ratio of the Feb-2000 Illinova merger) shows a Q1-2000 low of
$17.30, consistent with +220% and not with +361% (which matches the
unadjusted pre-merger share). +220.2% is used; with it Reebok (+234%) is the
true 2000 leader on a total-return basis.

Known members still missing below the top-3: LSI Logic (1999, +319%),
Novell (2003, +215%). Nortel Networks (1999, +304%) is in the S&P DJI list
but absent from the point-in-time membership file used here.

Stop dates inside the quarter are not observable from quarterly tables; the
stop is assumed to fill exactly at the stop level (-35%) on the date shown.
A gap below the level would make the outcome worse (sensitivity in the report).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PATCHES = [
    dict(label="PATCH_PCS-2000", name="Sprint PCS Group", rank_year=1999, rank_tr=3.432, hold_tr=-0.601,
         stop_date="2000-09-15", member_from="1998-11-24", end_date=None),
    dict(label="PATCH_NXTL-2000", name="Nextel Communications", rank_year=1999, rank_tr=3.365, hold_tr=-0.520,
         stop_date="2000-11-10", member_from="1998-04-01", end_date=None),
    dict(label="PATCH_RBK-2001", name="Reebok International", rank_year=2000, rank_tr=2.34, hold_tr=-0.031,
         stop_date=None, member_from="1996-01-02", end_date=None),
    dict(label="PATCH_DYN-2001", name="Dynegy", rank_year=2000, rank_tr=2.202, hold_tr=-0.542,
         stop_date="2001-09-17", member_from="2000-10-03", end_date=None),
    dict(label="PATCH_PVN-2003", name="Providian Financial", rank_year=2002, rank_tr=0.828, hold_tr=0.794,
         stop_date=None, member_from="1997-06-11", end_date=None),
    dict(label="PATCH_AV-2004", name="Avaya", rank_year=2003, rank_tr=4.28, hold_tr=0.33,
         stop_date=None, member_from="2000-10-02", end_date=None),
    dict(label="PATCH_DYN-2004", name="Dynegy", rank_year=2003, rank_tr=2.626, hold_tr=0.079,
         stop_date=None, member_from="2002-01-02", end_date=None),
    dict(label="PATCH_TXU-2005", name="TXU Corp.", rank_year=2004, rank_tr=1.78, hold_tr=0.599,
         stop_date=None, member_from="1996-01-02", end_date=None),
    dict(label="PATCH_UST-2009", name="UST Inc.", rank_year=2008, rank_tr=0.266, hold_tr=0.0,
         stop_date=None, member_from="1996-01-02", end_date="2009-01-06"),
]


def apply(p, stop=0.35, avaya_hold=None, reebok_hold=None):
    """Append synthetic columns to Panel p (in place) and their membership."""
    ye = pd.Series(np.arange(len(p.dates)), index=p.dates).groupby(p.dates.year).max()
    new_cols = []
    for pt in PATCHES:
        hold_tr = pt["hold_tr"]
        if pt["label"] == "PATCH_AV-2004" and avaya_hold is not None:
            hold_tr = avaya_hold
        if pt["label"] == "PATCH_RBK-2001" and reebok_hold is not None:
            hold_tr = reebok_hold
        r0, r1, r2 = int(ye[pt["rank_year"] - 1]), int(ye[pt["rank_year"]]), int(ye[pt["rank_year"] + 1])
        if pt["end_date"]:
            r2 = int(p.dates.searchsorted(pd.Timestamp(pt["end_date"])))
        a = np.full(len(p.dates), np.nan)
        n1 = r1 - r0
        a[r0:r1 + 1] = (1 + pt["rank_tr"]) ** (np.arange(n1 + 1) / n1)
        base = a[r1]
        n2 = max(1, r2 - r1)
        if pt["stop_date"] is None:
            a[r1:r2 + 1] = base * (1 + hold_tr) ** (np.arange(n2 + 1) / n2)
        else:
            sd = int(p.dates.searchsorted(pd.Timestamp(pt["stop_date"])))
            k = sd - r1
            lvl = 1 - stop
            a[r1:sd + 1] = base * lvl ** (np.arange(k + 1) / k) * 1.0001   # stays just above the level
            a[sd] = base * lvl * 0.9999                                    # touches the level on the stop day
            rem = r2 - sd
            a[sd:r2 + 1] = base * lvl * ((1 + hold_tr) / lvl) ** (np.arange(rem + 1) / rem)
        new_cols.append((pt, a))
    for arr_name in ["o", "h", "l", "c", "a", "div", "vol"]:
        arr = getattr(p, arr_name)
        add = []
        for pt, a in new_cols:
            if arr_name == "o":
                col = np.r_[np.nan, a[:-1]]          # open = previous close -> stop fills at the level
                col[np.isnan(a)] = np.nan
            elif arr_name == "div":
                col = np.zeros_like(a)
            elif arr_name == "vol":
                col = np.where(np.isnan(a), np.nan, 1e6)
            else:
                col = a.copy()
            add.append(col)
        setattr(p, arr_name, np.column_stack([arr] + add))
    p.labels = np.concatenate([p.labels, [pt["label"] for pt, _ in new_cols]])
    p.lab_idx = {k: i for i, k in enumerate(p.labels)}
    rows = []
    for pt, a in new_cols:
        ok = np.where(~np.isnan(a))[0]
        p.meta[pt["label"]] = {"src": "patch", "first": str(p.dates[ok[0]].date()), "last": str(p.dates[ok[-1]].date())}
        rows.append(dict(ticker=pt["label"], start=pd.Timestamp(pt["member_from"]),
                         end=p.dates[ok[-1]] + pd.Timedelta(days=1)))
    p.spx = pd.concat([p.spx, pd.DataFrame(rows)], ignore_index=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        f = p.a / p.c
    p.adj_factor = f
    p.ao, p.ah, p.al = p.o * f, p.h * f, p.l * f
    prev_c = np.vstack([np.full((1, p.c.shape[1]), np.nan), p.c[:-1]])
    with np.errstate(invalid="ignore", divide="ignore"):
        p.div_yield = np.nan_to_num(np.where(p.div > 0, p.div / prev_c, 0.0), nan=0.0)
    valid = ~np.isnan(p.a)
    n = len(p.dates)
    p.first_row = np.where(valid.any(0), valid.argmax(0), n)
    p.last_row = np.where(valid.any(0), n - 1 - valid[::-1].argmax(0), -1)
    return p
