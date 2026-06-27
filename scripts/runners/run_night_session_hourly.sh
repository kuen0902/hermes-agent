#!/usr/bin/env bash
# ==============================================================================
# Hermes Taiwan Stock Night Session Hourly Update Wrapper
# ==============================================================================
set -e

PYTHON="/Users/bookid/.hermes/.venv/bin/python"
SCRIPTS_DIR="/Users/bookid/.hermes/scripts"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Starting Night Session Hourly Update ==="

# 1. Fetch market prices for NQ, TSM, NVDA, SYNA, FITXP and update the bridge file
$PYTHON "$SCRIPTS_DIR/fetchers/fetch_market_prices.py"

# 2. Run the night session monitor report script
$PYTHON "$SCRIPTS_DIR/run_night_report.py"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Night Session Hourly Update Completed Successfully ==="
