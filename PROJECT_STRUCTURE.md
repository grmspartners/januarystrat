# PROJECT STRUCTURE

## Root files
- CLAUDE.md: mandatory research instructions.
- GRMS_JanuaryBuy_Analisi_Annuale.xlsx: current annual analysis workbook.
- GRMS_Report_January_Buy_Annuale.docx: current annual report.
- januarybuy-analisi-annuale.md: current annual methodology and reported results.

## source_original
Immutable snapshot of the previous research project.
Contains original source code, datasets, intermediate results, reports and charts.

Claude must treat this directory as historical source material.
Never overwrite or delete its contents.

## Research policy
- Reproduce the original annual results before changing any methodology.
- Trace every reported metric to its underlying data and code.
- Distinguish historical results from independently reproduced results.
- Record every modification and experiment.
- Never silently replace missing data or assumptions.
- New research code and outputs must be stored outside source_original.

## Suggested working directories
- research/: new research scripts.
- data/processed/: derived datasets.
- outputs/tables/: new tables.
- outputs/charts/: new charts.
- reports/: new reports.
- logs/: audit logs and experiment records.

## Git policy
Do not commit raw datasets, large binary files or duplicated historical artifacts without first evaluating their necessity.
Preserve source_original locally.
