# Telegram Bot Error Code Triage & Connectivity

## Error Codes
- **401 Unauthorized**: Token is invalid, revoked, or expired. Requires a new Token from BotFather. **Crucial**: 401 errors are often caused by scripts carrying stale/redacted tokens (e.g., `...REDACTED`). Always verify the token via `getMe` before assuming a network failure. Authoritative Source: Extract the live token from `lib_market_delivery.py` or `.env`.
- **403 Forbidden**: Bot cannot initiate conversation (BotFather policy). User MUST send `/start` to the bot first. Common after user clears chat history OR if the bot tries to DM a user who hasn't messaged it in the current session.
- **400 Bad Request: chat not found**: The Chat ID was valid once but is now unrecognized (User blocked bot or revoked access).

## Sync Triage & Connectivity (The Architect's Path)
When the user says "still no message" or "the bot is not responding":

1. **Direct Connectivity Verification**: 
   Instead of `curl` (which hates special chars in tokens), use `execute_code` to test the bot directly:
   ```python
   import urllib.request, ssl, urllib.parse
   ctx = ssl._create_unverified_context()
   url = f"https://api.telegram.org/bot{token}/sendMessage"
   data = urllib.parse.urlencode({"chat_id": cid, "text": "Test"}).encode()
   print(urllib.request.urlopen(urllib.request.Request(url, data=data), context=ctx).read())
   ```

2. **Identity Check**: 
   Audit `~/.hermes/.env`. Verify `TELEGRAM_BOT_TOKEN` matches the desired persona from `references/multi_bot_routing_map.md`. A common failure mode is the Gateway launching with a sub-bot token instead of the primary.

3. **Webhook Audit**: 
   Use `requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")`. If `pending_update_count > 0` but logs are silent, the local listener is stalled. Restart with `hermes gateway run --replace`.

## Formatting Optimization (The Zero Noise Principle)
- **Shell Expansion Pitfall**: NEVER send messages containing $, +, or - via terminal curl strings. The shell will misinterpret $401.55 as a variable and truncate it. Use execute_code with Python requests.
- **Threshold Display**: When a ticker triggers an "Absolute Value" report, only show the "較前次" (compared to last) delta if the price has actually changed.
  `change_str = f" (較前次：{pct:+.2f}%)" if current_price != last_price else ""`
