#!/Users/bookid/.hermes/.venv/bin/python
import sys
import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
import yfinance as yf

# 1. Check if today is a trading day using 2330.TW
try:
    t = yf.Ticker("2330.TW")
    hist = t.history(period="1d")
    if hist.empty:
        print("今日無交易資料 (可能為休市)。")
        sys.exit(0)
        
    latest_date = hist.index[-1].strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")
    
    if latest_date != today:
        print(f"最新交易日為 {latest_date}，非今日 ({today})，判斷為休市，終止執行。")
        sys.exit(0)
except Exception as e:
    print(f"休市檢查失敗，預設繼續執行: {e}")

# 2. Run central data sync to ensure latest prices
print("Running central data sync...")
sync_script = os.path.expanduser("~/.hermes/scripts/taiex_central_data_sync.py")
subprocess.run([sys.executable, sync_script], capture_output=True)

# 3. Get portfolio and print report
print("Generating Portfolio Report...")
tool_script = os.path.expanduser("~/.hermes/scripts/portfolio_tool.py")
result = subprocess.run([sys.executable, tool_script, "--view"], capture_output=True, text=True)

report_text = f"📊 **最終資產統計 (對齊實際庫存)**\n\n```\n{result.stdout.strip()}\n```"
print(report_text)

# The cron runner (if deliver is origin/local) will capture stdout and send to Telegram.
