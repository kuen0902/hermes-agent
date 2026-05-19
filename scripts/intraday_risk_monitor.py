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

# Profiles Configuration
PROFILES = {
    "personal": {
        "token": "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU",
        "chat_id": "6326497055",
        "title": "💎 核心持股 AI 風險監控"
    },
    "group": {
        "token": "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU",
        "chat_id": "-1003744330314",
        "title": "👩‍👩‍👧‍👦 群組關注檔 AI 風險監控"
    },
    "william": {
        "token": "8678817340:AAFSB4rY-KizV6vN5nO-F-aL-9WEGQ",
        "chat_id": "8695583357",
        "title": "👨‍💻 William 監控清單警報"
    }
}

# 設定停損停利 % 數
LONG_TAKE_PROFIT = 0.03
LONG_STOP_LOSS = -0.02
SHORT_TAKE_PROFIT = -0.03
SHORT_STOP_LOSS = 0.02

def send_telegram(message, profile="personal"):
    p_cfg = PROFILES.get(profile, PROFILES["personal"])
    url = f"https://api.telegram.org/bot{p_cfg['token']}/sendMessage"
    ctx = ssl._create_unverified_context()
    data = urllib.parse.urlencode({
        'chat_id': p_cfg['chat_id'],
        'text': message,
        'parse_mode': 'Markdown'
    }).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, context=ctx, timeout=5)
    except Exception as e:
        print(f"Telegram ({profile}) failed: {e}")

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
    alert_log = load_alert_log()
    if alert_log.get("date") != today_str:
        alert_log = {"date": today_str, "alerted_codes": []}
        
    df = pd.read_csv(INTRADAY_LOG)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df_today = df[df['timestamp'].dt.date == datetime.now().date()]
    
    if df_today.empty:
        return
        
    latest_data = df_today.sort_values('timestamp').groupby('code').last()
    
    CENTRAL_DATA = os.path.join(DATA_DIR, "central_stock_data.json")
    personal_codes, william_codes, group_codes = [], [], []
    if os.path.exists(CENTRAL_DATA):
        try:
            with open(CENTRAL_DATA, 'r') as f:
                c_data = json.load(f)
                personal_codes = list(c_data.get("personal_data", {}).keys())
                william_codes = c_data.get("william_codes", [])
                group_codes = c_data.get("group_codes", [])
        except: pass

    profile_alerts = {"personal": [], "group": [], "william": []}
    
    for code, pred_info in preds.items():
        if code in alert_log["alerted_codes"] or code not in latest_data.index:
            continue
            
        prob = pred_info.get('prob', 0.5)
        prev_close = pred_info.get('price', 0)
        if prev_close <= 0: continue
            
        current_price = latest_data.loc[code, 'price']
        name = latest_data.loc[code, 'name']
        return_pct = (current_price - prev_close) / prev_close
        
        alert_msg = ""
        if prob > 0.55:
            if return_pct >= LONG_TAKE_PROFIT:
                alert_msg = f"🎯 **【多單停利】** {name} (`{code}`)\n漲幅已達 **{return_pct*100:+.2f}%**\n現價：{current_price} | 昨收：{prev_close}"
            elif return_pct <= LONG_STOP_LOSS:
                alert_msg = f"🛑 **【多單停損】** {name} (`{code}`)\n跌幅已達 **{return_pct*100:+.2f}%**\n現價：{current_price} | 昨收：{prev_close}"
        elif prob < 0.45:
            if return_pct <= SHORT_TAKE_PROFIT:
                alert_msg = f"🎯 **【空單停利】** {name} (`{code}`)\n跌幅已達 **{return_pct*100:+.2f}%**\n現價：{current_price} | 昨收：{prev_close}"
            elif return_pct >= SHORT_STOP_LOSS:
                alert_msg = f"🛑 **【空單停損】** {name} (`{code}`)\n漲幅已達 **{return_pct*100:+.2f}%**\n現價：{current_price} | 昨收：{prev_close}"
                
        if alert_msg:
            if code in personal_codes: profile_alerts["personal"].append(alert_msg)
            if code in group_codes: profile_alerts["group"].append(alert_msg)
            if code in william_codes: profile_alerts["william"].append(alert_msg)
            alert_log["alerted_codes"].append(code)
            
    sent_count = 0
    for p_key, alerts in profile_alerts.items():
        if alerts:
            title = PROFILES[p_key]["title"]
            final_msg = f"⚠️ {title}\n\n" + "\n\n".join(alerts)
            send_telegram(final_msg, profile=p_key)
            sent_count += len(alerts)

    if sent_count > 0:
        save_alert_log(alert_log)
        print(f"Executed {sent_count} alerts.")

if __name__ == "__main__":
    run_risk_monitor()
