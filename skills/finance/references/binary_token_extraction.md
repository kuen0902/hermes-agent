# SOP: Binary Token Extraction & Verification

When source code is missing or credentials in `.py`/`.swift` files seem invalid (401 Unauthorized), the compiled binary is the "Absolute Reality" of what is currently running in production.

## 1. Extraction from Binaries
Use the `strings` command combined with a Regex for Telegram Bot Tokens:

```bash
# Pattern: [BotID]:[TokenHash]
strings /Users/bookid/.hermes/scripts/hermes_monitor | grep -E "[0-9]{9,10}:[a-zA-Z0-9_-]{35}"
```

## 2. Verification Protocol
**NEVER** inject an extracted token directly into a script without testing. Use the following `urllib` snippet in `execute_code`:

```python
import urllib.request, json, ssl
ctx = ssl._create_unverified_context()

def verify(token):
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        resp = urllib.request.urlopen(url, context=ctx, timeout=5)
        data = json.loads(resp.read().decode())
        return data.get("ok"), data.get("result", {}).get("username")
    except Exception as e:
        return False, str(e)

# Replace with extracted token
ok, result = verify("8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU")
print(f"Status: {ok}, Bot: {result}")
```

## 3. Propagation
Once verified, the token must be updated across all 4 core files:
1. `lib_market_delivery.py`
2. `hermes_monitor.swift` (Requires `swiftc` recompilation)
3. `intraday_risk_monitor.py`
4. `intraday_ml_pipeline.py`
