#!/bin/bash

# 讀取目前的 crontab
crontab -l > /tmp/current_cron.txt 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ 無法讀取目前的 crontab，您可能沒有設定任何排程。"
    exit 1
fi

# 檢查是否包含舊的 Python 腳本
if grep -q "taiex_central_data_sync.py" /tmp/current_cron.txt; then
    echo "找到舊的 Python 排程，正在進行切換..."
    
    # 替換指令為新的 Swift 引擎
    # 這行會把 "python ... taiex_central_data_sync.py" 整段取代成 hermes_sync.swift
    sed -i '' -E 's|([^ ]*python[0-9]*[ ]+)?([^ ]*taiex_central_data_sync\.py)|/Users/bookid/.hermes/scripts/hermes_sync.swift|g' /tmp/current_cron.txt
    
    # 寫回 crontab
    crontab /tmp/current_cron.txt
    
    echo "✅ 成功將 Cron Job 切換至 Swift 引擎！"
    echo "目前的排程設定如下："
    crontab -l | grep "hermes_sync.swift"
else
    echo "⚠️ 找不到舊的 Python 同步排程，可能已經替換過，或原本就不存在。"
    
    # 如果原本連 swift 的也沒有，提示使用者
    if grep -q "hermes_sync.swift" /tmp/current_cron.txt; then
        echo "✅ 您的排程已經是 Swift 版本了！"
    fi
fi

# 清理暫存檔
rm -f /tmp/current_cron.txt
