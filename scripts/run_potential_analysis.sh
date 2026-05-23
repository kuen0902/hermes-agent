#!/bin/bash

# --- Master Orchestrator: Taiwan Stock 5Y Survivor ML & Institutional Flow Pipeline ---
# This script orchestrates the E2E process of fetching institutional data, training models, and generating visual reports.

set -e # Exit immediately on error

echo "========================================================================="
echo "  🚀 STARTING HERMES TAIWAN STOCK 5Y SURVIVOR ML PIPELINE"
echo "========================================================================="

PYTHON_PATH="/Users/bookid/.hermes/.venv/bin/python"
SCRIPTS_DIR="/Users/bookid/.hermes/scripts"

# Step 0: Initialize DuckDB Analytical Database
echo ""
echo "-------------------------------------------------------------------------"
echo "  🔹 STEP 0: Initializing DuckDB Analytical Database"
echo "-------------------------------------------------------------------------"
$PYTHON_PATH $SCRIPTS_DIR/ml/init_potential_db.py

# Step 1: Sync Institutional Data for Top 500 High-Liquidity Stocks
echo ""
echo "-------------------------------------------------------------------------"
echo "  🔹 STEP 1: Syncing 5Y Institutional Investor Flows (三大法人) for Top 500"
echo "-------------------------------------------------------------------------"
$PYTHON_PATH $SCRIPTS_DIR/fetchers/fetch_institutional_5y.py --top 500

# Step 2: Run Machine Learning Features, Training, and Scorer
echo ""
echo "-------------------------------------------------------------------------"
echo "  🔹 STEP 2: Running XGBoost Wave Scorer & ML Training Engine"
echo "-------------------------------------------------------------------------"
$PYTHON_PATH $SCRIPTS_DIR/ml/potential_stocks_engine.py

# Step 3: Generate Visual Charts and Detailed Markdown Reports
echo ""
echo "-------------------------------------------------------------------------"
echo "  🔹 STEP 3: Generating Visual Radar Chart and Markdown Reports"
echo "-------------------------------------------------------------------------"
$PYTHON_PATH $SCRIPTS_DIR/ml/generate_potential_report.py

# Step 4: Run Machine Learning Predictions Calibration & Performance Loop
echo ""
echo "-------------------------------------------------------------------------"
echo "  🔹 STEP 4: Calibrating ML Predictions & Establishing Feedback Loop"
echo "-------------------------------------------------------------------------"
$PYTHON_PATH $SCRIPTS_DIR/ml/calibrate_predictions.py

echo ""
echo "========================================================================="
echo "  ✅ HERMES ML POTENTIAL STOCKS ANALYSIS PIPELINE COMPLETE!"
echo "  - Registry Data: ~/.hermes/data/top_50_potential_stocks.json"
echo "  - Detailed Report: ~/.hermes/data/top_50_report.md"
echo "  - Visual Chart: ~/.hermes/data/top_20_potential_stocks.png"
echo "========================================================================="
