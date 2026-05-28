#!/usr/bin/env bash
# ==============================================================================
# Hermes Daily Institutional Data Sync Wrapper
# ==============================================================================
set -e

PYTHON="/Users/bookid/.hermes/.venv/bin/python"
SCRIPTS_DIR="/Users/bookid/.hermes/scripts"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Starting institutional data sync with venv Python ==="
$PYTHON "$SCRIPTS_DIR/fetchers/fetch_institutional_data.py" "$@"
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Institutional data sync completed successfully ==="
