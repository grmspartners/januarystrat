"""Shared openpyxl styling for the GRMS workbooks (white surface, anthracite ink, bronze used sparingly)."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

INK = "2B2B2B"
BRONZE = "B5712A"
HDR_FILL = PatternFill("solid", fgColor="F3EEE6")
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
THIN = Side(style="thin", color="D9D6CF")
BOX = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
F_BASE = Font(name="Arial", size=9, color=INK)
F_BOLD = Font(name="Arial", size=9, color=INK, bold=True)
F_TITLE = Font(name="Arial", size=13, color=INK, bold=True)
F_SUB = Font(name="Arial", size=10, color=BRONZE, bold=True)
F_NOTE = Font(name="Arial", size=8, color="5A5A58", italic=True)
F_INPUT = Font(name="Arial", size=9, color="0000FF")
F_LINK = Font(name="Arial", size=9, color="008000")

PCT_KEYS = ("cagr", "rendimento", "ret", "dd", "excess", "copertura", "vol", "worst", "best", "pct", "hit", "share",
            "quota", "k_over_s", "iv", "premio", "mom", "extra", "drawdown", "peso", "aliquota", "momentum", "variazione",
            "median", "_m0", "_m1")
EUR_KEYS = ("final", "valore", "eur", "imposta", "plus", "gain", "tax", "zainetto", "capitale", "importo")
NUM2_KEYS = ("sharpe", "sortino", "calmar", "t_stat", "beta", "prezzo", "strike", "spot", "anni", "s_", "k_")


def clean_value(v):
    if isinstance(v, (np.floating,)):
        v = float(v)
    if isinstance(v, (np.integer,)):
        v = int(v)
    if isinstance(v, (np.bool_,)):
        v = bool(v)
    if isinstance(v, float) and not np.isfinite(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime().date()
    return v


def guess_format(col: str):
    c = col.lower()
    if any(k in c for k in ("anno", "year", "tranche", "pos", "rank", "n_", "numero", "mese")) and not any(
            k in c for k in ("rendimento", "ret")):
        return "0"
    if any(k in c for k in NUM2_KEYS):
        return "#,##0.00"
    if any(k in c for k in PCT_KEYS):
        return "0.0%"
    if any(k in c for k in EUR_KEYS):
        return "#,##0.00"
    return None


def write_table(ws, df: pd.DataFrame, row: int, col: int = 1, formats: dict | None = None, widths: bool = True,
                header_wrap: bool = True) -> int:
    """Write df with a styled header at (row, col). Returns the next free row."""
    formats = formats or {}
    for j, name in enumerate(df.columns):
        c = ws.cell(row=row, column=col + j, value=str(name))
        c.font, c.fill, c.border = F_BOLD, HDR_FILL, BOX
        c.alignment = Alignment(wrap_text=header_wrap, vertical="top")
    for i, rec in enumerate(df.itertuples(index=False), start=1):
        for j, v in enumerate(rec):
            c = ws.cell(row=row + i, column=col + j, value=clean_value(v))
            c.font, c.border = F_BASE, BOX
            name = str(df.columns[j])
            fmt = formats.get(name, guess_format(name))
            if fmt and isinstance(c.value, (int, float)) and not isinstance(c.value, bool):
                c.number_format = fmt
            if isinstance(c.value, (dt.date, dt.datetime)):
                c.number_format = "dd/mm/yyyy"
    if widths:
        for j, name in enumerate(df.columns):
            vals = df.iloc[:, j].astype(str)
            w = max(len(str(name)) * 0.9, vals.str.len().quantile(0.9) if len(vals) else 8)
            letter = get_column_letter(col + j)
            ws.column_dimensions[letter].width = max(ws.column_dimensions[letter].width or 0, min(48, max(9, w + 2)))
    return row + len(df) + 2


def title(ws, text: str, sub: str | None = None, row: int = 1):
    ws.cell(row=row, column=1, value=text).font = F_TITLE
    if sub:
        ws.cell(row=row + 1, column=1, value=sub).font = F_NOTE
    ws.sheet_view.showGridLines = False
    return row + 3


def para(ws, row: int, text: str, col: int = 1, font=None, merge_to: int = 10, height: float | None = None):
    c = ws.cell(row=row, column=col, value=text)
    c.font = font or F_BASE
    c.alignment = Alignment(wrap_text=True, vertical="top")
    if merge_to and merge_to > col:
        ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=merge_to)
    if height:
        ws.row_dimensions[row].height = height
    return row + 1


def sheet_from_df(wb, name: str, df: pd.DataFrame, heading: str, note: str | None = None, formats=None):
    ws = wb.create_sheet(name[:31])
    r = title(ws, heading, note)
    write_table(ws, df, r, formats=formats)
    ws.freeze_panes = ws.cell(row=r + 1, column=1)
    return ws
