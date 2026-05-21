import requests
import json
import os
import re
from datetime import datetime
import pytz

def get_price_via_search(ticker):
    """
    Fallback method to get price via searching the web when yfinance is rate-limited.
    """
    from hermes_tools import web_search
    
    query_map = {
        "NQ=F": "Nasdaq 100 Futures real time price",
        "TSM": "TSM ADR real time price",
        "NVDA": "NVDA stock real time price",
        "SYNA": "SYNA stock real time price",
        "EWT": "iShares MSCI Taiwan ETF price",
        "FITXP": "台指期 報價",
        "WTXP": "台指期 夜盤 報價"
    }
    
    query = query_map.get(ticker, f"{ticker} real time price")
    search_results = web_search(query)
    
    if not search_results.get("success"):
        return None
        
    text = json.dumps(search_results.get("data", {}))
    
    # Try to find a number with a decimal point (price)
    # This is a very rough heuristic but better than nothing
    try:
        # Looking for patterns like "123.45" or "42,332"
        # Specifically targeting common price formats in snippets
        prices = re.findall(r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b', text)
        if prices:
            # Filter out small integers like "100", "2026", etc.
            filtered = [p.replace(',', '') for p in prices if float(p.replace(',', '')) > 20]
            if filtered:
                return float(filtered[0])
    except:
        pass
    return None

def get_market_data_resilient(tickers):
    import yfinance as yf
    import pandas as pd
    
    results = {}
    for sym, name in tickers.items():
        price = None
        pct = 0.0
        delta = 0.0
        
        try:
            # Try yfinance with short period to minimize data transfer
            t = yf.Ticker(sym)
            hist = t.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                prev_close = hist['Open'].iloc[0]
                delta = price - prev_close
                pct = (delta / prev_close) * 100
        except Exception as e:
            print(f"yfinance failed for {sym}: {e}")
            
        if price is None:
            print(f"Entering Fallback for {sym}...")
            # Fallback to search
            price = get_price_via_search(sym)
            if price is not None:
                # We don't easily get pct/delta from search without more parsing
                results[sym] = {"price": price, "pct": 0.0, "delta": 0.0, "source": "search", "name": name}
            else:
                results[sym] = {"price": 0.0, "pct": 0.0, "delta": 0.0, "source": "failed", "name": name}
        else:
            results[sym] = {"price": price, "pct": pct, "delta": delta, "source": "yfinance", "name": name}
            
    return results

if __name__ == "__main__":
    # Test
    tickers = {"TSM": "台積電 ADR", "NVDA": "輝達", "NQ=F": "那指期"}
    res = get_market_data_resilient(tickers)
    print(json.dumps(res, indent=2, ensure_ascii=False))
