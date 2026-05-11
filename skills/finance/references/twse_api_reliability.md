# TWSE API Reliability Note (2026-05-11)

## Context
Yahoo Finance (`yfinance`) consistently throws `429 Too Many Requests` when syncing >20 TAIEX tickers every 10-20 minutes, even with session headers and chunking. 

## Solution: Direct TWSE/OTC API
The `taiex_central_data_sync.py` gatherer has been migrated to the official MIS API.

- **Primary URL**: `https://mis.twse.com.tw/stock/api/getStockInfo.jsp`
- **Params**: `ex_ch`, `json=1`, `delay=0`
- **Key Fields**:
    - `z`: Latest Trade Price (if '-' or 'null', check `pz`, `o`, or `y`)
    - `y`: Yesterday's Close
    - `v`: Current Volume
    - `c`: Stock Code
    - `ex`: Exchange (`tse`, `otc`, or `eb`)

## Handling SSL Verification Errors
The `mis.twse.com.tw` server often lacks a valid "Subject Key Identifier". 
- **Python Fix**:
```python
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
response = requests.get(url, verify=False, timeout=15)
```

## Symbology Mapping
- `tse_2330.tw` -> 2330 (TSMC) Listed
- `otc_5347.tw` -> 5347 (Vanguard) OTC
- `eb_7815.tw` -> 7815 (Carota) Emerging

## Orchestration Pitfall
If using `terminal` to run the orchestrator, ensure the `timeout` is sufficient (at least 300s) as Numbers AppleScript and API polling can take time.
