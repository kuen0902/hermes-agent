import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import os

# Configuration
SAVE_FILE = os.path.expanduser("~/.hermes/data/night_session_last.json")
os.makedirs(os.path.dirname(SAVE_FILE), exist_ok=True)

def get_market_data():
    # Indicators: EWT (Taiwan Proxy), TSM (TSMC ADR), NVDA (AI Lead)
    tickers = {"EWT": "MSCI 台灣 ETF", "TSM": "台積電 ADR", "NVDA": "輝達 (AI 領先)", "SYNA": "新思 (Human Interface)"}
    data_results = {}
    
    health_status = "Healthy"
    errors = []
    
    for sym, name in tickers.items():
        try:
            t = yf.Ticker(sym)
            # Use 1m interval to capture pre-market micro-movements
            hist = t.history(period="1d", interval="1m")
            if hist.empty:
                # Fallback to 1h if 1m is somehow missing (rare for these high volume tickers)
                hist = t.history(period="2d", interval="1h")
            
            if hist.empty:
                errors.append(f"{sym} 數據為空")
                continue
            
            info = t.info
            # CRITICAL: Use preMarketPrice if we are in pre-market hours
            current_price = info.get('preMarketPrice') or info.get('regularMarketPrice') or hist['Close'].iloc[-1]
            
            # Use 1 hour ago price for trend
            hour_ago_idx = hist.index[-1] - pd.Timedelta(hours=1)
            prev_hour_data = hist[hist.index <= hour_ago_idx]
            prev_price = prev_hour_data['Close'].iloc[-1] if not prev_hour_data.empty else hist['Open'].iloc[0]
            
            prev_close = info.get('previousClose', prev_price)
            
            data_results[sym] = {
                "name": name,
                "price": current_price,
                "session_delta_abs": current_price - prev_close,
                "hour_delta": ((current_price - prev_price) / prev_price) * 100,
                "session_delta": ((current_price - prev_close) / prev_close) * 100
            }
        except Exception as e:
            # --- WEB FALLBACK (GER ULTIMATE DEFENSE) ---
            try:
                # Basic search for real-time price as fallback
                # Note: In a production script, this would use a reliable API or scraping lib
                # Here we just log that we would enter GER fallback mode
                errors.append(f"{sym} 需啟動 GER 備援抓取")
            except:
                errors.append(f"{sym} 抓取失敗: {str(e)}")

    if errors:
        health_status = f"Unhealthy ({', '.join(errors)})"
    
    return data_results, health_status

def format_report(results, health):
    taipei_tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(taipei_tz).strftime("%Y-%m-%d %H:%M")
    
    lines = [
        f"🌌 **台股夜盤監測 (美股領先指標)**",
        f"⏰ 時間：`{now}`",
        f"----------------------------"
    ]
    
    def get_emoji(val):
        if val > 0.05: return "🔴" 
        if val < -0.05: return "🟢" 
        return "⚪️"

    # --- PERSISTENCE OVERHAUL: INTEGRATE GER/SP DELIVERY ---
    try:
        from lib_market_delivery import deliver_market_report
        # Extract structured data for delivery
        structured_data = {
            "FITXP": {"price": results.get("FITXP", {}).get("price", 0), "delta": results.get("FITXP", {}).get("session_delta_abs", 0), "pct": results.get("FITXP", {}).get("session_delta", 0)},
            "TSM": {"price": results.get("TSM", {}).get("price", 0), "delta": results.get("TSM", {}).get("session_delta_abs", 0), "pct": results.get("TSM", {}).get("session_delta", 0)},
            "NVDA": {"price": results.get("NVDA", {}).get("price", 0), "delta": results.get("NVDA", {}).get("session_delta_abs", 0), "pct": results.get("NVDA", {}).get("session_delta", 0)},
            "SYNA": {"price": results.get("SYNA", {}).get("price", 0), "delta": results.get("SYNA", {}).get("session_delta_abs", 0), "pct": results.get("SYNA", {}).get("session_delta", 0)}
        }
        # If price is missing from results, use a placeholder or log error
        deliver_market_report(structured_data)
    except Exception as e:
        print(f"Delivery Module Error: {str(e)}")

    ewt = results.get("EWT")
    if ewt:
        impact_est = ewt['session_delta'] * 1.0 # 1:1 roughly for EWT to TAIEX
        lines.append(f"📊 **近期走勢：{get_emoji(impact_est)} 估計變動 `{impact_est:+.1f}%`**")
        lines.append("")

    for sym, val in results.items():
        lines.append(f"**{val['name']} ({sym})**")
        lines.append(f"- 價格：`${val['price']:.2f}`")
        lines.append(f"- 每小時：{get_emoji(val['hour_delta'])} `{val['hour_delta']:+.2f}%` ")
        lines.append(f"- 較昨收：{get_emoji(val['session_delta'])} `{val['session_delta']:+.2f}%` ")
        lines.append("")

    lines.append(f"----------------------------")
    lines.append(f"🛡️ 健康檢查：`{health}`")
    lines.append(f"💡 *註：美股開盤前優先參考 Pre-Market 數據。*")
    
    return "\n".join(lines)

if __name__ == "__main__":
    results, health = get_market_data()
    print(format_report(results, health))
