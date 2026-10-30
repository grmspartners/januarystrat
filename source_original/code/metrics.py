"""
Performance statistics. Every figure is computed from a daily equity curve
(value of the portfolio in its reporting currency) so that all strategies and
benchmarks are measured identically.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats


def annual_returns(eq: pd.Series) -> pd.Series:
    ye = eq.groupby(eq.index.year).last()
    first = eq.iloc[0]
    prev = pd.concat([pd.Series([first], index=[ye.index[0] - 1]), ye.iloc[:-1]])
    prev.index = ye.index
    return ye / prev.values - 1


def max_drawdown(eq: pd.Series):
    peak = eq.cummax()
    dd = eq / peak - 1
    trough = dd.idxmin()
    start = eq.loc[:trough].idxmax()
    rec = eq.loc[trough:]
    recovered = rec[rec >= eq.loc[start]]
    end = recovered.index[0] if len(recovered) else None
    return float(dd.min()), start, trough, end


def summary(eq: pd.Series, rf_daily: pd.Series | None = None, final_after_liq: float | None = None,
            start_capital: float | None = None) -> dict:
    eq = eq.dropna()
    s0 = start_capital if start_capital is not None else eq.iloc[0]
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    final = eq.iloc[-1]
    cagr = (final / s0) ** (1 / years) - 1
    r = eq.pct_change().dropna()
    vol = r.std() * math.sqrt(252)
    if rf_daily is not None:
        ex = r - rf_daily.reindex(r.index).fillna(0.0)
    else:
        ex = r
    sharpe = ex.mean() / r.std() * math.sqrt(252) if r.std() > 0 else np.nan
    down = r[r < 0]
    sortino = ex.mean() / down.std() * math.sqrt(252) if len(down) > 1 else np.nan
    mdd, pk, tr, rc = max_drawdown(eq)
    ar = annual_returns(eq)
    out = dict(final=final, multiple=final / s0, cagr=cagr, vol=vol, sharpe=sharpe, sortino=sortino,
               max_dd=mdd, dd_peak=pk.date(), dd_trough=tr.date(), dd_recovery=rc.date() if rc is not None else None,
               calmar=cagr / abs(mdd) if mdd < 0 else np.nan, worst_year=ar.min(), best_year=ar.max(),
               pct_pos_years=(ar > 0).mean(), years=years, skew_daily=stats.skew(r), kurt_daily=stats.kurtosis(r))
    if final_after_liq is not None:
        out["final_after_liq"] = final_after_liq
        out["cagr_after_liq"] = (final_after_liq / s0) ** (1 / years) - 1
    return out


def probabilistic_sharpe(sr_hat: float, n: int, skew: float, kurt_excess: float, sr_bench: float = 0.0) -> float:
    """Bailey & Lopez de Prado (2012) PSR: P(true SR > sr_bench) given the
    sample SR (per-period, not annualised), n observations, skewness and
    EXCESS kurtosis of the returns."""
    num = (sr_hat - sr_bench) * math.sqrt(n - 1)
    den = math.sqrt(1 - skew * sr_hat + (kurt_excess) / 4 * sr_hat ** 2)
    return float(stats.norm.cdf(num / den))


def deflated_sharpe(sr_hat: float, n: int, skew: float, kurt_excess: float, sr_trials: np.ndarray) -> float:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014): PSR against the
    expected maximum SR of N independent trials with the observed dispersion
    of trial Sharpe ratios (all per-period)."""
    N = len(sr_trials)
    v = np.var(sr_trials, ddof=1)
    em = 0.5772156649
    sr0 = math.sqrt(v) * ((1 - em) * stats.norm.ppf(1 - 1 / N) + em * stats.norm.ppf(1 - 1 / (N * math.e)))
    return probabilistic_sharpe(sr_hat, n, skew, kurt_excess, sr0)
