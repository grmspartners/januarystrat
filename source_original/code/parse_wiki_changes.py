"""Parse the Wikipedia 'Historical components of the S&P 500' changes table
(wikitext saved on 12-Oct-2026) into data/processed/wiki_sp500_changes.csv:
date, added ticker/name, removed ticker/name, reason (as written by Wikipedia editors,
with references to S&P DJI press releases / newspapers in the source page)."""
from __future__ import annotations

import re

import pandas as pd

from config import PROC, RAW

SRC = RAW / "wiki_sp500_historical_components.wikitext"


def clean(x: str) -> str:
    x = re.sub(r"<ref[^>]*/>", "", x)
    x = re.sub(r"<ref[^>]*>.*?</ref>", "", x, flags=re.S)
    x = re.sub(r"\{\{[^{}]*\}\}", "", x)
    x = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", x)
    x = re.sub(r"\[https?://\S+ ([^\]]*)\]", r"\1", x)
    x = re.sub(r"'''?", "", x)
    return re.sub(r"\s+", " ", x).strip()


def parse() -> pd.DataFrame:
    t = SRC.read_text(encoding="utf-8")
    i = t.find('id="changes"')
    j = t.find("\n|}", i)
    body = t[i:j]
    rows = []
    for chunk in body.split("\n|-")[1:]:
        lines = [ln for ln in chunk.strip().split("\n") if ln.strip() and not ln.startswith("!")]
        cells = []
        for ln in lines:
            ln = ln.strip()
            if ln.startswith("|"):
                ln = ln.lstrip("|")
                cells.extend(ln.split("||"))
            elif cells:
                cells[-1] += " " + ln
        cells = [clean(c) for c in cells]
        if len(cells) < 5:
            continue
        d = pd.to_datetime(cells[0], errors="coerce")
        if pd.isna(d):
            continue
        rows.append(dict(date=d, added_ticker=cells[1], added_name=cells[2], removed_ticker=cells[3],
                         removed_name=cells[4], reason=cells[5] if len(cells) > 5 else ""))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = parse()
    PROC.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROC / "wiki_sp500_changes.csv", index=False)
    print(len(df), df.date.min(), df.date.max())
    print(df[df.removed_ticker != ""].groupby(df.date.dt.year).size().to_string())
