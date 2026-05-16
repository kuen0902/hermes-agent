#!/bin/bash
set -e
PYTHON="/Users/bookid/.hermes/.venv/bin/python"
$PYTHON /Users/bookid/.hermes/scripts/fetch_institutional_data.py
$PYTHON /Users/bookid/.hermes/scripts/daily_historical_sync.py
$PYTHON /Users/bookid/.hermes/scripts/ml_signal_inference.py
$PYTHON /Users/bookid/.hermes/scripts/ml_signal_reporter.py
