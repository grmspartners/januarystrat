"""
Panel: fast, read-only access to the aligned daily data built by data_layer.py,
plus point-in-time index membership and the market/rate series every engine
needs.

All arrays are [n_dates x n_labels] numpy float64. Index 0 is 1988-01-04.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from config import PROC
from data_layer import load_fred


@dataclass
class Panel:
    dates: pd.DatetimeIndex
    labels: np.ndarray
    o: np.ndarray          # split-adjusted open
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray          # split-adjusted close
    a: np.ndarray          # total-return adjusted close (splits + dividends + spin-offs)
    div: np.ndarray        # cash dividend per share on the split-adjusted basis (0 if none)
    vol: np.ndarray
    meta: dict
    spx: pd.DataFrame      # membership intervals: ticker(label), start, end
    ndx: pd.DataFrame      # membership intervals: ticker, start, end, label
    fred: pd.DataFrame = field(repr=False, default=None)
    lab_idx: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ load
    @classmethod
    def load(cls) -> "Panel":
        z = np.load(PROC / "panel.npz", allow_pickle=False)
        dates = pd.DatetimeIndex(z["dates"].astype("datetime64[D]"))
        labels = z["labels"]
        p = cls(dates=dates, labels=labels, o=z["open"], h=z["high"], l=z["low"], c=z["close"],
                a=z["adj_close"], div=z["dividends"], vol=z["volume"],
                meta=json.load(open(PROC / "labels.json")),
                spx=pd.read_parquet(PROC / "spx_intervals.parquet"),
                ndx=pd.read_parquet(PROC / "ndx_intervals_resolved.parquet"))
        p.lab_idx = {k: i for i, k in enumerate(labels)}
        p.fred = load_fred()
        p._derive()
        return p

    # Labels whose price history fails identity checks (wrong company / corrupted
    # stitch). Documented in the data audit.
    QUARANTINE = {
        "SNT-199910",   # Sonat Inc.: series trades at $3-11 in 1996 vs ~$40-50 actual -> wrong security
    }

    def _repair_adjustments(self):
        """Repair 'phantom' corporate-action adjustments.

        On a clean series the daily total return (from adj_close) equals the
        price return plus the dividend yield, after correcting for any split.
        Some recovered series (Tiingo / WIKI stitches) carry adjustment errors:
        e.g. USB-200102 shows +198% total return on 1997-01-16 while its close
        is flat. Rule: where |adj_ret - close_ret - div_yield| > 15%, replace the
        day's total return with the most conservative explanation, i.e. the
        candidate with the smallest absolute value among
          * the vendor's adjusted return,
          * the raw price return + dividend yield (no corporate action),
          * the price return corrected by a standard split ratio + dividend yield.
        Every repaired cell is logged (self.repairs) for the audit trail.
        """
        A, C = self.a, self.c
        ra = A[1:] / A[:-1] - 1.0
        rc = C[1:] / C[:-1] - 1.0
        prev_c = C[:-1]
        with np.errstate(invalid="ignore", divide="ignore"):
            dy = np.where(self.div[1:] > 0, self.div[1:] / prev_c, 0.0)
        dy = np.nan_to_num(dy)
        gap = ra - rc - dy
        flag = np.abs(np.nan_to_num(gap)) > 0.15
        ratios = np.array([1.25, 4 / 3, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 10, 15, 20, 1 / 2, 1 / 3, 1 / 4,
                           1 / 5, 1 / 8, 1 / 10, 1 / 15, 1 / 20, 1 / 25, 1 / 50, 1 / 100, 1 / 200])
        log = []
        ii, jj = np.where(flag)
        new_r = ra.copy()
        for i, j in zip(ii, jj):
            cands = [ra[i, j], rc[i, j] + dy[i, j]]
            cands += list((1 + rc[i, j]) * ratios - 1 + dy[i, j])
            best = min(cands, key=lambda x: abs(x) if np.isfinite(x) else 9e9)
            if abs(best - ra[i, j]) > 1e-9:
                log.append((self.labels[j], str(self.dates[i + 1].date()), float(ra[i, j]), float(best)))
                new_r[i, j] = best
        # rebuild adj_close from the repaired returns, anchored at the last valid price
        for j in sorted({c for _, c in zip(ii, jj)}):
            col = A[:, j]
            ok = np.where(~np.isnan(col))[0]
            if len(ok) < 2:
                continue
            a0, a1 = ok[0], ok[-1]
            r = new_r[a0:a1, j]
            r = np.where(np.isfinite(r), r, 0.0)
            lvl = np.concatenate([[1.0], np.cumprod(1 + r)])
            lvl = lvl / lvl[-1] * col[a1]
            A[a0:a1 + 1, j] = lvl
        self.repairs = pd.DataFrame(log, columns=["label", "date", "vendor_ret", "repaired_ret"])

    def _derive(self):
        for lab in self.QUARANTINE:
            if lab in self.lab_idx:
                j = self.lab_idx[lab]
                for arr in (self.o, self.h, self.l, self.c, self.a):
                    arr[:, j] = np.nan
                self.div[:, j] = 0.0
        self._repair_adjustments()
        # Adjustment factor converts split-adjusted OHLC to total-return basis.
        with np.errstate(invalid="ignore", divide="ignore"):
            f = self.a / self.c
        self.adj_factor = f
        self.ao = self.o * f
        self.ah = self.h * f
        self.al = self.l * f
        # Daily dividend yield on the split-adjusted basis (for dividend tax).
        prev_c = np.vstack([np.full((1, self.c.shape[1]), np.nan), self.c[:-1]])
        with np.errstate(invalid="ignore", divide="ignore"):
            self.div_yield = np.where(self.div > 0, self.div / prev_c, 0.0)
        self.div_yield = np.nan_to_num(self.div_yield, nan=0.0)
        # first / last valid row per label
        valid = ~np.isnan(self.a)
        n = len(self.dates)
        self.first_row = np.where(valid.any(0), valid.argmax(0), n)
        self.last_row = np.where(valid.any(0), n - 1 - valid[::-1].argmax(0), -1)
        # Daily cash rate: 3m T-bill (discount basis -> approx. simple yield), ffilled.
        tb = self.fred["DTB3"].reindex(self.dates.union(self.fred.index)).ffill().reindex(self.dates)
        self.tbill_3m = (tb / 100.0).values
        y1 = self.fred["DTB1YR"].combine_first(self.fred["DGS1"]) if "DTB1YR" in self.fred else self.fred["DGS1"]
        self.rate_1y = (y1.reindex(self.dates.union(y1.index)).ffill().reindex(self.dates) / 100.0).values
        fx = self.fred["DEXUSEU"]               # USD per 1 EUR, daily since 1999
        # Pre-1999: synthetic EUR from the Deutsche Mark monthly average
        # (1 EUR = 1.95583 DEM, fixed conversion rate of 31-Dec-1998).
        dem = self.fred["EXGEUS"].dropna()      # DEM per USD, monthly
        synth = (1.95583 / dem)
        synth.index = synth.index + pd.offsets.MonthEnd(0)
        fx_all = fx.combine_first(synth[synth.index < "1999-01-01"])
        self.usd_per_eur = fx_all.reindex(self.dates.union(fx_all.index)).ffill().reindex(self.dates).values

    # --------------------------------------------------------------- helpers
    def row(self, d) -> int:
        """Row index of the last trading day <= d."""
        return int(self.dates.searchsorted(pd.Timestamp(d), side="right") - 1)

    def col(self, label: str) -> int:
        return self.lab_idx[label]

    def series(self, label: str, field_: str = "a") -> pd.Series:
        return pd.Series(getattr(self, field_)[:, self.col(label)], index=self.dates)

    def month_end_rows(self) -> np.ndarray:
        """Rows of the last trading day of every calendar month."""
        s = pd.Series(np.arange(len(self.dates)), index=self.dates)
        return s.groupby([self.dates.year, self.dates.month]).max().values

    def members(self, index: str, d) -> list[int]:
        """Column indices of index members on date d (point-in-time).
        index in {"SPX", "NDX", "SPX+NDX"}."""
        d = pd.Timestamp(d)
        cols = set()
        if index in ("SPX", "SPX+NDX"):
            m = self.spx
            sel = m[(m.start <= d) & (m.end.isna() | (m.end > d))]
            cols |= {self.lab_idx[t] for t in sel.ticker if t in self.lab_idx}
        if index in ("NDX", "SPX+NDX"):
            m = self.ndx
            sel = m[(m.start <= d) & (m.end.isna() | (m.end > d)) & m.label.notna()]
            cols |= {self.lab_idx[t] for t in sel.label if t in self.lab_idx}
        return sorted(cols)

    def members_count(self, index: str, d) -> int:
        """Number of members on d INCLUDING those with no price data at all."""
        d = pd.Timestamp(d)
        n = 0
        if index in ("SPX", "SPX+NDX"):
            m = self.spx
            n += int(((m.start <= d) & (m.end.isna() | (m.end > d))).sum())
        if index in ("NDX", "SPX+NDX"):
            m = self.ndx
            n += int(((m.start <= d) & (m.end.isna() | (m.end > d))).sum())
        return n
