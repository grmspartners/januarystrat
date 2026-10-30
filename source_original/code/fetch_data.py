"""
Step 0: make sure the S&P 500 survivorship-aware dataset is in data/raw.

Source: Johnbrick123/sp500-data GitHub release (prices.parquet with S&P 500
members incl. ~300 delisted names recovered from Tiingo / WIKI / Kaggle,
membership_intervals.parquet, renames.csv).

Reproducibility: the release is refreshed every night. The exact copy used in
this study (downloaded 12-Oct-2026) is shipped in data/raw/frozen/ split into
25 MB parts. By default this script REASSEMBLES the frozen copy and checks it
against data/raw/MANIFEST.json (SHA-256). Use --latest to download the current
release instead (results will then differ slightly in the most recent years).

Yahoo Finance, FRED and Kenneth French files are already in data/raw (they were
downloaded once through the browser; tools/yahoo_browser_downloader.js shows how).
"""
from __future__ import annotations

import glob
import hashlib
import json
import sys
import urllib.request

from config import RAW

BASE = "https://github.com/Johnbrick123/sp500-data/releases/download/data/"
FILES = {"prices.parquet": "jb_prices.parquet",
         "membership_intervals.parquet": "jb_membership_intervals.parquet",
         "renames.csv": "jb_renames.csv"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def reassemble_frozen():
    parts = sorted(glob.glob(str(RAW / "frozen" / "jb_prices.parquet.part*")))
    if not parts:
        return False
    with open(RAW / "jb_prices.parquet", "wb") as out:
        for part in parts:
            with open(part, "rb") as f:
                out.write(f.read())
    mem = RAW / "frozen" / "jb_membership_intervals.parquet"
    if mem.exists():
        (RAW / "jb_membership_intervals.parquet").write_bytes(mem.read_bytes())
    return True


def main(latest=False):
    RAW.mkdir(parents=True, exist_ok=True)
    if latest or not reassemble_frozen():
        for src, dst in FILES.items():
            print("downloading", src)
            urllib.request.urlretrieve(BASE + src, RAW / dst)
    man = json.load(open(RAW / "MANIFEST.json")) if (RAW / "MANIFEST.json").exists() else {}
    for dst in FILES.values():
        p = RAW / dst
        if not p.exists():
            sys.exit(f"missing {p}")
        h = sha256(p)
        ok = man.get(dst, {}).get("sha256") == h
        print(f"{dst:34s} {p.stat().st_size:>12,d} bytes  {'= frozen copy' if ok else 'DIFFERENT from the frozen copy'}")


if __name__ == "__main__":
    main(latest="--latest" in sys.argv)
