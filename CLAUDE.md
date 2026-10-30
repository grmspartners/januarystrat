# JANUARY BUY — QUANTITATIVE RESEARCH PROTOCOL

## Mission
Conduct independent, reproducible quantitative research on the January Buy strategy described in the supplied Excel workbook, Word report and Markdown notes.

The objective is to determine whether the strategy has a genuine, economically exploitable information edge after realistic execution costs, taxes and structural fees. Do not assume that the existing conclusions are correct.

## Source files
Treat these three files as the initial source of truth:
- GRMS_JanuaryBuy_Analisi_Annuale.xlsx
- GRMS_Report_January_Buy_Annuale.docx
- januarybuy-analisi-annuale.md

Preserve all originals. Never overwrite source files.

The Markdown mentions additional source code, CSV files and research materials in a separate January Buy project directory. These materials are not necessarily available here. Inventory the available files and clearly identify missing dependencies before attempting to reproduce results. Never fabricate missing data or claim reproduction without evidence.

## First phase: forensic audit
1. Read all supplied documents and inspect every relevant workbook sheet, formula, named range and parameter.
2. Reconstruct the portfolio rules, annual winner selection, entry and exit timestamps, stop-loss mechanics, cash treatment, dividends, taxes and benchmarks.
3. Recalculate key results independently wherever the supplied data permit.
4. Reconcile discrepancies between the workbook, Word report and Markdown.
5. Create an audit log separating verified facts, reported claims, assumptions and unresolved questions.
6. Do not change strategy rules before documenting the original baseline.

## Core research questions
- Does the previous calendar year's best-performing S&P 500 constituent continue to outperform over the next six and twelve months?
- Is the reported advantage specific to the number-one stock, or does it extend to ranks two and three?
- Does a 35% stop-loss genuinely improve risk-adjusted and after-tax outcomes?
- Can moving averages, trend filters, trailing stops or volatility-based exits improve results out of sample?
- Is the apparent edge robust across market regimes, sectors and individual years?
- Does an investment company or other legally applicable structure improve final investor wealth after all costs and taxes?

## Historical data and selection integrity
Use historical S&P 500 constituents and point-in-time information wherever possible. Account for delisted firms, bankruptcies, mergers, ticker changes, splits and dividends.

Select each year's winner using only information available by the end of that year. Enter no earlier than the first executable market price of the following year. Do not use future information to determine eligibility, rank or entry.

If point-in-time constituents or total-return data are unavailable, disclose the limitation and quantify its possible effect where feasible. Do not present a modern survivor-only universe as an unbiased historical universe.

Validate data provenance, licensing, missing observations, adjusted-price methodology and timestamp conventions before running tests.

## Experimental design
Pre-register hypotheses and separate research development from final out-of-sample evaluation. Use walk-forward testing and time-based holdouts.

Test six- and twelve-month outcomes. Compare the 35% stop with a limited, explicitly documented set of alternative thresholds and exit rules. Treat technical indicators as hypotheses, not presumed improvements.

Control for multiple testing, parameter mining, survivorship bias, look-ahead bias and data snooping. Use suitable confidence intervals, bootstrap or permutation tests when justified by the data.

Include fair benchmarks, including S&P 500 total return, and compare strategies with consistent dates, cash flows and exposure. Account for trading costs, bid-ask spreads, slippage, overnight gaps and realistic stop execution.

Report CAGR, cumulative return, volatility, maximum drawdown, recovery time, Sharpe, Sortino, Calmar, turnover, market exposure, annual results and rolling-period results. Show uncertainty and sample size. Do not optimize only for CAGR.

## Tax and structure analysis
Model direct investment and the proposed investment-company or AMC structure as distinct cash-flow systems. Test annual fees of 0.5%, 0.6%, 0.7%, 0.8% and 0.9%.

Include transaction costs, stamp duty where applicable, dividends and withholding, tax on realized gains, loss offsets, taxation within the vehicle, distributions, liquidation and any relevant administration costs.

Verify Italian tax treatment against current official sources. Do not assume that a structure qualifies for a particular tax regime without establishing its legal and operational eligibility. Clearly distinguish verified rules from assumptions requiring professional tax advice.

Calculate final spendable wealth and the break-even conditions under which each structure outperforms the alternatives. Account for the tax deferral associated with holding an accumulating ETF without annual sales.

## Moderna and the 2026 hypothesis
Treat Moderna as a prospective candidate, not as a known winner. Establish the exact point-in-time selection rule and the date when a trade could actually be initiated. Do not use subsequent information to justify an earlier decision.

## Deliverables
Produce:
1. A source inventory and reproducibility audit.
2. A documented reconstruction of the original strategy.
3. Reproducible research code and automated tests.
4. Validated datasets, subject to licensing restrictions.
5. Tables and charts for six-month, twelve-month and annual results.
6. Out-of-sample and robustness results.
7. A complete after-tax structure comparison and fee sensitivity analysis.
8. A technical research report with assumptions, evidence, limitations and conclusions.

Maintain a clean directory structure. Record experiment parameters, data versions and execution dates. Keep original files immutable. Never claim that an experiment ran successfully unless it actually ran.

## Decision standard
The strategy is credible only if the edge is statistically supported, economically material, robust out of sample, implementable with point-in-time information and profitable after realistic costs and taxes.

If evidence is weak, contradictory or insufficient, say so directly. The objective is to discover the truth, not to confirm the initial thesis.
