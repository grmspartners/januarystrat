"""
Italian tax ledger for a retail investor in "regime amministrato".

What it models
--------------
* Capital gains on shares and options are "redditi diversi" (art. 67 TUIR),
  taxed at 26% at each disposal (the intermediary withholds the tax).
* Capital losses (minusvalenze) are credited to the "zainetto fiscale" and can
  offset redditi diversi realised in the same year and in the following four
  tax years (art. 68 c.5 TUIR). Unused losses expire on 31 December of the
  fourth year after realisation. Offsetting is applied oldest-first, the way
  intermediaries apply it, so the losses closest to expiry are used first.
* Gains on harmonised funds / ETFs are "redditi di capitale" (art. 44 TUIR):
  they are taxed at 26% and CANNOT absorb prior minusvalenze. Losses on ETFs
  are redditi diversi: they CAN offset future gains on shares, options, ETCs,
  but not future ETF gains. The `etf` flag reproduces this asymmetry.

Amounts are in the currency the caller chooses (USD or EUR): for an Italian
resident the legally relevant currency is EUR, so the engine passes EUR
amounts when it runs in EUR mode.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaxLedger:
    rate: float = 0.26
    carry_years: int = 4
    losses: list = field(default_factory=list)   # list of [amount, expiry_year]
    paid: float = 0.0                            # cumulative tax paid
    wasted: float = 0.0                          # losses that expired unused
    used: float = 0.0                            # losses actually used
    history: list = field(default_factory=list)  # one record per realisation (for the "zainetto" report)

    def _expire(self, year: int):
        keep = []
        for amt, exp in self.losses:
            if exp < year:
                self.wasted += amt
            else:
                keep.append([amt, exp])
        self.losses = keep

    def realise(self, gain: float, year: int, etf: bool = False) -> float:
        """Register a realised gain (>0) or loss (<0) in `year`.
        Returns the tax due now (>= 0)."""
        w0 = self.wasted
        self._expire(year)
        if gain <= 0:
            if gain < 0:
                self.losses.append([-gain, year + self.carry_years])
            self.history.append(dict(year=year, gain=gain, offset=0.0, taxable=0.0, tax=0.0, etf=etf,
                                     expired=self.wasted - w0, zainetto_after=self.available(year)))
            return 0.0
        taxable = gain
        if not etf:                                # ETF gains cannot absorb losses
            self.losses.sort(key=lambda x: x[1])   # oldest (closest to expiry) first
            for item in self.losses:
                if taxable <= 0:
                    break
                use = min(item[0], taxable)
                item[0] -= use
                taxable -= use
                self.used += use
            self.losses = [x for x in self.losses if x[0] > 1e-12]
        tax = self.rate * taxable
        self.paid += tax
        self.history.append(dict(year=year, gain=gain, offset=gain - taxable, taxable=taxable, tax=tax, etf=etf,
                                 expired=self.wasted - w0, zainetto_after=self.available(year)))
        return tax

    def available(self, year: int) -> float:
        return sum(a for a, e in self.losses if e >= year)

    def preview_tax(self, gain: float, year: int, etf: bool = False) -> float:
        """Tax that WOULD be due on `gain` without changing the ledger
        (used to compute after-tax liquidation value at the end of a test)."""
        if gain <= 0:
            return 0.0
        if etf:
            return self.rate * gain
        avail = sum(a for a, e in self.losses if e >= year)
        return self.rate * max(0.0, gain - avail)
