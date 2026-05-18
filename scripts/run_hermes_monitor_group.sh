#!/bin/bash
# 群組即時監控腳本
# 只有當觸發閾值時才輸出警報，否則輸出狀態訊息

RESULT=$(/Users/bookid/.hermes/scripts/hermes_monitor --profile group 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    if [ -n "$RESULT" ]; then
        # 有警報內容，輸出警報
        echo "$RESULT"
    else
        # 無警報，輸出狀態訊息讓 Cron 標記為 ok
        echo "群組監控運行正常：無異常觸發"
    fi
    exit 0
else
    # 執行錯誤
    echo "群組監控執行失敗：$RESULT"
    exit $EXIT_CODE
fi
