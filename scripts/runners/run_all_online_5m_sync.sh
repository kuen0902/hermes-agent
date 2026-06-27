#!/usr/bin/env bash
# ==============================================================================
# Hermes Daily "Remaining Online Stocks" 5-Minute Historical Price Sync Wrapper
# ==============================================================================
set -e

PYTHON="/Users/bookid/.hermes/.venv/bin/python"
SCRIPTS_DIR="/Users/bookid/.hermes/scripts"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Starting all online remaining 5m data sync ==="
$PYTHON "$SCRIPTS_DIR/fetchers/sync_all_online_5m.py" "$@"
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] All online remaining 5m data sync completed successfully ==="
