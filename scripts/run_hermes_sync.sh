#!/bin/bash
# hermes_sync 數據同步腳本

RESULT=$(/usr/bin/swift /Users/bookid/.hermes/scripts/hermes_sync.swift 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    if [ -n "$RESULT" ]; then
        echo "$RESULT"
    else
        echo "數據同步完成"
    fi
    exit 0
else
    echo "數據同步執行失敗：$RESULT"
    exit $EXIT_CODE
fi
