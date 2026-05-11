# TAIEX/TPEx Automation Cheatsheet

Knowledge gathered from managing Taiwan Stock Exchange (TAIEX) and Taipei Exchange (TPEx) automation workflows on macOS.

## 1. Ticker Suffix Mapping
Yahoo Finance (`yfinance`) requires distinct suffixes for Taiwan markets:
- **Listed (TSE/TWSE)**: `.TW` (e.g., `2330.TW`)
- **OTC (TPEx)**: `.TWO` (e.g., `8027.TWO`)

**Strategy**: If fetching `.TW` returns a 404/Empty result, immediately retry with `.TWO`.

## 2. SSL Certificate Fix (macOS)
Scripts running via cron or terminal on macOS often encounter:
`[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate in certificate chain`

**Fix for urllib**:
```python
import ssl
import urllib.request

# Create unverified context
ctx = ssl._create_unverified_context()

# Use in urlopen
with urllib.request.urlopen(url, context=ctx) as response:
    data = response.read()
```

## 3. Telegram Bot Health Check
Use this snippet to diagnose 401 Unauthorized errors:
```python
import urllib.request, json, ssl
ctx = ssl._create_unverified_context()
token = "YOUR_BOT_TOKEN"
url = f"https://api.telegram.org/bot{token}/getMe"

try:
    with urllib.request.urlopen(url, context=ctx) as r:
        print(json.loads(r.read().decode())["ok"])
except Exception as e:
    print(f"Failed: {e}") # 401 means invalid token
```

## 4. Numbers Data Extraction
Refer to `apple-numbers` core skill for the "Tab-Separated Pattern" to read portfolio data from `StockTracking_Daily.numbers`. Ensure the document is open in Numbers.app before running the script.
