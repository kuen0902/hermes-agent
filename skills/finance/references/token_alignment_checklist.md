# Telegram Token Alignment Detection

Use this script pattern to verify which tokens are live and which identities they correspond to across the codebase.

```python
import os
import re
import urllib.request
import json
import ssl

ctx = ssl._create_unverified_context()
token_pattern = re.compile(r'[0-9]{9,10}:[a-zA-Z0-9_-]{35}')

def test_token(tk):
    url = f"https://api.telegram.org/bot{tk}/getMe"
    try:
        resp = urllib.request.urlopen(url, context=ctx, timeout=3)
        data = json.loads(resp.read().decode())
        if data.get("ok"):
            return data["result"]["username"]
    except:
        pass
    return None

def scan_and_verify():
    all_tokens = set()
    search_dirs = [
        os.path.expanduser("~/.hermes/scripts/"),
        os.getcwd()
    ]

    for d in search_dirs:
        if not os.path.exists(d): continue
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith(('.py', '.swift', '.sh', '.json', '.yaml', '.txt', '.log')):
                    path = os.path.join(root, f)
                    try:
                        with open(path, 'r', errors='ignore') as file:
                            content = file.read()
                            matches = token_pattern.findall(content)
                            for m in matches:
                                all_tokens.add(m)
                    except: pass

    print(f"Total unique tokens found: {len(all_tokens)}")
    for tk in all_tokens:
        user = test_token(tk)
        if user:
            print(f"✅ Bot Found: @{user} | Token: {tk[:10]}...{tk[-4:]}")
        else:
            print(f"❌ Dead Token: {tk[:10]}...{tk[-4:]}")

if __name__ == "__main__":
    scan_and_verify()
```

## Key Rules
1. **Never Assume**: If the user says "it stopped working," the first step is running this verification.
2. **Physical Injection**: Once the live token for the target bot (e.g., Star Platinum) is found, it must be updated in all python/swift source files and the swift binary recompiled.
3. **Log Check**: If tokens are live and updating but messages aren't appearing, check `gateway.log` for `Chat not found`.
