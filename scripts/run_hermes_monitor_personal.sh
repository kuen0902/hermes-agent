#!/bin/bash
# 個人組合即時監控腳本

RESULT=$(/Users/bookid/.hermes/scripts/hermes_monitor --profile personal 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    if [ -n "$RESULT" ]; then
        echo "$RESULT"
    else
        echo "個人組合監控運行正常：無異常觸發"
    fi
    exit 0
else
    echo "個人組合監控執行失敗：$RESULT"
    exit $EXIT_CODE
fi
