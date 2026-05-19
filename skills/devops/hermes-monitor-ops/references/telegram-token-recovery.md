# Telegram Token Recovery Pattern

When bot tokens are suspected of being invalid (404/401) and `terminal` calls with `curl` are failing due to quoting issues:

## 1. Test via execute_code
Use this Python snippet to verify the token without shell interference:

```python
import urllib.request
import json
import ssl

def check_token(token):
    ctx = ssl._create_unverified_context()
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        with urllib.request.urlopen(url, context=ctx, timeout=5) as resp:
            return json.load(resp)
    except Exception as e:
        return {"error": str(e)}

# Read from .env if needed
# token = "..."
print(check_token(token))
```

## 2. Multi-Script Patching
If the token is dead, use a regex-based replacement across the script directory:

```python
import os
import re

# Use a validated token (e.g. from the Gateway .env)
# valid_token = "..."

def resync_tokens(directory, old_prefix, new_token):
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(('.py', '.swift')):
                path = os.path.join(root, f)
                with open(path, 'r') as f_obj:
                    content = f_obj.read()
                # Target common token formats
                new_content = re.sub(old_prefix + r':[^",\s\']+', new_token, content)
                if content != new_content:
                    with open(path, 'w') as f_obj:
                        f_obj.write(new_content)
                    print(f"Patched: {path}")

# Example: directory="~/.hermes/scripts/", old_prefix="8737129549"
```
