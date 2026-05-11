# Headless Automation Pitfalls: Numbers.app & Cron

## Session Context (2026-05-05)
The agent was tasked to run a stock monitor script (`group_stock_monitor.py`) as a cron job. The script reads from `StockTracking_Daily.numbers` via `osascript`.

## Key Failures & Solutions

### 1. Terminal Timeouts
- **Problem**: Running the script via `terminal` tool timed out after 60s.
- **Root Cause**: `osascript` was waiting for Numbers.app to open/load the document.
- **Solution**: For background execution, either increase the tool timeout or prioritize non-GUI data access.

### 2. Lock File Stalling
- **Problem**: The script used a `.lock` file to prevent spamming Telegram. Because of the previous timeout, the lock file existed but the script never finished, preventing subsequent runs from sending messages.
- **Debug Technique**: 
    - Check for existing lock files in `~/.hermes/data/`.
    - Temporarily patch the `check_lock()` function to `return True` to force execution.
    - Path used: `/Users/bookid/.hermes/data/group_stock_sent.lock`

### 3. Missing Terminal Output
- **Problem**: The script sent results to Telegram but didn't `print()` them, leaving the agent blind to the actual result in the terminal log.
- **Solution**: Patch the script to `print(final_msg)` so the execution result is captured in the Hermes tool output.

### 4. AppleScript Reliability
- **Problem**: Fetching data from a specific sheet/table can be slow or fail if the document structure changed slightly.
- **Fallback Pattern**:
  ```python
  STOCK_MAPPING = get_holdings_from_numbers("Group")
  if not STOCK_MAPPING:
      # Hard-coded fallback for critical services
      STOCK_MAPPING = {"2330": "台積電", ...}
  ```
