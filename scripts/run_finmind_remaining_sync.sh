#!/usr/bin/env bash
# ==============================================================================
# Hermes Daily FinMind Remaining Sync Wrapper
# ==============================================================================
set -e

PYTHON="/Users/bookid/.hermes/.venv/bin/python"
SCRIPTS_DIR="/Users/bookid/.hermes/scripts"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Starting FinMind remaining sync with venv Python ==="
$PYTHON "$SCRIPTS_DIR/fetchers/sync_remaining_finmind_data.py" "$@"
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] FinMind remaining sync completed successfully ==="
