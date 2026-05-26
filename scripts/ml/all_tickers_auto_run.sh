#!/bin/bash
# -*- coding: utf-8 -*-
PYTHON="/Users/bookid/.hermes/.venv/bin/python"
SCRIPT="/Users/bookid/.hermes/scripts/ml/all_tickers_batch_trainer.py"
STATE_FILE="/Users/bookid/.hermes/models/batch_training_state.json"
BATCH_SIZE=100

echo "========================================================="
  echo " 🔄 啟動全市場在線商品 ML 滾動批量訓練自動循環跑器 "
echo "========================================================="

while true; do
    # 執行單次批次訓練
    $PYTHON $SCRIPT --batch-size=$BATCH_SIZE --resume
    EXIT_CODE=$?
    
    # 使用 Python 安全檢測是否已完成全市場訓練
    ALL_DONE=$($PYTHON -c "
import json, os
if os.path.exists('$STATE_FILE'):
    with open('$STATE_FILE', 'r', encoding='utf-8') as f:
        data = json.load(f)
        total = data.get('total_tickers', 0)
        completed = len(data.get('processed_tickers', []))
        if total > 0 and completed >= total:
            print('yes')
        else:
            print('no')
else:
    print('no')
")

    if [ "$ALL_DONE" = "yes" ]; then
        echo "========================================================="
        echo " 🎉 全市場所有商品已全數訓練完成！自動循環已順利結束。"
        echo "========================================================="
        break
    fi
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo "⚠️ 批次訓練中斷或出現異常，5秒後自動重試接續進度..."
        sleep 5
        continue
    fi
    
    # 批次間冷卻時間，防止 CPU 持續滿載過熱
    echo "☕ 批次完成，CPU 降溫冷卻 10 秒後自動啟動下一批次..."
    sleep 10
done
