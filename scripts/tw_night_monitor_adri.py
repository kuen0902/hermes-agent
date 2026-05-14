import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import os
import json

# Configuration
SAVE_FILE = os.path.expanduser("~/.hermes/data/night_session_last.json")
BRIDGE_FILE = os.path.expanduser("~/.hermes/data/market_prices_bridge.json")
os.makedirs(os.path.dirname(SAVE_FILE), exist_ok=True)

def get_bridge_data():
    if os.path.exists(BRIDGE_FILE):
        with open(BRIDGE_FILE, 'r') as f:
            return json.load(f)
    return {}

def get_market_data():
    tickers = {"EWT": "MSCI 台灣 ETF", "TSM": "台積電 ADR", "NVDA": "輝達 (AI 領先)", "SYNA": "新思 (Human Interface)"}
    data_results = {}
    bridge = get_bridge_data()
    errors = []
    
    for sym, name in tickers.items():
        price = None
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                prev_close = hist['Open'].iloc[0]
                data_results[sym] = {
                    "name": name,
                    "price": price,
                    "session_delta_abs": price - prev_close,
                    "hour_delta": 0.0,
                    "session_delta": ((price - prev_close) / prev_close) * 100 if prev_close else 0,
                    "source": "yfinance"
                }
        except:
            pass
            
        if sym not in data_results:
            # Fallback to bridge
            if sym in bridge:
                price = bridge[sym]
                data_results[sym] = {
                    "name": name,
                    "price": price,
                    "session_delta_abs": 0.0,
                    "hour_delta": 0.0,
                    "session_delta": 0.0,
                    "source": "bridge"
                }
            else:
                errors.append(f"{sym} 數據獲取失敗")

    health = "Healthy" if not errors else f"Degraded ({', '.join(errors)})"
    
    # Add FITXP if in bridge
    if "FITXP" in bridge:
        data_results["FITXP"] = {
            "name": "台指期 (夜)",
            "price": bridge["FITXP"],
            "session_delta_abs": 0.0,
            "hour_delta": 0.0,
            "session_delta": 0.0,
            "source": "bridge"
        }

    return data_results, health

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

    # Integration with delivery module
    try:
        from lib_market_delivery import deliver_market_report
        # Prepare structured data (use current prices from results)
        delivery_data = {
            "FITXP": {"price": results.get("FITXP", {}).get("price", 0), "pct": 0.0},
            "TSM": {"price": results.get("TSM", {}).get("price", 0), "pct": results.get("TSM", {}).get("session_delta", 0)},
            "NVDA": {"price": results.get("NVDA", {}).get("price", 0), "pct": results.get("NVDA", {}).get("session_delta", 0)},
            "SYNA": {"price": results.get("SYNA", {}).get("price", 0), "pct": results.get("SYNA", {}).get("session_delta", 0)}
        }
        deliver_market_report(delivery_data)
    except Exception as e:
        print(f"Delivery error: {e}")

    for sym, val in results.items():
        if sym == "FITXP": continue
        lines.append(f"**{val['name']} ({sym})**")
        lines.append(f"- 價格：`${val['price']:.2f}` (via {val['source']})")
        lines.append(f"- 較昨收：{get_emoji(val['session_delta'])} `{val['session_delta']:+.2f}%` ")
        lines.append("")

    if "FITXP" in results:
        lines.append(f"📌 **台指期 (夜盤)**")
        lines.append(f"- 價格：`{results['FITXP']['price']}`")
        lines.append("")

    return "\n".join(lines)

if __name__ == "__main__":
    results, health = get_market_data()
    report = format_report(results, health)
    if health != "Healthy":
        report += f"\n----------------------------\n🛡️ 健康檢查：`{health}`"
    print(report)
