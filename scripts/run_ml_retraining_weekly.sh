#!/bin/bash
# Weekly ML Retraining Pipeline
# Scheduled to run on Weekends (Saturday 02:00 AM)
PYTHON="/Users/bookid/workspace/hermes-agent/venv_314/bin/python"

echo "1. Fetching historical data backfills (Delta Mode)..."
$PYTHON /Users/bookid/.hermes/scripts/fetch_tw_historical_all.py

echo "2. Merging stock data master tables (Vectorized)..."
$PYTHON /Users/bookid/.hermes/scripts/merge_stock_data.py

echo "3. Retraining ML Model with latest market dynamics..."
$PYTHON /Users/bookid/.hermes/scripts/ml_trainer.py

echo "Weekend ML Retraining Complete."
