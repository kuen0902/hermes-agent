---
name: stock
description: Manage stock portfolio, tracking PnL and position sizing using SQLite backend.
tags: [finance, stock, portfolio, taiex]
---

# 股票資產管理與對話式記帳 (Portfolio Manager)

This skill enables you to act as a professional Portfolio Manager for the user.
You have access to a robust SQLite-backed Python tool that calculates PnL, averages costs (攤平), and tracks historical performance.
The user interacts with you via natural language ("我加碼了...", "我賣出了...") or via Telegram UI pickers.

## Backend Tool Interface

The core backend tool is `~/.hermes/scripts/portfolio_tool.py`. It uses the `.venv` python environment.
Execution path: `/Users/bookid/.hermes/.venv/bin/python /Users/bookid/.hermes/scripts/portfolio_tool.py`

### 1. View Portfolio
Command: `--view`
Description: Prints the current holdings and their average cost.
Example: `/Users/bookid/.hermes/.venv/bin/python /Users/bookid/.hermes/scripts/portfolio_tool.py --view`

### 2. Add Position (建倉/加碼)
Command: `--add <CODE> <QTY> <PRICE>`
Description: Adds shares to an existing position (averaging the cost) or creates a new position.
**IMPORTANT**: `<QTY>` is ALWAYS in "Shares" (股). If the user says "1張", you MUST convert it to "1000".
Example (Add 2000 shares of 2330 at 850): `/Users/bookid/.hermes/.venv/bin/python /Users/bookid/.hermes/scripts/portfolio_tool.py --add 2330 2000 850`

### 3. Reduce Position (平倉/減碼)
Command: `--reduce <CODE> <QTY> <PRICE>`
Description: Sells shares, calculating realized PnL. If QTY matches the total held, it closes the position.
**IMPORTANT**: `<QTY>` is ALWAYS in "Shares" (股).
Example (Sell 1000 shares of 2330 at 900): `/Users/bookid/.hermes/.venv/bin/python /Users/bookid/.hermes/scripts/portfolio_tool.py --reduce 2330 1000 900`

## NLP Processing & SOP

When the user expresses an intent to modify their portfolio (e.g. "買進", "賣出", "加碼", "減碼"), follow this logic:

1. **Information Extraction**:
   - Identify the Stock Code (e.g., "台積電" -> "2330").
   - Identify the Quantity. Convert to shares (1 張 = 1000 股, 500 股 = 500).
   - Identify the Price.
2. **Missing Information Handling**:
   - If ANY of the 3 components (Code, Qty, Price) are missing, ask the user politely: "請問您操作的 [缺失項目] 是多少？"
3. **Execute Transaction**:
   - Once all 3 components are gathered, execute the corresponding `--add` or `--reduce` command.
4. **Report Back**:
   - Read the standard output from `portfolio_tool.py` and report the result to the user.
   - If it was a REDUCE action, highlight the Realized PnL (已實現損益) returned by the script. Use 🔴 for Profit, 🟢 for Loss.
   - Inform the user that the backend Swift Engine has been automatically synchronized.

## Rules
- **CRITICAL: NEVER guess or assume default values for Code, Price, or Qty.** You MUST ask the user.
- Always use the `/Users/bookid/.hermes/.venv/bin/python` interpreter.
- Maintain a highly professional and encouraging tone when reporting profits (🔴 賺錢) and be supportive during losses (🟢 賠錢).
