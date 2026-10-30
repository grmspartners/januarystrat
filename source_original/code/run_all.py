"""
One command to rebuild everything from the raw inputs.

    pip install pandas numpy scipy pyarrow statsmodels matplotlib openpyxl pyyaml
    cd code
    python run_all.py            # full pipeline (about 30-40 minutes)
    python run_all.py --report   # only rebuild charts and the Excel workbook

Order: fetch_data -> parse_yahoo -> data_layer (panel) -> parse_wiki_changes -> build_top3 -> spariti
(titoli spariti) -> experiments (B C D DL E F) -> experiments2 (G1-G4) -> rank_tests -> extra_analyses
(G5, factors) -> final_selection (48 rules x 12 tranches x 4 views) -> final_decision -> rebalanced_mix ->
make_report (main workbook + charts) -> build_excel_leaps -> build_excel_definitiva -> paper_tables.
Excel files with formulas are recalculated by opening them in Excel (or LibreOffice).
"""
from __future__ import annotations

import subprocess
import sys
import time

STEPS = ["fetch_data.py", "parse_yahoo.py", "data_layer.py", "parse_wiki_changes.py", "build_top3.py", "spariti.py",
         "experiments.py", "experiments2.py", "rank_tests.py", "extra_analyses.py", "final_selection.py",
         "final_decision.py", "rebalanced_mix.py", "make_report.py", "build_excel_leaps.py",
         "build_excel_definitiva.py", "paper_tables.py",
         # focused annual note (October 2026): top-1 vs top-3, stop, LEAPS 35/65, lordo / lordista (AMC) / nettista
         "annual_study.py", "build_excel_annuale.py", "charts_annuale.py", "report_annuale_tables.py", "build_report_annuale.py"]

if __name__ == "__main__":
    steps = ["make_report.py"] if "--report" in sys.argv else STEPS
    for s in steps:
        t = time.time()
        print(f"=== {s}", flush=True)
        subprocess.run([sys.executable, s], check=True)
        print(f"    done in {time.time() - t:.0f}s", flush=True)
