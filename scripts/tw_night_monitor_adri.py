import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import os
import json
import requests

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

def get_market_data():
    tickers = {"EWT": "MSCI 台灣 ETF", "TSM": "台積電 ADR", "NVDA": "輝達 (AI 領先)", "SYNA": "新思 (Human Interface)"}
    data_results = {}
    bridge = get_bridge_data()
    prev_close_cache = get_prev_close_cache()
    errors = []
    
    for sym, name in tickers.items():
        price = None
        prev_close = None
        source = "yfinance"
        
        # 1. 優先使用 history(period="2d", prepost=True) 獲取最可靠的當前價與昨收價
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="2d", prepost=True)
            if not hist.empty:
                if len(hist) >= 2:
                    price = float(hist['Close'].iloc[-1])
                    prev_close = float(hist['Close'].iloc[-2])
                    source = "yf_hist"
                elif len(hist) == 1:
                    price = float(hist['Close'].iloc[-1])
                    prev_close = float(hist['Open'].iloc[0])
                    source = "yf_hist_1d"
                    # 嘗試從 info 中獲取更精確的昨收價
                    try:
                        info_pc = ticker.info.get('previousClose')
                        if info_pc:
                            prev_close = float(info_pc)
                    except:
                        pass
        except Exception as e:
            pass
            
        # 2. 第二層級備份：使用 basic_info 或 info 屬性
        if price is None or prev_close is None:
            try:
                ticker = yf.Ticker(sym)
                info = ticker.info
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
                if price is not None and prev_close is not None:
                    price = float(price)
                    prev_close = float(prev_close)
                    source = "yf_info"
            except Exception as e:
                pass
                
        # 3. 第三層級備份：使用 fast_info 屬性
        if price is None or prev_close is None:
            try:
                ticker = yf.Ticker(sym)
                fast_info = ticker.fast_info
                try:
                    price = fast_info['last_price']
                    prev_close = fast_info['previous_close']
                except (TypeError, KeyError):
                    price = getattr(fast_info, 'last_price', None)
                    prev_close = getattr(fast_info, 'previous_close', None)
                
                if price is not None and prev_close is not None:
                    price = float(price)
                    prev_close = float(prev_close)
                    source = "yf_fast"
            except Exception as e:
                pass
                
        # 4. 第四層級備份：當 yfinance 完全失敗時，使用 bridge 價格，但仍嘗試單獨獲取 yfinance 的昨收價以進行計算
        if price is None or prev_close is None:
            if sym in bridge:
                price = bridge[sym]
                source = "bridge"
                
                # 嘗試單獨獲取昨收價
                try:
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(period="2d", prepost=True)
                    if not hist.empty and len(hist) >= 2:
                        prev_close = float(hist['Close'].iloc[-2])
                        source = "bridge+yf_prev"
                    elif not hist.empty:
                        prev_close = float(hist['Open'].iloc[0])
                        source = "bridge+yf_prev"
                except Exception as e:
                    pass
                    
                if prev_close is None:
                    try:
                        ticker = yf.Ticker(sym)
                        prev_pc = ticker.info.get('previousClose')
                        if prev_pc:
                            prev_close = float(prev_pc)
                            source = "bridge+yf_prev"
                    except Exception as e:
                        pass

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
            # 只有價格但沒有昨收，只能顯示 0.0%
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
    
    # 5. 台指期 (FITXP) 處理：使用 bridge 中的夜盤即時點數，並從 yfinance 獲取 TXF1=TW 或 ^TWII 的昨收計算真正漲跌幅
    if "FITXP" in bridge:
        fitxp_price = bridge["FITXP"]
        fitxp_prev_close = None
        proxy_used = "None"
        
        for proxy in ["TXF1=TW", "^TWII"]:
            try:
                t = yf.Ticker(proxy)
                hist = t.history(period="2d")
                if not hist.empty:
                    if len(hist) >= 2:
                        fitxp_prev_close = float(hist['Close'].iloc[-2])
                    else:
                        fitxp_prev_close = float(hist['Close'].iloc[-1])
                    if fitxp_prev_close:
                        proxy_used = proxy
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
