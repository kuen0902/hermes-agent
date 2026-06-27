#!/usr/bin/env bash
# ==============================================================================
# Hermes Active Retained Stocks Backfill Runner Wrapper
# ==============================================================================
set -e

PYTHON="/Users/bookid/.hermes/.venv/bin/python"
SCRIPTS_DIR="/Users/bookid/.hermes/scripts"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Starting batch backfill for retained stocks ==="
$PYTHON "$SCRIPTS_DIR/backfill_all_retained.py" --batch-size=100
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Batch backfill completed successfully ==="
