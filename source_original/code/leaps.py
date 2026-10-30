"""
LEAPS pricing helpers (Black-Scholes-Merton with continuous dividend yield).

Why a model and not market prices
---------------------------------
Free historical option chains for 1990-2026 do not exist (OptionMetrics /
ORATS are paid). We therefore PRICE the LEAPS with Black-Scholes using an
implied volatility estimated from the stock's own realised volatility:

    sigma_IV = clip(RV_252d * iv_mult, 20%, 200%)   (floor = Config.leaps_iv_floor)

iv_mult captures the volatility risk premium (implied usually above realised)
and is a stress parameter: results are reported for several values, together
with the bid/ask half-spread paid on entry and exit.

Contract chosen (the rule proposed in the thread)
-------------------------------------------------
On the first trading day of the year buy the January LEAPS of the FOLLOWING
year (about 12.5 months to expiry) with the strike K such that the premium
equals `prem_frac` (default 35%) of the stock price. The maximum loss per
contract is therefore 35% of the notional controlled, by construction. The
position is sold on the last trading day of the year (about 3 weeks of time
value left), so the tax year matches the stock strategy.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm


def bs_call(S, K, T, r, q, sigma):
    """Vectorised Black-Scholes-Merton call price."""
    S = np.asarray(S, dtype=float)
    K = np.asarray(K, dtype=float)
    T = np.maximum(np.asarray(T, dtype=float), 1e-8)
    sig = np.maximum(np.asarray(sigma, dtype=float), 1e-6)
    sqT = np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sig ** 2) * T) / (sig * sqT)
    d2 = d1 - sig * sqT
    return S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def bs_delta(S, K, T, r, q, sigma):
    T = max(T, 1e-8)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return math.exp(-q * T) * norm.cdf(d1)


def strike_for_premium(S, T, r, q, sigma, prem_frac):
    """Strike K such that call(S, K) = prem_frac * S.
    Feasible only if prem_frac is below the zero-strike value S*exp(-qT)."""
    target = prem_frac * S
    f = lambda K: float(bs_call(S, K, T, r, q, sigma)) - target
    lo, hi = 1e-6 * S, 20.0 * S
    if f(lo) < 0:          # even a zero strike is cheaper than target (huge q): use deepest ITM
        return lo
    return brentq(f, lo, hi, xtol=1e-10 * S)


def third_friday(year: int, month: int = 1):
    import datetime as dt
    d = dt.date(year, month, 15)
    while d.weekday() != 4:
        d += dt.timedelta(days=1)
    return d


def realised_vol(a_col: np.ndarray, end_row: int, window: int = 252, min_obs: int = 60) -> float:
    """Annualised close-to-close volatility of log total returns over the
    `window` rows ending at end_row (inclusive). NaN-tolerant."""
    s = a_col[max(0, end_row - window):end_row + 1]
    s = s[~np.isnan(s)]
    if len(s) < min_obs:
        return float("nan")
    lr = np.diff(np.log(s))
    return float(np.std(lr, ddof=1) * math.sqrt(252))
