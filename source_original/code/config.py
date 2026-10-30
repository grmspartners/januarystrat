"""
GRMS Partners - "January Buy" momentum study
=============================================

Central configuration: file locations and the default economic assumptions.

Every number that changes a backtest result lives here (or is passed explicitly
to the engine), so a reader can audit the assumptions in one place.

Conventions
-----------
* All prices are in USD unless a function says otherwise.
* "adj" series are split- AND dividend-adjusted (total-return basis).
* "close" series are split-adjusted only (the price you would see on a chart
  that has been back-adjusted for splits, without dividends).
* Rates are decimals (0.26 = 26%).
"""
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROC = DATA / "processed"
OUT = ROOT / "out"

# Public, survivorship-aware S&P 500 dataset (github.com/Johnbrick123/sp500-data)
JB_PRICES = RAW / "jb_prices.parquet"
JB_MEMBERS = RAW / "jb_membership_intervals.parquet"
JB_RENAMES = RAW / "jb_renames.csv"

# Yahoo Finance batch downloaded through the browser (Nasdaq-100 names + benchmarks)
YAHOO_BATCH = PROC / "yahoo_batch1.parquet"

# Nasdaq-100 point-in-time membership (github.com/jmccarrell/n100tickers), 2007+
NDX_MEMBERS = RAW / "ndx_membership_intervals.csv"   # built by build_ndx_membership.py
NDX_YAHOO_MAP = RAW / "ndx_yahoo_map.json"
YAHOO_RAW = RAW / "GRMS_YAHOO_batch1.ndjson.gz"
YAHOO_META = PROC / "yahoo_batch1_meta.json"
WIKI_SP500 = RAW / "wiki_sp500_current.csv"
FF_DIR = RAW

FRED_JSON = RAW / "GRMS_FRED_v1.json"

# --------------------------------------------------------------------------
# Italian tax regime (verified against primary sources, see the thesis
# appendix for references). Values are the CURRENT regime and are applied to
# the whole history on purpose: the question is "what would this strategy do
# for an Italian investor today", not "what did it do under 1997 law".
# --------------------------------------------------------------------------
TAX_CAPITAL_GAINS = 0.26          # redditi diversi on shares / options (art. 67-68 TUIR)
TAX_ETF_GAINS = 0.26              # redditi di capitale on harmonised funds / ETFs
TAX_TBILL = 0.125                 # interest on white-list government bonds (US T-bills)
LOSS_CARRY_YEARS = 4              # minusvalenze usable until the 4th year after realisation
US_DIV_WHT = 0.15                 # US withholding with W-8BEN (Italy-US treaty)
IT_DIV_TAX = 0.26                 # Italian tax on the NET foreign dividend (regime amministrato)
DIV_TAX_EFFECTIVE = 1 - (1 - US_DIV_WHT) * (1 - IT_DIV_TAX)   # = 37.1%
STAMP_DUTY = 0.002                # imposta di bollo 0.20% p.a. on the dossier value

# --------------------------------------------------------------------------
# Trading frictions (per side, as a fraction of traded value)
# --------------------------------------------------------------------------
COST_PER_SIDE = 0.0010            # 10 bps: commission + half-spread + slippage, large caps
ETF_TER_SPX = 0.0007              # UCITS S&P 500 accumulating ETF (e.g. CSPX-type)
ETF_TER_NDX = 0.0030              # UCITS Nasdaq-100 accumulating ETF (EQQQ-type)

# --------------------------------------------------------------------------
# Strategy defaults (the rule set described in the original thread)
# --------------------------------------------------------------------------
START_CAPITAL = 100.0
STOP_LOSS = 0.35                  # sell if price falls 35% below the purchase price
