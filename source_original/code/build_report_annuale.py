"""Fill the annual-study report template with the generated tables and build the Word file."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from config import OUT

ROOT = Path(__file__).resolve().parents[1]


def main():
    T = json.load(open(OUT / "report_annuale_tables.json"))
    txt = (ROOT / "paper" / "annuale.md").read_text()      # template with {{placeholders}}
    missing = sorted(set(re.findall(r"\{\{(\w+)\}\}", txt)) - set(T))
    if missing:
        raise SystemExit(f"missing placeholders: {missing}")
    txt = re.sub(r"\{\{(\w+)\}\}", lambda m: str(T[m.group(1)]), txt)
    md_out = OUT / "GRMS_Report_January_Buy_Annuale.md"
    md_out.write_text(txt)
    # Word: images resolved from out/docx_annuale/charts
    d = OUT / "docx_annuale"
    (d / "charts").mkdir(parents=True, exist_ok=True)
    for f in ("fig20_annuale_lordo.png", "fig21_annuale_nettista.png", "fig22_rendimenti_annui.png", "fig23_lordo_lordista_nettista.png"):
        shutil.copy(OUT / "charts" / f, d / "charts" / f)
    (d / "report.md").write_text(txt.replace("results/charts/", "charts/"))
    conv = Path(__file__).resolve().parent / "md2docx.js"
    try:
        subprocess.run(["node", str(conv), str(d / "report.md"), str(OUT / "GRMS_Report_January_Buy_Annuale.docx"), str(d)], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:      # Node.js or the docx package missing
        print("Word non generato (serve Node.js con il pacchetto docx):", exc)
    print("ok", md_out)


if __name__ == "__main__":
    main()
