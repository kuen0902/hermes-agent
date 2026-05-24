#!/bin/bash
# ==============================================================================
# 盤後 ML 預測與發送完整管線自動化腳本
# 動作：
#   1. 更新所有監控個股之三大法人買賣超與最新外資持股比率 (SQLite)
#   2. 執行 27 維度的自適應 ML 推理，並發送圖表與報告給各自的 Telegram Profile
# ==============================================================================
set -e

PYTHON="/Users/bookid/.hermes/.venv/bin/python"
SCRIPTS_DIR="/Users/bookid/.hermes/scripts"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] 1. 開始更新所有監控股票之三大法人與外資持股比率 ==="
$PYTHON "$SCRIPTS_DIR/fetchers/fetch_institutional_data.py"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] 2. 開始同步當日最新日線價量並寫入 DuckDB ==="
$PYTHON "$SCRIPTS_DIR/daily_historical_sync.py" --fast

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] 3. 開始同步當日 5 分鐘高頻價量數據 ==="
$PYTHON "$SCRIPTS_DIR/fetchers/sync_historical_5m.py"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] 4. 開始執行 36 維度 ML 滾動遞迴預測與校準 ==="
$PYTHON "$SCRIPTS_DIR/ml/intraday_ml_pipeline.py"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] 盤後 ML 預測流程執行完畢 ==="
