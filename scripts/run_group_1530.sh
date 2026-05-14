#!/bin/bash
set -e
PYTHON="/Users/bookid/workspace/hermes-agent/venv_314/bin/python"
$PYTHON /Users/bookid/.hermes/scripts/taiex_central_data_sync.py
$PYTHON /Users/bookid/.hermes/scripts/group_confluence_analysis.py
