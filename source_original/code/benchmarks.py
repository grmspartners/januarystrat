"""
Benchmarks with the correct Italian tax treatment of an index ETF.

Investment vehicle assumed: a UCITS ACCUMULATING ETF (what an Italian investor
can actually buy; US-domiciled SPY/QQQ are not purchasable as PRIIPs/KID rules
apply). Index return = total return net of the 15% US withholding suffered by
the fund on dividends, minus the TER.

Tax regimes
-----------
* "bh"        buy & hold: 26% only at the end on the total gain (capital income).
* "annual"    sell on the last trading day of each year and buy back on the
              first day of the next (the thread's comparison). Gains taxed 26%
              every year. Losses are minusvalenze that CANNOT offset future ETF
              gains (redditi di capitale) -> they are recorded and wasted.
* "annual_sym" the same but letting losses offset future gains, i.e. what the
              investor WOULD get with a direct basket of shares. Shows the cost
              of the Italian asymmetry.
* "none"      gross, no taxes, no stamp duty.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from panel import Panel
from tax_it import TaxLedger


def index_tr(p: Panel, which: str = "SPX", ter: float = 0.0007, wht: float = 0.15) -> pd.Series:
    """Daily total-return index of the ETF (net of fund-level withholding and TER)."""
    if which == "SPX":
        tr = p.series("Y_^SP500TR", "a")
        spy_c = p.series("Y_SPY", "c")
        spy_d = pd.Series(p.div[:, p.col("Y_SPY")], index=p.dates)
        dy = (spy_d / spy_c.shift(1)).fillna(0.0)
        r = tr.pct_change()
    elif which == "NDX":
        px = p.series("Y_^NDX", "c")
        q_c = p.series("Y_QQQ", "c")
        q_d = pd.Series(p.div[:, p.col("Y_QQQ")], index=p.dates)
        dy = (q_d / q_c.shift(1)).fillna(0.0)
        r = px.pct_change() + dy          # gross TR proxy
    else:
        raise ValueError(which)
    days = pd.Series(p.dates, index=p.dates).diff().dt.days.fillna(1)
    r_net = r - wht * dy - ter * days / 365.0
    idx = (1 + r_net.fillna(0.0)).cumprod()
    idx[r.isna() & (idx.index < r.first_valid_index())] = np.nan
    return idx


def run_benchmark(p: Panel, which="SPX", first_year=2009, end=None, regime="bh", currency="USD",
                  stamp=0.002, cost=0.0010, ter=None, cg_tax=0.26, start_capital=100.0):
    if ter is None:
        ter = 0.0007 if which == "SPX" else 0.0030
    idx = index_tr(p, which, ter=ter)
    ye = pd.Series(np.arange(len(p.dates)), index=p.dates).groupby(p.dates.year).max()
    d0 = int(ye.loc[first_year - 1])
    last = len(p.dates) - 1 if end is None else p.row(end)
    fx = pd.Series(p.usd_per_eur, index=p.dates)
    ccy = (lambda usd, row: usd / fx.iloc[row]) if currency == "EUR" else (lambda usd, row: usd)
    ledger = TaxLedger(rate=cg_tax)
    val = start_capital * (fx.iloc[d0] if currency == "EUR" else 1.0)
    val *= (1 - cost)
    basis = ccy(start_capital * (fx.iloc[d0] if currency == "EUR" else 1.0), d0)
    invested = basis
    out = {}
    ye_rows = set(ye.values)
    for t in range(d0 + 1, last + 1):
        val *= idx.iloc[t] / idx.iloc[t - 1]
        if t in ye_rows and t < last:
            if regime in ("annual", "annual_sym"):
                proceeds = val * (1 - cost)
                gain = ccy(proceeds, t) - basis
                tax = ledger.realise(gain, p.dates[t].year, etf=(regime == "annual"))
                if regime == "annual" and gain < 0:
                    pass  # recorded in the ledger but unusable against ETF gains
                tax_usd = tax * (fx.iloc[t] if currency == "EUR" else 1.0)
                val = (proceeds - tax_usd) * (1 - cost)
                basis = ccy(proceeds - tax_usd, t)
            if regime != "none" and stamp:
                val *= 1 - stamp
        out[p.dates[t]] = val
    v = pd.Series(out)
    final = v.iloc[-1]
    if regime == "none":
        liq = 0.0
    else:
        gain = ccy(final * (1 - cost), last) - basis
        liq = max(0.0, gain) * cg_tax
        liq = liq * (fx.iloc[last] if currency == "EUR" else 1.0)
    if currency == "EUR":
        v = v / fx.reindex(v.index)
        final_after = v.iloc[-1] - liq / fx.iloc[last]
    else:
        final_after = final - liq
    s0 = pd.Series({p.dates[d0]: start_capital})
    v = pd.concat([s0, v])
    return dict(equity=v, final=float(v.iloc[-1]), final_after_liq=float(final_after),
                tax_paid=ledger.paid, losses_wasted=ledger.wasted + (ledger.available(9999) if regime == "annual" else 0))
