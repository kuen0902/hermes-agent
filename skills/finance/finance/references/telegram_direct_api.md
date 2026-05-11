# Direct Telegram API Delivery via Python

When the agent's high-level `send_message` tool fails with `Chat not found` (common for specific group IDs or bot permissions in groups), use this direct delivery pattern in your Python scripts.

## Core Implementation (Python)

```python
import urllib.request
import urllib.parse
import ssl

def send_telegram(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    
    # CRITICAL: Bypass macOS SSL certificate verification failures
    ctx = ssl._create_unverified_context()
    
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            return response.getcode() == 200
    except Exception as e:
        print(f"Telegram Delivery Error: {e}")
        return False
```

## CLI Management (curl Patterns)

For quick maintenance and verification, use `curl` directly via terminal.

### 0. Bot Registry
- **GER Core**: `8513436203:AAHcvVxNgLEqQ_U_JH55mZaENCWfl4VTFJ4` (@kuenmingBot) - **Main communication channel.**
- **Monitor**: `8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU` (@taiwangupiaoBot) - **Stock/Group distribution.**

### 1. Send Message
```bash
curl -s -X POST "https://api.telegram.org/bot<token>/sendMessage" \
     -d chat_id="<id>" \
     -d text="<message>"
```

### 2. Update Bot Name (Identity Management)
```bash
curl -s -X POST "https://api.telegram.org/bot<token>/setMyName" \
     -d name="黃金體驗-鎮魂曲"
```

### 3. Check Recent Messages (Get Updates)
### 3. Check Recent Messages (Get Updates)
```bash
curl -s "https://api.telegram.org/bot<token>/getUpdates?offset=-1"
```

## Maintenance Workflow: Token Swap
1. Edit `~/.hermes/.env`.
2. Run `hermes gateway restart`.
3. Check `tail -f ~/.hermes/logs/gateway.log` to confirm "Connected to Telegram (polling mode)".

## Common Pitfalls & Debugging
- **SSL Certificate Verification Failures**: Native Python on macOS often fails to verify SSL certificates for `api.telegram.org`. Always use `ssl._create_unverified_context()` as shown in the implementation above.

     -d chat_id="<id>" \
     -d reply_to_message_id="<msg_id>" \
     -d text="<message>"
```

### 5. Send Typing Indicator (Interaction Feedback)
```bash
curl -s -X POST "https://api.telegram.org/bot<token>/sendChatAction" \
     -d chat_id="<id>" \
     -d action="typing"
```

## Common Pitfalls & Debugging

### 1. HTTP Error 401: Unauthorized
**Root Cause**: The Bot Token provided is invalid or has been revoked in BotFather.
**Diagnostic**: `urllib.request.urlopen(".../getMe")` returns `401 Unauthorized`.
**Fix**: Generate a new token and update the `BOT_TOKEN` variable in the script.

### 2. HTTP Error 403: Forbidden
**Root Cause**: Bot cannot initiate a conversation with a user who hasn't messaged it first.
**Diagnostic**: `sendMessage` returns `403 Forbidden: bot can't initiate conversation`.
**Fix**: Ask the user to search for the bot's username and click **"Start"** or send any text message.

### 3. HTTP Error 400: Bad Request: chat not found
**Root Cause**: The Chat ID was previously valid but the session is lost (e.g. user blocked the bot or chat history was cleared).
**Fix**: Similar to 403, have the user re-engage with the bot.

### 4. Markdown Parsing Error
**Root Cause**: Characters like `_`, `*`, `[` in the message break Telegram's parser.
**Fix**: Wrap tickers in backticks (`` `2330.TW` ``) and bold names (`**TSMC**`). Alternately, send without `parse_mode`.
