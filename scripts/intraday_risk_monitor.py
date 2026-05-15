import os
import json
import pandas as pd
from datetime import datetime
import urllib.request
import urllib.parse
import ssl

DATA_DIR = os.path.expanduser("~/.hermes/data")
INTRADAY_LOG = os.path.join(DATA_DIR, "intraday_data_log.csv")
PREDICTIONS_FILE = os.path.join(DATA_DIR, "intraday_predictions.json")
ALERT_LOG = os.path.join(DATA_DIR, "ml_alerted_today.json")

TELEGRAM_TOKEN = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
CHAT_ID = "6326497055"

# 設定停損停利 % 數
LONG_TAKE_PROFIT = 0.03   # 偏多: 獲利 +3.0%
LONG_STOP_LOSS = -0.02    # 偏多: 虧損 -2.0%
SHORT_TAKE_PROFIT = -0.03 # 偏空: 獲利 -3.0% (價格下跌)
SHORT_STOP_LOSS = 0.02    # 偏空: 虧損 +2.0% (價格上漲)

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
        urllib.request.urlopen(req, context=ctx, timeout=5)
    except Exception as e:
        print(f"Telegram failed: {e}")

def load_alert_log():
    if os.path.exists(ALERT_LOG):
        try:
            with open(ALERT_LOG, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_alert_log(data):
    with open(ALERT_LOG, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def run_risk_monitor():
    if not os.path.exists(INTRADAY_LOG) or not os.path.exists(PREDICTIONS_FILE):
        return
        
    try:
        with open(PREDICTIONS_FILE, 'r') as f:
            preds = json.load(f)
    except:
        return
        
    if not preds:
        return
        
    today_str = datetime.now().date().isoformat()
    
    # 讀取警報紀錄，如果換日了就清空
    alert_log = load_alert_log()
    if alert_log.get("date") != today_str:
        alert_log = {"date": today_str, "alerted_codes": []}
        
    df = pd.read_csv(INTRADAY_LOG)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    today = datetime.now().date()
    df_today = df[df['timestamp'].dt.date == today]
    
    if df_today.empty:
        return
        
    # 取得每檔股票當天的最新價格與名稱
    latest_data = df_today.sort_values('timestamp').groupby('code').last()
    
    alerts = []
    
    for code, pred_info in preds.items():
        if code in alert_log["alerted_codes"]:
            continue # 今天已經叫過了，防洗版
            
        if code not in latest_data.index:
            continue
            
        prob = pred_info.get('prob', 0.5)
        prev_close = pred_info.get('price', 0)
        
        if prev_close <= 0:
            continue
            
        current_price = latest_data.loc[code, 'price']
        name = latest_data.loc[code, 'name']
        
        return_pct = (current_price - prev_close) / prev_close
        
        alert_msg = ""
        
        # 偏多預測 (勝率 > 55%)
        if prob > 0.55:
            if return_pct >= LONG_TAKE_PROFIT:
                alert_msg = f"🎯 **【多單停利】** {name} (`{code}`)\n漲幅已達 **{return_pct*100:+.2f}%**\n現價：{current_price} | 昨收：{prev_close}"
            elif return_pct <= LONG_STOP_LOSS:
                alert_msg = f"🛑 **【多單停損】** {name} (`{code}`)\n跌幅已達 **{return_pct*100:+.2f}%**\n現價：{current_price} | 昨收：{prev_close}"
                
        # 偏空預測 (勝率 < 45%)
        elif prob < 0.45:
            if return_pct <= SHORT_TAKE_PROFIT:
                alert_msg = f"🎯 **【空單停利】** {name} (`{code}`)\n跌幅已達 **{return_pct*100:+.2f}%**\n現價：{current_price} | 昨收：{prev_close}"
            elif return_pct >= SHORT_STOP_LOSS:
                alert_msg = f"🛑 **【空單停損】** {name} (`{code}`)\n漲幅已達 **{return_pct*100:+.2f}%**\n現價：{current_price} | 昨收：{prev_close}"
                
        if alert_msg:
            alerts.append(alert_msg)
            alert_log["alerted_codes"].append(code)
            
    if alerts:
        final_msg = "⚠️ **盤中 AI 自動風險監控警報**\n\n" + "\n\n".join(alerts)
        send_telegram(final_msg)
        save_alert_log(alert_log)
        print(f"已觸發 {len(alerts)} 筆盤中警報。")
        
if __name__ == "__main__":
    run_risk_monitor()
