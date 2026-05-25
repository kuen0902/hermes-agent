#!/Users/bookid/.hermes/.venv/bin/python
import os
import json
import requests
import urllib3
from datetime import datetime

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
DATA_DIR = os.path.expanduser("~/.hermes/data")
JSON_PATH = os.path.join(DATA_DIR, "top_50_potential_stocks.json")

# Telegram Star Platinum Configuration
TELEGRAM_TOKEN = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
TELEGRAM_CHAT_ID = "6326497055"

def send_telegram(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        r = requests.post(url, data=payload, timeout=15, verify=False)
        if r.status_code == 200:
            print("🎉 Telegram message sent successfully to Star Platinum!")
        else:
            print(f"❌ Failed to send Telegram: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ Telegram connection failed: {e}")

def main():
    print("Preparing Top 30 Potential Stocks Telegram Report...")
    
    if not os.path.exists(JSON_PATH):
        print(f"❌ Top 50 potential stocks JSON not found at {JSON_PATH}")
        return
        
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        top_50 = json.load(f)
        
    top_30 = top_50[:30]
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Construct a beautiful premium Telegram Markdown message
    msg_lines = [
        f"🎖️ **HERMES QUANT: 30 檔最佳波段潛力選股**",
        f"📅 **日期**：{today_str}",
        f"📈 **模型選股基礎**：14年日線主力籌碼與信用多因子 XGBoost 預測引擎",
        f"----------------------------------------"
    ]
    
    for stock in top_30:
        rank = stock['rank']
        ticker = stock['ticker']
        code = stock['code']
        name = stock['name'].replace('*', '\\*').replace('_', '\\_')
        close = stock['close']
        pred_ret = stock['predicted_return_20d'] * 100.0
        dual_5d = stock['dual_force_5d']
        
        # Highlight large institutional buyings
        chip_str = ""
        if dual_5d >= 1000.0:
            chip_str = f" | 🔥 **5D法人: {dual_5d:,.0f}張**"
        elif dual_5d > 10.0:
            chip_str = f" | 5D法人: {dual_5d:,.0f}張"
            
        msg_lines.append(
            f"*{rank:02d}.* **{name}** (`{code}`): 價 *{close:.2f}* | 預估20D: *{pred_ret:+.2f}%*{chip_str}"
        )
        
    msg_lines.append(f"----------------------------------------")
    msg_lines.append(f"💡 *量化警示：本報告為機器學習波段預測之評分排序，請配合5分K卡爾曼動能引擎進行日內交易點位校準。祝交易順利！*")
    
    full_message = "\n".join(msg_lines)
    
    # Send it (will attempt but might fail in sandbox, print instructions if so)
    print("Sending message...")
    send_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, full_message)

if __name__ == "__main__":
    main()
