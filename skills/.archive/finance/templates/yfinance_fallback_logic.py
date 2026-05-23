import yfinance as yf
from datetime import datetime

def fetch_yfinance_fallback(codes):
    """
    Fallback mechanism for when the TAIEX Official API misses symbols 
    (e.g., Emerging Market stocks or newly listed tickers).
    """
    results = {}
    if not codes: return results
    
    # Check both .TW (TSE) and .TWO (OTC/Emerging)
    for c in codes:
        for suffix in [".TW", ".TWO"]:
            sym = f"{c}{suffix}"
            try:
                t = yf.Ticker(sym)
                info = t.info
                # Current price might be under different keys depending on session status
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                prev = info.get('previousClose')
                
                if price and prev:
                    results[c] = {
                        "symbol": sym,
                        "price": float(price),
                        "volume": int(info.get('volume', 0)),
                        "prev_close": float(prev),
                        "change": float(price - prev),
                        "pct": float((price - prev) / prev * 100),
                        "time": datetime.now().isoformat()
                    }
                    break # Success, don't check other suffix
            except Exception:
                continue
    return results
