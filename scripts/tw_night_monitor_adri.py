from datetime import datetime
import pytz
import os
import json
import requests
import time
import random

# Configuration
SAVE_FILE = os.path.expanduser("~/.hermes/data/night_session_last.json")
BRIDGE_FILE = os.path.expanduser("~/.hermes/data/market_prices_bridge.json")
CACHE_FILE = os.path.expanduser("~/.hermes/data/night_session_tier_cache.json")
PREV_CLOSE_FILE = os.path.expanduser("~/.hermes/data/night_session_prev.json")
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

def get_prev_close_cache():
    if os.path.exists(PREV_CLOSE_FILE):
        try:
            with open(PREV_CLOSE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def fetch_yahoo_chart_direct(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
    params = {
        "range": "2d",
        "interval": "1d",
        "includePrePost": "true"
    }
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0"
    ]
    max_retries = 3
    base_delay = 1.0
    price = None
    prev_close = None
    source = "direct_api"
    
    for attempt in range(max_retries):
        headers = {'User-Agent': random.choice(user_agents)}
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                result = data["chart"]["result"][0]
                meta = result.get("meta", {})
                
                price = meta.get("regularMarketPrice")
                prev_close = meta.get("chartPreviousClose")
                
                closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
                valid_closes = [c for c in closes if c is not None]
                
                if price is None and valid_closes:
                    price = valid_closes[-1]
                
                if prev_close is None:
                    if len(valid_closes) >= 2:
                        prev_close = valid_closes[-2]
                    elif len(valid_closes) == 1:
                        prev_close = valid_closes[0]
                
                if price is not None:
                    price = float(price)
                if prev_close is not None:
                    prev_close = float(prev_close)
                
                if price is not None:
                    return price, prev_close, f"direct_api_attempt_{attempt + 1}"
            elif r.status_code == 429:
                source = f"direct_api_429_attempt_{attempt + 1}"
            else:
                source = f"direct_api_err_{r.status_code}_attempt_{attempt + 1}"
        except Exception as e:
            source = f"direct_api_exc_{type(e).__name__}_attempt_{attempt + 1}"
            
        if attempt < max_retries - 1:
            time.sleep(base_delay * (2 ** attempt) + random.uniform(0.1, 0.5))
            
    return price, prev_close, source

def get_market_data():
    tickers = {"EWT": "MSCI 台灣 ETF", "TSM": "台積電 ADR", "NVDA": "輝達 (AI 領先)", "SYNA": "新思 (Human Interface)"}
    data_results = {}
    bridge = get_bridge_data()
    prev_close_cache = get_prev_close_cache()
    errors = []
    
    for sym, name in tickers.items():
        price = None
        prev_close = None
        source = "direct_api"
        
        # 1. 優先使用直連 API 獲取
        price, prev_close, source = fetch_yahoo_chart_direct(sym)
                
        # 2. 當直連 API 失敗時，使用 bridge 價格，但仍嘗試單獨獲取直連 API 的昨收價
        if price is None or prev_close is None:
            if sym in bridge:
                price = bridge[sym]
                source = "bridge"
                
                # 嘗試單獨獲取昨收價
                _, pc_fallback, _ = fetch_yahoo_chart_direct(sym)
                if pc_fallback is not None:
                    prev_close = pc_fallback
                    source = "bridge+direct_prev"

        # 從快取讀取備份昨收價
        if prev_close is None and sym in prev_close_cache:
            prev_close = prev_close_cache[sym]
            source += "+cache_prev"
            
        # 更新快取
        if prev_close is not None:
            prev_close_cache[sym] = prev_close

        # 寫入最終獲取結果
        if price is not None and prev_close is not None:
            data_results[sym] = {
                "name": name,
                "price": float(price),
                "session_delta_abs": float(price - prev_close),
                "hour_delta": 0.0,
                "session_delta": float(((price - prev_close) / prev_close) * 100) if prev_close else 0.0,
                "source": source
            }
        elif price is not None:
            data_results[sym] = {
                "name": name,
                "price": float(price),
                "session_delta_abs": 0.0,
                "hour_delta": 0.0,
                "session_delta": 0.0,
                "source": f"{source}_no_prev"
            }
        else:
            errors.append(f"{sym} 數據獲取失敗")

    health = "Healthy" if not errors else f"Degraded ({', '.join(errors)})"
    
    # 3. 台指期 (FITXP) 處理：使用 bridge 中的夜盤即時點數，並從直連 API 獲取 TXF1=TW 或 ^TWII 的昨收計算真正漲跌幅
    if "FITXP" in bridge:
        fitxp_price = bridge["FITXP"]
        fitxp_prev_close = None
        proxy_used = "None"
        
        for proxy in ["TXF1=TW", "^TWII"]:
            try:
                _, pc_val, _ = fetch_yahoo_chart_direct(proxy)
                if pc_val is not None:
                    fitxp_prev_close = pc_val
                    proxy_used = f"direct_{proxy}"
                    break
            except:
                pass
                
        if fitxp_prev_close is None and "FITXP" in prev_close_cache:
            fitxp_prev_close = prev_close_cache["FITXP"]
            proxy_used = "cache"

        if fitxp_prev_close is not None:
            prev_close_cache["FITXP"] = fitxp_prev_close
            data_results["FITXP"] = {
                "name": "台指期 (夜)",
                "price": fitxp_price,
                "session_delta_abs": float(fitxp_price - fitxp_prev_close),
                "hour_delta": 0.0,
                "session_delta": float(((fitxp_price - fitxp_prev_close) / fitxp_prev_close) * 100),
                "source": f"bridge+{proxy_used}_prev"
            }
        else:
            data_results["FITXP"] = {
                "name": "台指期 (夜)",
                "price": fitxp_price,
                "session_delta_abs": 0.0,
                "hour_delta": 0.0,
                "session_delta": 0.0,
                "source": "bridge_fallback"
            }

    with open(PREV_CLOSE_FILE, 'w') as f:
        json.dump(prev_close_cache, f)

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
    
    untriggered = []
    
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
        else:
            untriggered.append(f"{sym.split('.')[0]}: {pct:+.1f}%")
            
        cache[sym] = current_tier

    # Save Cache
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

    if untriggered:
        lines.append(f"   ▸ 未達推播門檻：`" + ", ".join(untriggered) + "`")

    if not delivery_data:
        return "\n".join(lines), False

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
