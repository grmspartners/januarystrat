"""
Momentum signals and point-in-time ranking.

Definition used throughout the study
------------------------------------
On a decision date d (a close), the universe is the set of index members ON d.
Each member's momentum is its TOTAL return (dividends reinvested) from the
close of the reference date d0 to the close of d:

    mom = A[d] / A[d0] - 1

For the annual rule, d0 is the last trading day of the previous year and d is
the last trading day of the current year, i.e. the calendar-year return that
financial media report as "best performing stock of the year".

A member listed after d0 (IPO / spin-off) has no price at d0. The rule
`min_days` decides whether it competes using its return since its first
print: True to the spirit of the original thread (SanDisk 2025 was ranked on
its post-spin-off return), but those returns are not comparable to full-year
returns, so the choice is a tested parameter, not a hidden assumption.

Nothing here reads data after d: no look-ahead.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from panel import Panel


def ranking(p: Panel, index: str, d_row: int, d0_row: int, min_days: int | None = 126,
            skip_rows: int = 0, cols: list[int] | None = None) -> pd.DataFrame:
    """Return a DataFrame of members on dates[d_row] sorted by momentum (desc).

    min_days: None -> only members with a price at d0 (full window);
              int  -> members listed after d0 compete if they have >= min_days
                      trading days of history at d (return measured from first print).
    skip_rows: end the window `skip_rows` trading days before d (12-1 momentum).
    """
    if cols is None:
        cols = p.members(index, p.dates[d_row])
    end = d_row - skip_rows
    out = []
    for j in cols:
        a_end = p.a[end, j]
        if np.isnan(a_end) or p.first_row[j] > end:
            continue
        if p.last_row[j] < d_row:          # stopped trading before the decision date
            continue
        fr = p.first_row[j]
        if fr <= d0_row:
            a0 = p.a[d0_row, j]
            if np.isnan(a0):
                continue
            partial = False
        else:
            if min_days is None or (end - fr) < min_days:
                continue
            a0 = p.a[fr, j]
            partial = True
        out.append((j, p.labels[j], a_end / a0 - 1.0, partial, end - max(fr, d0_row)))
    df = pd.DataFrame(out, columns=["col", "label", "mom", "partial", "days"])
    return df.sort_values("mom", ascending=False).reset_index(drop=True)


def year_end_rows(p: Panel) -> dict[int, int]:
    """Row of the last trading day of each calendar year."""
    s = pd.Series(np.arange(len(p.dates)), index=p.dates)
    g = s.groupby(p.dates.year).max()
    return g.to_dict()
