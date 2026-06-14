#!/Users/bookid/.hermes/.venv/bin/python
import sys
import os
import subprocess
from datetime import datetime
import pytz
import requests

# 1. Check if today is a trading day using 2330.TW via direct Yahoo Chart API
try:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/2330.TW"
    r = requests.get(url, params={"range": "1d", "interval": "1d"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    if r.status_code != 200:
        print(f"今日交易資料獲取失敗 (HTTP {r.status_code})。")
        sys.exit(0)
        
    res = r.json()["chart"]["result"][0]
    ts = res["timestamp"][-1]
    taipei_tz = pytz.timezone("Asia/Taipei")
    latest_date = datetime.fromtimestamp(ts, taipei_tz).strftime("%Y-%m-%d")
    today = datetime.now(taipei_tz).strftime("%Y-%m-%d")
    
    if latest_date != today:
        print(f"最新交易日為 {latest_date}，非今日 ({today})，判斷為休市，終止執行。")
        sys.exit(0)
except Exception as e:
    print(f"休市檢查失敗，預設繼續執行: {e}")

# 2. Skip native Swift sync. Orchestrator provides central cache.

# 3. Get portfolio and print report
print("Generating Portfolio Report...")
tool_script = os.path.expanduser("~/.hermes/scripts/portfolio_tool.py")
result = subprocess.run([sys.executable, tool_script, "--view"], capture_output=True, text=True)

report_text = f"📊 **最終資產統計 (對齊實際庫存)**\n\n```\n{result.stdout.strip()}\n```"
print(report_text)


# The cron runner (if deliver is origin/local) will capture stdout and send to Telegram.
