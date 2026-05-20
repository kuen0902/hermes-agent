import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os
import json

def get_bridge_data(key):
    try:
        bridge_path = "/Users/bookid/.hermes/data/market_prices_bridge.json"
        if os.path.exists(bridge_path):
            with open(bridge_path, 'r') as f:
                data = json.load(f)
                return data.get(key)
    except:
        return None

def get_night_session_status():
    ticker_symbol = "NQ=F"
    taipei_tz = pytz.timezone('Asia/Taipei')
    report_time = datetime.now(taipei_tz).strftime("%Y-%m-%d %H:%M")
    
    data = None
    try:
        ticker = yf.Ticker(ticker_symbol)
        data = ticker.history(period="1d", interval="1m")
    except Exception as e:
        pass # Suppress output so it doesn't pollute the notification when falling back

    if data is None or data.empty:
        # --- BRIDGE FALLBACK ---
        current_price = get_bridge_data("NQ")
        if current_price:
            msg = [
                f"🌌 **台股夜盤指標 (Nasdaq Futures)**",
                f"⏰ 檢測時間：`{report_time}`",
                f"----------------------------",
                f"💰 **目前點數 (NQ)**：`{current_price:,.1f}`",
                f"📊 **狀態**：`PROXIED (Resilient Bridge)`",
                f"----------------------------"
            ]
            return "\n".join(msg)
        return "❌ [Health Check ERROR]: 無法獲取 NQ=F 數據。"

    # Normal Flow
    current_price = data['Close'].iloc[-1]
    open_price = data['Open'].iloc[0]
    last_update = data.index[-1]
    
    hour_ago = last_update - timedelta(hours=1)
    prev_data = data[data.index <= hour_ago]
    prev_hour_price = prev_data['Close'].iloc[-1] if not prev_data.empty else open_price
    
    session_change = current_price - open_price
    session_pct = (session_change / open_price) * 100
    hour_change = current_price - prev_hour_price
    hour_pct = (hour_change / prev_hour_price) * 100

    def get_color_emoji(val):
        if val > 0.05: return "🔴"
        if val < -0.05: return "🟢"
        return "⚪️"

    msg = [
        f"🌌 **台股夜盤指標 (Nasdaq Futures)**",
        f"⏰ 檢測時間：`{report_time}`",
        f"----------------------------",
        f"💰 **目前點數 (NQ)**：`{current_price:,.1f}`",
        f"",
        f"📊 **近期走勢 (Hourly)**",
        f"{get_color_emoji(hour_change)} 漲跌：`{hour_change:+.1f}` ({hour_pct:+.2f}%)",
        f"",
        f"📈 **全日變動 (vs NY Open)**",
        f"{get_color_emoji(session_change)} 漲跌：`{session_change:+.1f}` ({session_pct:+.2f}%)",
        f"----------------------------"
    ]
    return "\n".join(msg)

if __name__ == "__main__":
    print(get_night_session_status())
