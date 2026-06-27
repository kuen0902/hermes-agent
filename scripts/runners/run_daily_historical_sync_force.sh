#!/usr/bin/env bash
# ==============================================================================
# Hermes Daily Historical Sync Force Runner Wrapper
# ==============================================================================
set -e

PYTHON="/Users/bookid/.hermes/.venv/bin/python"
SCRIPTS_DIR="/Users/bookid/.hermes/scripts"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Starting forced full market daily historical sync ==="
$PYTHON "$SCRIPTS_DIR/daily_historical_sync.py" --force
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Forced daily historical sync completed successfully ==="
