"""
Working copy of the original project: work/replica_originale/ (ignored by Git).

The original scripts locate every input and output from their own position
(config.ROOT = parents[1] of code/), so a byte-identical copy of source_original/
runs unchanged and writes only inside the copy. source_original/ is only read.

    python -m research.replica_originale prepare     # copy source_original/ and verify the copy
    python -m research.replica_originale run-data    # fetch_data -> parse_yahoo -> data_layer, in the copy
    python -m research.replica_originale check       # load the rebuilt panel and check it (no backtest)
    python -m research.replica_originale run annual_study.py report_annuale_tables.py   # phase 1.3

Guards, every time:
  * source_original/ is verified against its SHA-256 manifest before and after;
  * config.ROOT (and, for `run`, config.OUT) of the copy must resolve inside work/replica_originale;
  * the original steps run with HTTP(S) proxies pointing to a closed local port,
    so any attempt to download data fails instead of silently fetching new data.
`run` also requires the copied code to be byte-identical to the original (no file of the
copy modified or missing) and accepts only the scripts authorised for phase 1.3.
Console output is saved in logs/fase_1_0/ (data steps) and logs/fase_1_3/ (`run`);
.txt because *.log is ignored by Git.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import importlib.metadata
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

from research import integrity

REPO = integrity.REPO
WORK = REPO / "work"
DEST = WORK / "replica_originale"
CODE = DEST / "code"
LOGS = REPO / "logs" / "fase_1_0"
LOGS_RUN = REPO / "logs" / "fase_1_3"
DATA_STEPS = ["fetch_data.py", "parse_yahoo.py", "data_layer.py"]
RUN_ALLOWED = ["annual_study.py", "report_annuale_tables.py"]     # authorised on 2026-10-30 (phase 1.3)
DEAD_PROXY = "http://127.0.0.1:9"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def require_intact_original(when: str) -> None:
    diff = integrity.verify()
    if not diff.ok:
        sys.exit(f"source_original/ is NOT intact ({when}):\n{diff.report()}")
    print(f"[{utc_now()}] source_original/ intact ({when})")


def offline_env() -> dict:
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env[k] = DEAD_PROXY
    env["NO_PROXY"] = env["no_proxy"] = ""
    return env


def copy_root() -> Path:
    """config.ROOT as the copied config.py computes it."""
    out = subprocess.run([sys.executable, "-c", "import config; print(config.ROOT)"], cwd=CODE,
                         capture_output=True, text=True, env=offline_env(), check=True)
    return Path(out.stdout.strip()).resolve()


def require_copy_paths() -> None:
    root = copy_root()
    if root != DEST.resolve() or integrity.PROTECTED.resolve() in (root, *root.parents):
        sys.exit(f"config.ROOT of the copy resolves to {root}, expected {DEST}")
    print(f"config.ROOT of the copy = {root}")


def prepare(force: bool) -> None:
    require_intact_original("before copy")
    if DEST.exists():
        if not force:
            sys.exit(f"{DEST} exists; use --force to rebuild it")
        if WORK.resolve() not in DEST.resolve().parents:
            sys.exit(f"refusing to delete {DEST}: not inside {WORK}")
        shutil.rmtree(DEST)
    WORK.mkdir(exist_ok=True)
    shutil.copytree(integrity.PROTECTED, DEST, symlinks=True)
    diff = integrity.verify(DEST)
    if not diff.ok:
        sys.exit(f"the copy differs from the manifest:\n{diff.report()}")
    print(f"copy of source_original/ -> {DEST}: identical to the manifest "
          f"({len(integrity.read_manifest(integrity.MANIFEST))} files)")
    require_copy_paths()
    require_intact_original("after copy")


def run_data() -> None:
    if not CODE.is_dir():
        sys.exit(f"{CODE} missing: run `prepare` first")
    require_intact_original("before run-data")
    require_copy_paths()
    LOGS.mkdir(parents=True, exist_ok=True)
    for step in DATA_STEPS:
        script = (CODE / step).resolve()
        assert DEST.resolve() in script.parents, script
        t0, start = time.time(), utc_now()
        res = subprocess.run([sys.executable, step], cwd=CODE, capture_output=True, text=True, env=offline_env())
        secs = time.time() - t0
        log = LOGS / f"replica_{step.removesuffix('.py')}.txt"
        log.write_text(f"step: {step}\ncwd: work/replica_originale/code\ninterpreter: {sys.executable} "
                       f"(Python {sys.version.split()[0]})\nnetwork: HTTP(S) proxies -> {DEAD_PROXY} (offline)\n"
                       f"start_utc: {start}\nduration_s: {secs:.1f}\nexit_code: {res.returncode}\n"
                       f"--- stdout ---\n{res.stdout}--- stderr ---\n{res.stderr}")
        print(f"[{utc_now()}] {step}: exit {res.returncode} in {secs:.0f}s -> {log.relative_to(REPO)}")
        if res.returncode != 0:
            sys.exit(f"{step} failed, see {log}")
    require_intact_original("after run-data")


def _sha256(path: Path) -> str:
    return integrity.sha256_file(path)


def copy_out_dir() -> Path:
    """config.OUT as the copied config.py computes it."""
    out = subprocess.run([sys.executable, "-c", "import config; print(config.OUT)"], cwd=CODE,
                         capture_output=True, text=True, env=offline_env(), check=True)
    return Path(out.stdout.strip()).resolve()


def require_copy_code_unchanged() -> None:
    """Every file shipped in source_original/ is present and unmodified in the copy
    (files added by the pipeline are allowed)."""
    diff = integrity.verify(DEST)
    if diff.modified or diff.missing:
        sys.exit(f"the copy no longer matches the original:\n{diff.report()}")
    print(f"copy of the original: 0 modified, 0 missing ({len(diff.added)} files added by the pipeline)")


def module_constants(path: Path) -> dict:
    """Top-level UPPERCASE literal assignments of a module, read without executing it."""
    out = {}
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                names = [t] if isinstance(t, ast.Name) else list(getattr(t, "elts", []))
                vals = [node.value] if isinstance(t, ast.Name) else list(getattr(node.value, "elts", []))
                for n, v in zip(names, vals):
                    if isinstance(n, ast.Name) and n.id.isupper():
                        try:
                            out[n.id] = ast.literal_eval(v)
                        except ValueError:
                            out[n.id] = ast.unparse(v)
    return out


def snapshot(folder: Path) -> dict[str, tuple[int, str]]:
    return {p.relative_to(folder).as_posix(): (p.stat().st_size, _sha256(p))
            for p in sorted(folder.rglob("*")) if p.is_file()}


def versions() -> str:
    pk = ["numpy", "pandas", "pyarrow", "scipy", "openpyxl", "matplotlib"]
    return f"Python {sys.version.split()[0]}; " + "; ".join(f"{k} {importlib.metadata.version(k)}" for k in pk)


def run_steps(steps: list[str]) -> None:
    bad = [s for s in steps if s not in RUN_ALLOWED]
    if bad:
        sys.exit(f"not authorised in this phase: {bad} (allowed: {RUN_ALLOWED})")
    if not CODE.is_dir():
        sys.exit(f"{CODE} missing: run `prepare` and `run-data` first")
    require_intact_original("before run")
    require_copy_paths()
    require_copy_code_unchanged()
    out_dir = copy_out_dir()
    if out_dir != (DEST / "out").resolve() or integrity.PROTECTED.resolve() in out_dir.parents:
        sys.exit(f"config.OUT of the copy resolves to {out_dir}, expected {DEST / 'out'}")
    created = not out_dir.exists()
    out_dir.mkdir(exist_ok=True)       # annual_study.py writes to OUT without creating it (run_all.py's earlier steps do)
    print(f"config.OUT of the copy = {out_dir}" + (" (created)" if created else ""))
    LOGS_RUN.mkdir(parents=True, exist_ok=True)
    for step in steps:
        script = (CODE / step).resolve()
        assert DEST.resolve() in script.parents, script
        before = snapshot(out_dir)
        cmd = [sys.executable, step]
        t0, start = time.time(), utc_now()
        res = subprocess.run(cmd, cwd=CODE, capture_output=True, text=True, env=offline_env())
        secs = time.time() - t0
        after = snapshot(out_dir)
        written = [f"  {k}  {after[k][0]} bytes  sha256={after[k][1]}" + ("" if k not in before else "  (overwritten)")
                   for k in sorted(after) if before.get(k) != after[k]]
        consts = module_constants(script)
        log = LOGS_RUN / f"esecuzione_{step.removesuffix('.py')}.txt"
        log.write_text(
            f"step: {step}\n"
            f"command: cd work/replica_originale/code && {shlex.join(cmd).replace(str(REPO) + '/', '')}\n"
            f"script sha256: {_sha256(script)} (= manifest entry code/{step})\n"
            f"versions: {versions()}\n"
            f"config: ROOT=work/replica_originale  OUT=work/replica_originale/out"
            f"{'  (out/ created by the runner)' if created and step == steps[0] else ''}\n"
            f"module constants (read with ast, not executed): {json.dumps(consts, ensure_ascii=False)}\n"
            f"network: HTTP(S) proxies -> {DEAD_PROXY} (offline)\n"
            f"start_utc: {start}\nduration_s: {secs:.1f}\nexit_code: {res.returncode}\n"
            f"files written to out/:\n" + "\n".join(written) + "\n"
            f"--- stdout ---\n{res.stdout}--- stderr ---\n{res.stderr}")
        print(f"[{utc_now()}] {step}: exit {res.returncode} in {secs:.0f}s, {len(written)} files written "
              f"-> {log.relative_to(REPO)}")
        if res.returncode != 0:
            sys.exit(f"{step} failed, see {log}")
    require_copy_code_unchanged()
    require_intact_original("after run")


def check() -> None:
    """Load the rebuilt panel exactly as the original code does and record what was built.
    No ranking, no portfolio, no backtest."""
    require_intact_original("before check")
    require_copy_paths()
    sys.path.insert(0, str(CODE))
    import numpy as np
    import pandas as pd
    import config
    assert Path(config.__file__).resolve().parent == CODE.resolve(), config.__file__
    from panel import Panel
    import patches

    lines = [f"check run at {utc_now()} (Python {sys.version.split()[0]}, numpy {np.__version__}, pandas {pd.__version__})"]
    add = lines.append

    # 1. reassembled dataset vs the shipped manifest
    man = json.load(open(config.RAW / "MANIFEST.json"))
    for name in ("jb_prices.parquet", "jb_membership_intervals.parquet", "jb_renames.csv"):
        p = config.RAW / name
        h = _sha256(p)
        add(f"{name}: {p.stat().st_size} bytes sha256={h} manifest_match={h == man[name]['sha256']}")

    # 2. minimal profile of the raw S&P 500 price file
    jb = pd.read_parquet(config.JB_PRICES)
    add(f"jb_prices: rows={len(jb)} tickers={jb.ticker.nunique()} columns={list(jb.columns)}")
    add(f"jb_prices: dtypes={ {c: str(t) for c, t in jb.dtypes.items()} }")
    d = pd.to_datetime(jb["date"])
    add(f"jb_prices: dates {d.min().date()} -> {d.max().date()}")
    add(f"jb_prices: rows by source={jb['source'].astype(str).value_counts().to_dict()}")
    for t in ("SNDK", "SNDK-201605", "MRNA"):
        s = d[jb.ticker == t]
        add(f"jb_prices: {t}: first={s.min().date() if len(s) else None} last={s.max().date() if len(s) else None} rows={len(s)}")
    del jb, d

    # 3. processed files written by the pipeline (inside the copy)
    for p in sorted(config.PROC.iterdir()):
        add(f"processed: {p.name} {p.stat().st_size} bytes sha256={_sha256(p)}")

    # 4. panel as the original code loads it (quarantine + adjustment repairs applied)
    p = Panel.load()
    add(f"panel: dates={len(p.dates)} ({p.dates[0].date()} -> {p.dates[-1].date()}) labels={len(p.labels)}")
    add(f"panel: S&P 500 membership intervals={len(p.spx)} (start {p.spx.start.min().date()}), "
        f"members on {p.dates[-1].date()}={len(p.members('SPX', p.dates[-1]))}")
    add(f"panel: adjustment repairs={len(p.repairs)} cells on {p.repairs.label.nunique()} labels")

    # 5. repairs vs the historical log shipped in the main results workbook (read-only)
    import openpyxl
    wb = openpyxl.load_workbook(integrity.PROTECTED / "results" / "GRMS_JanuaryBuy_Risultati.xlsx",
                                read_only=True, data_only=True)
    rows = list(wb["Riparazioni_dati"].iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r and "label" in [str(x) for x in r])
    hist = pd.DataFrame(rows[hi + 1:], columns=rows[hi]).dropna(how="all")
    hist = hist[["label", "date", "vendor_ret", "repaired_ret"]]
    hist["date"] = hist["date"].astype(str).str[:10]
    mine = p.repairs.copy()
    key = ["label", "date"]
    m = mine.merge(hist, on=key, how="outer", suffixes=("_rebuilt", "_hist"), indicator=True)
    both = m[m._merge == "both"]
    dv = float(np.nanmax(np.abs(both.vendor_ret_rebuilt.astype(float) - both.vendor_ret_hist.astype(float)))) if len(both) else float("nan")
    dr = float(np.nanmax(np.abs(both.repaired_ret_rebuilt.astype(float) - both.repaired_ret_hist.astype(float)))) if len(both) else float("nan")
    add(f"repairs vs historical sheet 'Riparazioni_dati': rebuilt={len(mine)} historical={len(hist)} "
        f"matched={len(both)} only_rebuilt={int((m._merge == 'left_only').sum())} "
        f"only_historical={int((m._merge == 'right_only').sum())} max|d vendor_ret|={dv:.2e} max|d repaired_ret|={dr:.2e}")

    # 6. survivorship patches
    n0 = len(p.labels)
    patches.apply(p)
    new = [str(x) for x in p.labels[n0:]]
    add(f"patches: {len(new)} synthetic series added: {new}")
    add(f"last date in panel (AN_parametri.json reports 2026-10-09): {p.dates[-1].date()}")

    out = LOGS / "replica_check.txt"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"-> {out.relative_to(REPO)}")
    require_intact_original("after check")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m research.replica_originale", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("prepare")
    sp.add_argument("--force", action="store_true", help="delete and rebuild work/replica_originale")
    sub.add_parser("run-data")
    sub.add_parser("check")
    sr = sub.add_parser("run", help=f"run original scripts in the copy (allowed: {', '.join(RUN_ALLOWED)})")
    sr.add_argument("steps", nargs="+")
    args = ap.parse_args(argv)
    {"prepare": lambda: prepare(args.force), "run-data": run_data, "check": check,
     "run": lambda: run_steps(args.steps)}[args.cmd]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
