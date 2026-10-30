"""
Backtest engine for "buy last period's winner(s)" momentum rules.

One engine, every variant
-------------------------
The same code runs the rule from the original thread and all its variants:

  universe      S&P 500 / Nasdaq-100 / union, point-in-time
  rebalance     annual (default), semiannual, quarterly, monthly
  lookback      momentum window in months (12 = previous calendar year)
  top_n         how many winners to hold (equal weight at entry)
  stop          fixed stop below entry (default 35%) or trailing; intraday
                (low touches the level, fill at the level or at the open on a
                gap) or on closes
  after_stop    stay in cash until the next rebalance (thread rule) or switch
                into the period-to-date leader of the index
  instrument    the stock itself, or a LEAPS call whose premium is 35% of spot
  taxes         Italian regime amministrato (26%, 4-year loss carry-forward,
                37.1% effective on US dividends, 12.5% on T-bill interest,
                0.20% stamp duty), or "deferred" (a gross-roll-up wrapper that
                pays 26% only at the end), or none
  currency      USD (as in the thread) or EUR (an Italian investor: values and
                taxable gains measured in euro)

Timing (no look-ahead)
----------------------
Decision on the close of the last trading day of the period, using only data
up to that close. Old holdings are sold on that close. New holdings are bought
at the OPEN of the first trading day of the next period (default) or at the
decision close. During the period, stops are checked day by day using only
that day's bar. A holding whose data ends (acquisition / delisting) is sold
at its last available close and the proceeds wait in cash.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from leaps import bs_call, realised_vol, strike_for_premium, third_friday
from panel import Panel
from signals import ranking
from tax_it import TaxLedger


@dataclass
class Config:
    universe: str = "SPX"
    first_year: int = 2009            # first holding year
    first_month: int = 1              # month in which the first holding period starts
    end: str | None = None            # last date (default: last panel date)
    rebalance_m: int = 12             # holding period in months (12 annual, 6, 3, 1)
    lookback_m: int = 12              # momentum window in months
    skip_m: int = 0                   # skip the most recent month(s) (12-1 momentum)
    top_n: int = 1
    min_days: int | None = 126        # partial-window listings compete if >= this many days
    stop: float | None = 0.35         # None = no stop
    stop_type: str = "entry"          # "entry" (fixed below purchase) | "trailing"
    stop_exec: str = "intraday"       # "intraday" | "close"
    after_stop: str = "cash"          # "cash" | "leader"
    max_switches: int = 2             # per slot per period when after_stop == "leader"
    buy_at: str = "open"              # "open" (next day open) | "close" (decision close)
    keep_winners: bool = False        # do not sell & rebuy names selected again
    cost: float = 0.0010              # per side, fraction of traded value
    tax_mode: str = "realized"        # "realized" | "deferred" | "none"
    cg_tax: float = 0.26
    div_tax: float = 0.371
    carry_years: int = 4
    stamp: float = 0.002
    cash_yield: bool = True           # idle cash earns the 3m T-bill
    cash_tax: float = 0.125
    currency: str = "USD"             # "USD" | "EUR"
    instrument: str = "stock"         # "stock" | "leaps"
    leaps_prem: float = 0.35          # LEAPS premium as fraction of spot
    leaps_alloc: float = 0.35         # fraction of capital spent on premium (rest in T-bills)
    leaps_iv_mult: float = 1.10
    leaps_half_spread: float = 0.03   # paid on entry and on exit, fraction of option mid
    leaps_iv_floor: float = 0.20
    regime_filter: str | None = None  # None | "sma10": hold stocks only while the S&P 500 TR is above
                                      # its 10-month average (checked at each month-end close)
    vol_target: float | None = None   # e.g. 0.40: weight = min(1, target / realised vol 63d); rest in T-bills
    start_capital: float = 100.0
    label: str = ""

    def as_dict(self):
        return asdict(self)


@dataclass
class Position:
    col: int
    label: str
    shares: float                 # stock shares on total-return basis, or option contracts
    basis: float                  # cost basis in tax currency
    entry_ref: float              # reference level for the stop (adjusted price)
    peak: float                   # running max for trailing stops
    entry_row: int
    kind: str = "stock"           # "stock" | "leaps"
    K: float = 0.0                # LEAPS strike (on the price-index basis)
    expiry: pd.Timestamp | None = None
    sigma: float = 0.0
    q: float = 0.0
    r: float = 0.0
    switches: int = 0


class Backtest:
    def __init__(self, p: Panel, cfg: Config):
        self.p, self.c = p, cfg
        self.trades: list[dict] = []
        self.events: list[dict] = []

    # --------------------------------------------------------------- periods
    def _periods(self):
        p, c = self.p, self.c
        me = p.month_end_rows()
        me_dates = p.dates[me]
        last_row = len(p.dates) - 1 if c.end is None else p.row(c.end)
        # decision = last trading day of the month before (first_year, first_month)
        y, m = c.first_year, c.first_month - 1
        if m == 0:
            y, m = y - 1, 12
        k0 = int(np.where((me_dates.year == y) & (me_dates.month == m))[0][0])
        ks = list(range(k0, len(me), c.rebalance_m))
        out = []
        for i, k in enumerate(ks):
            d_row = me[k]
            if d_row >= last_row:
                break
            k_end = ks[i + 1] if i + 1 < len(ks) else None
            end_row = me[k_end] if k_end is not None and me[k_end] <= last_row else last_row
            k_lb = k - c.lookback_m
            if k_lb < 0:
                continue
            d0_row = me[k_lb]
            skip_rows = 0
            if c.skip_m:
                skip_rows = d_row - me[k - c.skip_m]
            out.append(dict(decision=d_row, d0=d0_row, start=d_row + 1, end=end_row, skip=skip_rows))
            if end_row == last_row:
                break
        return out

    # ----------------------------------------------------------- utilities
    def _fx(self, row):              # USD per EUR
        return self.p.usd_per_eur[row]

    def _to_tax_ccy(self, usd, row):
        return usd / self._fx(row) if self.c.currency == "EUR" else usd

    def _price_index_col(self, j):
        """Price-only index (dividends stripped) on the adjusted basis: the
        underlying that a LEAPS holder participates in."""
        if not hasattr(self, "_pi_cache"):
            self._pi_cache = {}
        if j not in self._pi_cache:
            a = self.p.a[:, j]
            dy = self.p.div_yield[:, j]
            r = np.ones_like(a)
            r[1:] = a[1:] / a[:-1] - dy[1:]
            r = np.where(np.isfinite(r), r, 1.0)
            pi = np.cumprod(r)
            pi[np.isnan(a)] = np.nan
            self._pi_cache[j] = pi
        return self._pi_cache[j]

    # -------------------------------------------------------------- selling
    def _sell(self, pos: Position, row: int, value_usd: float, reason: str):
        """Sell a position at value_usd (gross). Returns net cash after cost and tax."""
        c = self.c
        proceeds = value_usd * (1 - c.cost) if pos.kind == "stock" else value_usd
        gain = self._to_tax_ccy(proceeds, row) - pos.basis
        tax_ccy = 0.0
        if c.tax_mode == "realized":
            tax_ccy = self.ledger.realise(gain, self.p.dates[row].year)
        tax_usd = tax_ccy * self._fx(row) if c.currency == "EUR" else tax_ccy
        self.trades.append(dict(label=pos.label, kind=pos.kind, entry=self.p.dates[pos.entry_row].date(),
                                exit=self.p.dates[row].date(), reason=reason,
                                ret=proceeds / pos.cost_usd - 1 if getattr(pos, "cost_usd", 0) else np.nan,
                                gain_taxccy=gain, tax_taxccy=tax_ccy))
        return proceeds - tax_usd

    # --------------------------------------------------------------- buying
    def _buy_stock(self, j: int, row: int, cash_usd: float, at: str) -> Position:
        p, c = self.p, self.c
        px = p.ao[row, j] if at == "open" else p.a[row, j]
        if not np.isfinite(px):
            px = p.a[row, j]
        sh = cash_usd * (1 - c.cost) / px
        pos = Position(col=j, label=p.labels[j], shares=sh, basis=self._to_tax_ccy(cash_usd, row),
                       entry_ref=px, peak=px, entry_row=row)
        pos.cost_usd = cash_usd
        return pos

    def _buy_leaps(self, j: int, row: int, cash_usd: float, period_end_row: int) -> Position | None:
        p, c = self.p, self.c
        pi = self._price_index_col(j)
        S = pi[row]
        sig = realised_vol(p.a[:, j], row - 1, 252)
        if not np.isfinite(sig):
            sig = realised_vol(p.a[:, j], row - 1, 63, min_obs=20)
        if not np.isfinite(sig):
            return None
        sig = float(np.clip(sig * c.leaps_iv_mult, c.leaps_iv_floor, 2.0))
        q = float(np.nansum(p.div_yield[max(0, row - 252):row, j]))
        r = float(np.nan_to_num(p.rate_1y[row], nan=0.03))
        end_date = p.dates[period_end_row]
        exp = pd.Timestamp(third_friday(end_date.year + 1, 1))
        T = (exp - p.dates[row]).days / 365.0
        K = strike_for_premium(S, T, r, q, sig, c.leaps_prem)
        mid = float(bs_call(S, K, T, r, q, sig))
        ask = mid * (1 + c.leaps_half_spread)
        n = cash_usd / ask
        pos = Position(col=j, label=p.labels[j], shares=n, basis=self._to_tax_ccy(cash_usd, row),
                       entry_ref=S, peak=S, entry_row=row, kind="leaps", K=K, expiry=exp, sigma=sig, q=q, r=r)
        pos.cost_usd = cash_usd
        self.events.append(dict(date=p.dates[row].date(), label=p.labels[j], event="leaps_buy", S=S, K=K,
                                K_over_S=K / S, T=T, sigma=sig, mid_over_S=mid / S))
        return pos

    def _leaps_value(self, pos: Position, row: int, exit_: bool = False) -> float:
        p, c = self.p, self.c
        pi = self._price_index_col(pos.col)
        S = pi[min(row, p.last_row[pos.col])]
        T = max((pos.expiry - p.dates[row]).days / 365.0, 1e-6)
        sig = pos.sigma
        if exit_:
            rv = realised_vol(p.a[:, pos.col], row, 63, min_obs=20)
            if np.isfinite(rv):
                sig = float(np.clip(rv * c.leaps_iv_mult, c.leaps_iv_floor, 2.0))
        mid = float(bs_call(S, pos.K, T, pos.r, pos.q, sig))
        if exit_:
            return pos.shares * mid * (1 - c.leaps_half_spread)
        return pos.shares * mid

    def _pos_value(self, pos: Position, row: int) -> float:
        if pos.kind == "leaps":
            return self._leaps_value(pos, row)
        j = pos.col
        r = min(row, self.p.last_row[j])
        return pos.shares * self.p.a[r, j]

    # ------------------------------------------------------------------ run
    def run(self):
        p, c = self.p, self.c
        self.ledger = TaxLedger(rate=c.cg_tax, carry_years=c.carry_years)
        periods = self._periods()
        if not periods:
            raise ValueError("no periods")
        first = periods[0]
        start_row = first["start"]
        cash = c.start_capital * (self._fx(first["decision"]) if c.currency == "EUR" else 1.0)
        positions: list[Position] = []
        # Contributions for "deferred" mode: total invested in tax currency
        invested_taxccy = self._to_tax_ccy(cash, first["decision"])
        values = np.full(len(p.dates), np.nan)
        holdings_log = []
        year_end_rows = set(pd.Series(np.arange(len(p.dates)), index=p.dates).groupby(p.dates.year).max().values)
        n_stops = 0
        me_rows = set(p.month_end_rows())
        risk_on = None
        if c.regime_filter == "sma10":
            tr = p.series("Y_^SP500TR", "a")
            me_idx = sorted(me_rows)
            m_tr = tr.iloc[me_idx]
            sma = m_tr.rolling(10).mean()
            risk_on = {r: bool(v >= s_) for r, v, s_ in zip(me_idx, m_tr.values, sma.values) if np.isfinite(s_)}
        scheduled: list[int] = []      # columns to buy at the next open (regime re-entry)
        pending: list[int] = []        # current period's selection while risk-off

        def weight_of(j, row):
            if c.vol_target is None:
                return 1.0
            from leaps import realised_vol
            rv = realised_vol(p.a[:, j], row - 1, 63, min_obs=20)
            return 1.0 if not np.isfinite(rv) or rv <= 0 else min(1.0, c.vol_target / rv)

        for k, per in enumerate(periods):
            d, s, e = per["decision"], per["start"], per["end"]
            # ---- 1. ranking at the decision close
            if c.universe in ("SPX", "NDX", "SPX+NDX"):
                rk = ranking(p, c.universe, d, per["d0"], min_days=c.min_days, skip_rows=per["skip"])
            # A name whose data ends on the decision day (deal closing, delisting)
            # cannot be bought at the next open: skip it and take the next one.
            buy_row_chk = s if c.buy_at == "open" else d
            sel = [j for j in rk.col if p.last_row[j] >= buy_row_chk and np.isfinite(p.a[buy_row_chk, j])][:c.top_n]
            # ---- 2. sell old positions on the decision close (unless kept)
            keep = []
            for pos in positions:
                if c.keep_winners and pos.kind == "stock" and pos.col in sel:
                    keep.append(pos)
                    continue
                if pos.kind == "leaps":
                    v = self._leaps_value(pos, d, exit_=True)
                else:
                    v = self._pos_value(pos, d)
                cash += self._sell(pos, d, v, "rebalance")
            positions = keep
            # ---- 3. buy new positions
            new_cols = [j for j in sel if j not in [q.col for q in positions]]
            buy_row = s if c.buy_at == "open" else d
            at = "open" if c.buy_at == "open" else "close"
            scheduled, pending = [], []
            if risk_on is not None and not risk_on.get(d, True) and c.instrument == "stock":
                pending = list(new_cols)       # risk-off at the decision: stay in T-bills
                new_cols = []
            if c.instrument == "stock":
                if new_cols:
                    alloc = cash / len(new_cols)
                    spent = 0.0
                    for j in new_cols:
                        w = weight_of(j, buy_row)
                        positions.append(self._buy_stock(j, buy_row, alloc * w, at))
                        spent += alloc * w
                    cash -= spent
                for pos in positions:          # kept winners: reset stop reference to period start
                    if pos.entry_row < buy_row:
                        pos.entry_ref = p.a[d, pos.col]
                        pos.peak = pos.entry_ref
            else:
                total = cash
                prem_budget = total * c.leaps_alloc
                per_name = prem_budget / max(1, len(new_cols))
                spent = 0.0
                for j in new_cols:
                    lp = self._buy_leaps(j, buy_row, per_name, e)
                    if lp is not None:
                        positions.append(lp)
                        spent += per_name
                cash = total - spent
            mom_of = dict(zip(rk.col, rk.mom))
            holdings_log.append(dict(period_start=p.dates[s].date(), period_end=p.dates[e].date(),
                                     selected=[p.labels[j] for j in sel],
                                     moms=[round(float(mom_of[j]), 4) for j in sel]))
            # ---- 4. daily loop
            if c.buy_at == "close":
                values[d] = cash + sum(self._pos_value(q, d) for q in positions)
            for t in range(s, e + 1):
                # regime re-entry scheduled at the previous month-end: buy at today's open
                if scheduled:
                    alloc = cash / len(scheduled)
                    spent = 0.0
                    for j in scheduled:
                        if p.last_row[j] >= t and np.isfinite(p.a[t, j]):
                            w = weight_of(j, t)
                            positions.append(self._buy_stock(j, t, alloc * w, "open"))
                            spent += alloc * w
                    cash -= spent
                    scheduled = []
                # cash interest (net of tax), accrued daily
                if c.cash_yield and cash > 0:
                    rate = p.tbill_3m[t - 1] if np.isfinite(p.tbill_3m[t - 1]) else 0.0
                    days = (p.dates[t] - p.dates[t - 1]).days
                    cash *= 1 + rate * days / 360.0 * (1 - (c.cash_tax if c.tax_mode != "none" else 0.0))
                still = []
                for pos in positions:
                    j = pos.col
                    if pos.kind == "stock":
                        if t > p.last_row[j]:                       # data ended: acquired / delisted
                            cash += self._sell(pos, p.last_row[j], pos.shares * p.a[p.last_row[j], j], "delisted")
                            continue
                        if t == pos.entry_row and c.buy_at == "open":
                            # bought at today's open: the stop applies from the open onward
                            pass
                        # dividend tax: reduce shares, increase basis by net reinvested dividend
                        dy = p.div_yield[t, j]
                        if dy > 0 and t > pos.entry_row:
                            gross = p.a[t, j] / p.a[t - 1, j]
                            v_prev = pos.shares * p.a[t - 1, j]
                            mult = (gross - c.div_tax * dy) / gross
                            pos.shares *= mult
                            pos.basis += self._to_tax_ccy(v_prev * dy * (1 - c.div_tax), t)
                        # stop
                        if c.stop is not None:
                            ref = pos.peak if c.stop_type == "trailing" else pos.entry_ref
                            lvl = ref * (1 - c.stop)
                            hit, fill = False, None
                            if c.stop_exec == "intraday":
                                lo = p.al[t, j]
                                if np.isfinite(lo) and lo <= lvl:
                                    op = p.ao[t, j]
                                    fill = op if (np.isfinite(op) and op <= lvl and t != pos.entry_row) else lvl
                                    hit = True
                            else:
                                if p.a[t, j] <= lvl:
                                    fill, hit = p.a[t, j], True
                            if hit:
                                n_stops += 1
                                proceeds = self._sell(pos, t, pos.shares * fill, "stop")
                                self.events.append(dict(date=p.dates[t].date(), label=pos.label, event="stop",
                                                        level=lvl / pos.entry_ref - 1))
                                if c.after_stop == "leader" and pos.switches < c.max_switches and t + 1 <= e - 5:
                                    rk2 = ranking(p, c.universe, t, d, min_days=c.min_days)
                                    held = {q.col for q in positions} | {pos.col}
                                    cand = [jj for jj in rk2.col if jj not in held and p.last_row[jj] >= t + 1
                                            and np.isfinite(p.a[t + 1, jj])]
                                    if cand:
                                        newp = self._buy_stock(cand[0], t + 1, proceeds, "open")
                                        newp.switches = pos.switches + 1
                                        self.events.append(dict(date=p.dates[t + 1].date(), label=newp.label,
                                                                event="switch_in"))
                                        still.append(newp)
                                        continue
                                cash += proceeds
                                continue
                            if c.stop_type == "trailing":
                                pos.peak = max(pos.peak, p.a[t, j])
                        still.append(pos)
                    else:  # LEAPS
                        if t > p.last_row[j]:
                            v = self._leaps_value(pos, p.last_row[j], exit_=True)
                            cash += self._sell(pos, p.last_row[j], v, "delisted")
                            continue
                        still.append(pos)
                positions = still
                # regime filter at month-end closes inside the period
                if risk_on is not None and t in me_rows and t < e and c.instrument == "stock":
                    on = risk_on.get(t, True)
                    if not on and positions:
                        pending = [q.col for q in positions]
                        for q in positions:
                            cash += self._sell(q, t, self._pos_value(q, t), "regime")
                        positions = []
                        self.events.append(dict(date=p.dates[t].date(), label="*", event="regime_off"))
                    elif on and not positions and pending:
                        scheduled = list(pending)
                        pending = []
                        self.events.append(dict(date=p.dates[t].date(), label="*", event="regime_on"))
                # stamp duty on the year-end close (on total value of the dossier)
                if c.stamp and t in year_end_rows and c.tax_mode != "none":
                    tot = cash + sum(self._pos_value(q, t) for q in positions)
                    duty = c.stamp * tot
                    if tot > 0:
                        f = 1 - duty / tot
                        cash *= f
                        for q in positions:
                            q.shares *= f
                values[t] = cash + sum(self._pos_value(q, t) for q in positions)
                if not np.isfinite(values[t]):
                    raise RuntimeError(f"non-finite portfolio value on {p.dates[t].date()}: "
                                       f"{[(q.label, q.shares) for q in positions]}, cash={cash}")

        # ---- final liquidation value (tax on unrealised gains as if sold on the last day)
        last = periods[-1]["end"]
        gross_val = values[last]
        liq_tax_ccy = 0.0
        if c.tax_mode == "realized":
            led = self.ledger
            yr = p.dates[last].year
            tmp = TaxLedger(rate=led.rate, carry_years=led.carry_years, losses=[x[:] for x in led.losses])
            for pos in positions:
                v = self._leaps_value(pos, last, exit_=True) if pos.kind == "leaps" else self._pos_value(pos, last) * (1 - c.cost)
                liq_tax_ccy += tmp.realise(self._to_tax_ccy(v, last) - pos.basis, yr)
        elif c.tax_mode == "deferred":
            final_ccy = self._to_tax_ccy(gross_val, last)
            liq_tax_ccy = max(0.0, final_ccy - invested_taxccy) * c.cg_tax
        liq_tax_usd = liq_tax_ccy * (self._fx(last) if c.currency == "EUR" else 1.0)

        v = pd.Series(values, index=p.dates).dropna()
        if c.currency == "EUR":
            v = v / pd.Series(p.usd_per_eur, index=p.dates).reindex(v.index)
            liq_tax = liq_tax_ccy
        else:
            liq_tax = liq_tax_usd
        self.result = dict(
            equity=v,
            final=float(v.iloc[-1]),
            final_after_liq=float(v.iloc[-1] - liq_tax),
            start=c.start_capital,
            tax_paid=self.ledger.paid,
            losses_wasted=self.ledger.wasted,
            losses_unused_end=self.ledger.available(p.dates[last].year),
            tax_history=pd.DataFrame(self.ledger.history),
            liq_tax=liq_tax,
            n_stops=n_stops,
            holdings=pd.DataFrame(holdings_log),
            trades=pd.DataFrame(self.trades),
            events=pd.DataFrame(self.events),
            first_date=v.index[0], last_date=v.index[-1],
        )
        return self.result


def run(p: Panel, **kw) -> dict:
    return Backtest(p, Config(**kw)).run()
