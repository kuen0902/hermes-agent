#!/bin/bash
set -e
ulimit -n 10240 || true
PYTHON="/Users/bookid/.hermes/.venv/bin/python"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] 1. 開始更新所有監控股票之三大法人與外資持股比率 ==="
$PYTHON /Users/bookid/.hermes/scripts/fetchers/fetch_institutional_data.py

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Phase 1: Daily Historical Sync (Full Market) ==="
$PYTHON /Users/bookid/.hermes/scripts/daily_historical_sync.py

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] 3. 開始同步當日 5 分鐘高頻價量數據 ==="
$PYTHON /Users/bookid/.hermes/scripts/fetchers/sync_historical_5m.py

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] 4. 開始執行全新個股自適應 14年-150日 滾動模型重新訓練與優化 ==="
$PYTHON /Users/bookid/.hermes/scripts/ml/rolling_ml_orchestrator.py

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] 5. 開始執行 41 維度 ML 盤後實時預估與校準 (無擾模式) ==="
$PYTHON /Users/bookid/.hermes/scripts/ml/intraday_ml_pipeline.py --silent

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] 6. 開始計算全市場 500 檔個股最新波段潛力股排名 (唯推論模式) ==="
$PYTHON /Users/bookid/.hermes/scripts/ml/potential_stocks_engine.py --inference-only

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] 7. 生成潛力股圖表報告並發送至 Jojo Telegram ==="
$PYTHON /Users/bookid/.hermes/scripts/ml/generate_potential_report.py --send-telegram

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] 清晨 5:00 ML 滾動修正自適應管線流程全部執行完畢 ==="


