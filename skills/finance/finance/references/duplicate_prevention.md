# Telegram Notification Redirection & Duplicate Prevention

## Problem
In Hermes Agent, when a `cronjob` runs a script that has internal notification logic (e.g., calling the Telegram Bot API directly), the user often receives the message twice:
1. One from the script's native API call.
2. One from Hermes delivering the script's `stdout` as the cron result.

## Scenario: The "Golden Experience" vs. "Star Platinum" Model
The user wants to keep the main interaction channel ("Golden Experience") clean while receiving high-frequency updates in a specialized bot ("Star Platinum").

## Implementation Pattern

### 1. The Script (Python)
Ensure the script is silent unless explicitly asked for verbosity.
```python
import sys
# ... internal message logic ...

def main():
    # 1. Fetch data
    # 2. Logic to build message
    # 3. Send to external Bot API
    send_to_telegram(full_message)
    
    # 4. Silence stdout for main chat
    if "--verbose" in sys.argv:
        print(full_message)
    # else: print nothing!
```

### 2. The Cronjob Setup
When creation the cronjob, set `deliver` to `local`.
```bash
# Example hermes command
hermes cron create "stock-monitor" --schedule "*/10 9-13 * * 1-5" --deliver local --prompt "Run the script..."
```
This forces the agent to save the output to `~/.hermes/cron/output/` without posting it back to the Telegram chat.

## Verification
- Check `~/.hermes/cron/output/<job_id>/` for logs.
- Monitor the bot to confirm single-delivery.
