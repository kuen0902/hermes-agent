#!/bin/bash
set -e

cd /Users/bookid/.hermes

echo "📌 加入 .gitignore 規則，避免誤傳編譯好的執行檔..."
# 確保忽略無副檔名的執行檔，但不影響資料夾
echo "scripts/hermes_orchestrator" >> .gitignore
echo "scripts/hermes_sync" >> .gitignore
echo "scripts/hermes_monitor" >> .gitignore
git add .gitignore

echo "📌 將所有 Python、Swift、Shell 與 JSON 設定檔加入追蹤..."
git add scripts/*.py
git add scripts/*.swift
git add scripts/*.sh
git add -f cron/jobs.json

echo "📌 提交本次架構升級的版本紀錄..."
git commit -m "feat(ml): Upgrade to 5-Min high frequency pipeline and implement RSI/MACD feature engineering"

echo "📌 推送至遠端 FEATURE-IMPLEMENT_SWIFT 分支..."
git push origin FEATURE-IMPLEMENT_SWIFT

echo "✅ 備份與同步完成！所有的程式碼都已安全地上傳至遠端儲存庫。"
