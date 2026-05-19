#!/Users/bookid/.hermes/.venv/bin/python
import os
import sys
import json
import subprocess
import urllib.request
import urllib.parse
import ssl
from datetime import datetime

DATA_DIR = os.path.expanduser("~/.hermes/data")
SIGNALS_FILE = os.path.join(DATA_DIR, "trade_signals.json")
ARCHIVE_DIR = os.path.join(DATA_DIR, "trade_archive")
PORTFOLIO_TOOL = os.path.expanduser("~/.hermes/scripts/portfolio_tool.py")

# Using Star Platinum Token for executing alerts
TELEGRAM_TOKEN = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
CHAT_ID = "6326497055"  # Personal Jojo Chat

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    ctx = ssl._create_unverified_context()
    data = urllib.parse.urlencode({
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, context=ctx, timeout=10)
    except Exception as e:
        print(f"Telegram failed: {e}")

def run_orchestrator():
    print("--- Auto-Trading Orchestrator ---")
    if not os.path.exists(SIGNALS_FILE):
        print("無待處理的自動交易訊號。")
        return

    try:
        with open(SIGNALS_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"讀取訊號檔失敗: {e}")
        return

    signals = data.get("signals", [])
    if not signals:
        print("訊號檔為空。")
        return

    messages = ["🤖 **AI 聯動自動交易執行報告**\n"]
    
    for sig in signals:
        action = sig.get("action")
        code = sig.get("code")
        name = sig.get("name")
        price = sig.get("price")
        qty = sig.get("qty", 1.0)
        prob = sig.get("prob", 0)
        
        icon = "📈 加碼" if action == "add" else "📉 減碼"
        print(f"執行 {icon}: {name}({code}) {qty}張 @ {price}")
        
        cmd = [sys.executable, PORTFOLIO_TOOL]
        if action == "add":
            cmd.extend(["--add", str(code), str(qty), str(price)])
        elif action == "reduce":
            cmd.extend(["--reduce", str(code), str(qty), str(price)])
            
        result = subprocess.run(cmd, capture_output=True, text=True)
        out = result.stdout.strip()
        
        if out:
            # Clean output for markdown
            clean_out = out.replace("*", "\\*").replace("_", "\\_")
            messages.append(f"**訊號**: {name} ({code}) - ML 勝率 {prob*100:.1f}%\n`{clean_out}`\n")

    if len(messages) > 1:
        final_msg = "\n".join(messages)
        send_telegram(final_msg)
        print("已發送執行報告至 Telegram。")

    # Archive the processed signals
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    archive_path = os.path.join(ARCHIVE_DIR, f"signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    os.rename(SIGNALS_FILE, archive_path)
    print(f"訊號已封存至: {archive_path}")

if __name__ == "__main__":
    run_orchestrator()
