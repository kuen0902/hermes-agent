import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import os
import json

# Configuration
SAVE_FILE = os.path.expanduser("~/.hermes/data/night_session_last.json")
BRIDGE_FILE = os.path.expanduser("~/.hermes/data/market_prices_bridge.json")
CACHE_FILE = os.path.expanduser("~/.hermes/data/night_session_tier_cache.json")
os.makedirs(os.path.dirname(SAVE_FILE), exist_ok=True)

TIERS = [3.0, 5.0, 7.0, 9.0]

def get_current_tier(pct: float) -> int:
    abs_pct = abs(pct)
    crossed = 0
    for t in TIERS:
        if abs_pct >= t:
            crossed = int(t)
    return crossed * (1 if pct >= 0 else -1)

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
    
    # Load Cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
        except:
            pass

    delivery_data = {}
    lines = []
    
    def get_emoji(val):
        if val > 0: return "🔴" 
        if val < 0: return "🟢" 
        return "⚪️"

    lines.append(f"🌌 **台股夜盤監測 (階梯突破)**")
    lines.append(f"⏰ 時間：`{now}`")
    lines.append(f"💡 *條件：跨越 ±3%, ±5%, ±7%, ±9%*")
    lines.append(f"----------------------------")
    
    for sym, val in results.items():
        pct = val['session_delta']
        current_tier = get_current_tier(pct)
        last_tier = cache.get(sym, 0)
        
        # Only trigger if crossed a NEW tier (and not 0)
        if current_tier != 0 and current_tier != last_tier:
            delivery_data[sym] = {
                "name": val['name'],
                "price": val['price'],
                "pct": pct,
                "tier": current_tier
            }
            trend = "🚀" if abs(current_tier) > abs(last_tier) else "📉"
            lines.append(f"{get_emoji(pct)}{trend} **{val['name']}** ({sym})")
            lines.append(f"   ▸ 價格：`${val['price']:.2f}` (via {val['source']})")
            lines.append(f"   ▸ 較昨收：`{pct:+.2f}%` (突破 `{current_tier}%` 門檻)")
            lines.append("")
            
        cache[sym] = current_tier

    # Save Cache
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

    if not delivery_data:
        return "[SILENT]", False

    # Integration with delivery module
    try:
        from lib_market_delivery import deliver_market_report
        deliver_market_report(delivery_data)
    except Exception as e:
        print(f"Delivery error: {e}")

    return "\n".join(lines), True

if __name__ == "__main__":
    results, health = get_market_data()
    report, delivered = format_report(results, health)
    if delivered and health != "Healthy":
        report += f"\n----------------------------\n🛡️ 健康檢查：`{health}`"
    print(report)
