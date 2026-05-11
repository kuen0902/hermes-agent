import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz

def get_night_session_status():
    # Ticker for Nasdaq Futures (Leading proxy for Taiwan Night Session/AI)
    # Since WTX=F is broken on Yahoo, NQ=F is the best operational lead.
    ticker_symbol = "NQ=F"
    
    try:
        ticker = yf.Ticker(ticker_symbol)
        data = ticker.history(period="1d", interval="1m")
        
        if data.empty:
            return "❌ [Health Check ERROR]: 無法獲取 NQ=F 數據。"
        
        last_update = data.index[-1]
        taipei_tz = pytz.timezone('Asia/Taipei')
        now_taipei = datetime.now(taipei_tz)
        
        # Check freshness
        if (now_taipei - last_update.astimezone(taipei_tz)).total_seconds() > 3600:
             return f"⚠️ [Health Check WARNING]: 數據延遲 (最後更新: {last_update.astimezone(taipei_tz).strftime('%H:%M')})"

    except Exception as e:
        return f"❌ [Health Check ERROR]: {str(e)}"

    current_price = data['Close'].iloc[-1]
    open_price = data['Open'].iloc[0]
    
    # Prev hour calculation
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

    report_time = datetime.now(taipei_tz).strftime("%Y-%m-%d %H:%M")
    
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
        f"----------------------------",
        f"✅ 狀態：Healthy (Pivoted to NQ=F)"
    ]
    
    return "\n".join(msg)

if __name__ == "__main__":
    print(get_night_session_status())
