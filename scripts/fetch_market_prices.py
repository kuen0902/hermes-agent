#!/usr/bin/env python3
import yfinance as yf
import json
from datetime import datetime
import pytz

taipei_tz = pytz.timezone('Asia/Taipei')
timestamp = datetime.now(taipei_tz).isoformat()

prices = {}

# Fetch NQ Futures (Nasdaq 100 Futures)
try:
    nq = yf.Ticker("NQ=F")
    hist = nq.history(period="1d")
    if not hist.empty:
        prices["NQ"] = float(hist['Close'].iloc[-1])
        print(f"NQ: {prices['NQ']}")
except Exception as e:
    print(f"NQ error: {e}")

# Fetch TSM
try:
    tsm = yf.Ticker("TSM")
    hist = tsm.history(period="1d")
    if not hist.empty:
        prices["TSM"] = float(hist['Close'].iloc[-1])
        print(f"TSM: {prices['TSM']}")
except Exception as e:
    print(f"TSM error: {e}")

# Fetch NVDA
try:
    nvda = yf.Ticker("NVDA")
    hist = nvda.history(period="1d")
    if not hist.empty:
        prices["NVDA"] = float(hist['Close'].iloc[-1])
        print(f"NVDA: {prices['NVDA']}")
except Exception as e:
    print(f"NVDA error: {e}")

# Fetch SYNA
try:
    syna = yf.Ticker("SYNA")
    hist = syna.history(period="1d")
    if not hist.empty:
        prices["SYNA"] = float(hist['Close'].iloc[-1])
        print(f"SYNA: {prices['SYNA']}")
except Exception as e:
    print(f"SYNA error: {e}")

# Fetch FITXP (Taiwan Index Futures Night Session)
# Try TXF1=TW first
if "FITXP" not in prices:
    try:
        fitxp = yf.Ticker("TXF1=TW")
        hist = fitxp.history(period="1d")
        if not hist.empty:
            prices["FITXP"] = float(hist['Close'].iloc[-1])
            print(f"FITXP (TXF1=TW): {prices['FITXP']}")
    except Exception as e:
        print(f"FITXP (TXF1=TW) error: {e}")

# If that didn't work, try M2F1=TW
if "FITXP" not in prices:
    try:
        fitxp = yf.Ticker("M2F1=TW")
        hist = fitxp.history(period="1d")
        if not hist.empty:
            prices["FITXP"] = float(hist['Close'].iloc[-1])
            print(f"FITXP (M2F1=TW): {prices['FITXP']}")
    except Exception as e2:
        print(f"FITXP (M2F1=TW) error: {e2}")

# If still no FITXP, try Taiwan Weighted Index as proxy
if "FITXP" not in prices:
    try:
        tw_index = yf.Ticker("^TWII")
        hist = tw_index.history(period="1d")
        if not hist.empty:
            prices["FITXP"] = float(hist['Close'].iloc[-1])
            print(f"FITXP (^TWII proxy): {prices['FITXP']}")
    except Exception as e3:
        print(f"FITXP (^TWII) error: {e3}")

# Add timestamp
prices["timestamp"] = timestamp

# Write to bridge file
bridge_path = "/Users/bookid/.hermes/data/market_prices_bridge.json"
with open(bridge_path, 'w') as f:
    json.dump(prices, f, indent=2)

print(f"\nBridge file written to {bridge_path}")
print(f"Current prices: {json.dumps(prices, indent=2)}")
