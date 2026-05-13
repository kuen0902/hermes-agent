#!/bin/bash
set -e
python3 /Users/bookid/.hermes/scripts/daily_historical_sync.py
python3 /Users/bookid/.hermes/scripts/ml_signal_inference.py
python3 /Users/bookid/.hermes/scripts/ml_signal_reporter.py
