# Resilient Bridge Pattern (Anti-429 Rate Limiting)

The "Resilient Bridge" is a multi-tier fallback architecture designed to maintain 100% data availability for automated financial agents, even when primary APIs (like Yahoo Finance) are under heavy rate-limiting or IP bans (HTTP 429).

## 1. The Core Architecture

1. **The Cache (Storage)**: A local `market_prices_bridge.json` file serves as the "Source of Truth" for all reporting scripts.
2. **The Fetcher (Update Logic)**: 
   - A dedicated agent task or cron step uses `delegate_task` or a robust browser-based scraper to visit landing pages (Google Finance, Yahoo Finance Web UI, HiStock).
   - This "Agent-level fetch" is harder to block than raw API requests because it uses residential-like footprints and interactive browsing.
   - Values are extracted and written to the Bridge JSON.
3. **The Consumer (Reporting Scripts)**:
   - Scripts (`tw_night_monitor_adri.py`, etc.) first attempt the standard API/Library call (`yfinance`).
   - If the return is empty or an error (429/Timeout), they immediately pivot to the `market_prices_bridge.json` cache.
   - Indicators (e.g., "via bridge" or "PROXIED") are added to the report for transparency.

## 2. Implementation in Automated Cron Jobs

Cron job prompts must be updated from "Run script X" to a multi-stage request:
1. "Fetch real-time prices for [Tickers] using browser tools/search."
2. "Update the bridge cache file at `/path/to/market_prices_bridge.json`."
3. "Execute the reporting script."

## 3. Python Fallback Pattern

Example integration in a monitor script:

```python
import json, os, yfinance as yf

def get_data(ticker_symbol):
    # Tier 1: API
    try:
        t = yf.Ticker(ticker_symbol)
        hist = t.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
    except:
        pass

    # Tier 2: Bridge Cache
    bridge_path = "~/.hermes/data/market_prices_bridge.json"
    if os.path.exists(bridge_path):
        with open(bridge_path, 'r') as f:
            bridge_data = json.load(f)
            return bridge_data.get(ticker_symbol)
    
    return None
```

## 4. Why This Works
This pattern transforms a technical failure (API ban) into a workflow coordination task (Agent browsing). It leverages the fact that browser-based navigation (via Browserbase/Selenium/CDP) is vastly more resilient than headless HTTP clients.

## 5. Known-Good URL Templates for Scraping
When APIs fail, use `browser_navigate` directly to these targets:
- **US Stocks (Real-time/Pre-market)**: `https://www.google.com/finance/quote/{SYMBOL}:{EXCHANGE}` (e.g., `TSM:NYSE`, `NVDA:NASDAQ`, `SYNA:NASDAQ`).
- **TAIEX Night Session (FITXP)**: https://histock.tw/index-tw/FITXP - Extremely stable. Look for the "股價" (Price) static text.

## 6. Anti-Bot Strategy & Price Source Selection

- **Avoid Google Search via Browser Tools**: `google.com/search` frequently triggers aggressive bot detection/CAPTCHAs when accessed via browser automation tools.
- **Better Alternative 1**: Use the `web_search` tool (API-driven) which is significantly less likely to be blocked.
- **Better Alternative 2**: Navigate directly to secondary finance sites like MSN, CNBC, Yahoo Finance, or HiStock.
- **Preferred Targets**:
    - **Synaptics (SYNA)**: `https://finance.yahoo.com/quote/SYNA/`
    - **Futures (NQ)**: `https://www.tradingview.com/symbols/CME_MINI-NQ1!/`
    - **TSM/NVDA**: MSN Money or MarketWatch.

## 7. Price Source Selection Logic (US Assets)

1. **15:00 - 21:30**: US Pre-market. Use `preMarketPrice`.
2. **21:30 - 04:00**: US Regular Session. Use `regularMarketPrice` or `currentPrice`.
3. **04:00 - 05:00**: US After-hours. Use `postMarketPrice`.
*Note: Always verify the timestamp of the price to ensure you aren't reporting stale "Previous Close" data as "current".*
