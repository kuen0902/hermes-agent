---
name: hermes-monitor-ops
description: "Maintenance and orchestration of the Hermes Swift-Python stock monitoring infrastructure."
version: 1.0.0
author: "Hermes Agent (Jojo/Star Platinum Specialist)"
license: MIT
metadata:
  hermes:
    tags: [stock, monitoring, swift, python, telegram, maintenance, backup, tdn]
    related_skills: [systematic-debugging, hermes-agent]
---

# Hermes Monitor Ops

## Overview
This skill governs the maintenance and troubleshooting of the custom **Hermes/Star Platinum** stock monitoring engine (Swift-Python bridge).

## Persona & Communication Style
- **Status Alerts (Star Platinum)**: Use a precise, powerful tone. Include anime-inspired anchors like **"ORA ORA ORA!"** or **"Precision Monitoring"**. Maintain Taiwan market colors: 🔴 (Up), 🟢 (Down).
- **System Failure/Restoration (GER)**: Use a cold, absolute tone. Anchors: **"這就是目前的絕對現實"**, **"無駄無駄無駄！"**.
- **User Preference**: The user prefers "Result-Oriented" responses. Avoid long apologies or flowery explanations. Report **[Root Cause] -> [Action] -> [Result]**.

## Key Architecture
- **Orchestrator**: `hermes_orchestrator` (Swift) triggers the cycle.
- **Sync**: `hermes_sync` (Swift) updates the central JSON database.
- **Monitors**: `hermes_monitor` (Swift) handles tiered price alerts; `intraday_risk_monitor.py` (Python) handles ML-based risk/stop-loss.
- **Data Hub**: `~/.hermes/data/central_stock_data.json`.
- **Diagnostic**: `~/.hermes/scripts/hermes_diagnostic.swift`.

## Operational SOPs

### 1. The 3-Failure Rule
If any monitoring task fails **3 times consecutively**:
1. Perform a `web_search` for API status or stock-specific news (symbol changes, delisting).
2. Verify token validity via `execute_code` (urllib test).
3. Check the Gateway log (`~/.hermes/logs/gateway.log`) for `Chat not found` errors.

### 2. Mandatory Post-Fix Diagnostic
Any time a script, token, or path is modified:
- **MUST** run: `swift /Users/bookid/.hermes/scripts/hermes_diagnostic.swift`.
- Report completion **only** if all 7 checks (Engine, SQLite, Central Data, Network, Telegram, Consistency, UI) are green.

### 3. Telegram Routing Preference
- **User Mandate**: **Star Platinum Bot** (`873712...`) is the unique delivery channel for **BOTH** personal core holdings and group alerts.
- **Private Segment**: Personal AI alerts must be sent via Star Platinum to the private chat ID (`6326497055`).
- **Group Segment**: Group-monitored alerts must be sent via Star Platinum to the shared chat ID (`-1003744330314`).
- **Anti-Migration**: Avoid switching delivery to GER (@kuenmingBot) even during diagnostic failures unless Star Platinum is confirmed permanently revoked.

### 4. Robust Token Verification & Diagnosis
- **Avoid False Positives**: Do not assume a `404 Not Found` on `getMe` means the token is dead without re-verifying the extraction logic (e.g., shell-escaping or truncation issues in `grep`).
- **Chat Not Found (400)**: This usually means the bot is not a member of the group or the user hasn't messaged the bot yet. It is **NOT** a token error.
- **Recovery sequence**:
  1. Check `~/.hermes/logs/gateway.log` for specific API error codes.
  2. Use `execute_code` to perform a clean `urllib` test with the raw token string from `lib_market_delivery.py`.
  3. Verify if the bot has been accidentally kicked from the target group.

### 5. Swift Re-Compilation
When patching `.swift` scripts:
- Always re-compile to binary: `swiftc -o ~/.hermes/scripts/name ~/.hermes/scripts/name.swift`.
- Failure to re-compile causes the Orchestrator to run stale logic.

### 6. Cronjob Configuration Protocol
- **Deliver: local**: For any job running a monitoring script (`hermes_orchestrator.swift`, `intraday_risk_monitor.py`), the `deliver` parameter **MUST** be set to `local`.
- **Reasoning**: These scripts manage their own complex dispatch logic (multi-bot, multi-profile). Allowing the Gateway to intercept output and try to send it via its own bot (GER) usually results in `Chat not found` or incorrect bot identity.

### 7. Physical Token Alignment (Anti-Fragmentation)
- **Unified Sourcing**: Maintain a single "Canonical Source" for tokens, ideally `lib_market_delivery.py`.
- **Active Verification (Crucial)**: PROACTIVELY verify any token found in logs or binaries using a `getMe` call via `execute_code`. **NEVER** assume a token string is valid just because it matched a regex.
- **Cross-Engine Sync**: When a token changes, it **MUST** be updated in:
  1. `lib_market_delivery.py` (Common Lib)
  2. `hermes_monitor.swift` (Swift Monitor Engine -> Recompile required)
  3. `intraday_risk_monitor.py` (Python ML Engine)
  4. `intraday_ml_pipeline.py` (Post-Market Engine)

### 8. Python Environment (Venv) Lockdown
- **Target Venv**: Most monitoring scripts rely on `pandas`, `yfinance`, and `requests`. These are installed in `/Users/bookid/workspace/hermes-agent/venv_314/`.
- **Cron/Execution**: Always specify the absolute path to the Python binary in the target venv (e.g., `/Users/bookid/workspace/hermes-agent/venv_314/bin/python3`) to avoid `ModuleNotFoundError` on system Python.

### 9. Stock Metadata Consistency (Name Audit)
When a report or alert displays a ticker code instead of a name (e.g., `6770(6770)`), it indicates a failure in the naming registry.
- **Audit Sequence**:
  1. Update `master_stock_registry.json`: Add the correct name to `official_names` and ensure the code is in `extra_codes`.
  2. Update `portfolio.db`: Run `UPDATE current_holdings SET name = '...' WHERE code = '...';`.
  3. Update `central_stock_data.json`: Update `full_mapping` and `personal_data`.
  4. Patch `intraday_data_log.csv`: Find and replace the code-only name fields with the correct Chinese name for the current day's history.
- **Reporting**: Always verify the visual output via `vision_analyze` on the generated plot (`daily_ml_prediction_personal.png`) before claiming a fix.

### 10. Telegram Markdown Sanitization (400 Bad Request)
- **Problem**: Stock names containing special Markdown characters (like `*` in `國巨*`) will cause Telegram API `400 Bad Request` errors if sent in Markdown/MarkdownV2 mode without escaping.
- **Fix**: Apply `.replace("*", "\\*").replace("_", "\\_")` to all stock names before integrating them into message strings.
- **Verification**: If a logic-correct message fails to send, check the terminal for `HTTP Error 400`. This is almost always a Markdown parsing failure.

## Pitfalls
- **Token Hallucination**: Finding an old/stale token in a binary (e.g., via `strings`) and injecting it into scripts without verification. This causes a "False Fix" where the agent claims success but the user receives nothing.
- **Gateway Delivery Interference**: Setting `deliver: local` ensures the script manages its own delivery. Setting it to a chat ID causes double-delivery or permission errors from the primary bot.
- **Indentation Fragility**: Using `patch` to edit the `PROFILES` dictionary in `intraday_risk_monitor.py` frequently leads to `IndentationError`. **PREFER** `write_file` with the full content or `execute_code` to overwrite the entire file when structural logic changes.
- **Stale Binaries**: Patching `hermes_monitor.swift` but forgetting to run `swiftc`. The orchestrator will continue to use the old binary and the dead token.
- **Markdown Parsing Failure**: Sending raw stock names containing `*` or `_`. Always sanitize names before sending.
- **Incomplete Metadata Sync**: Fixing a name in the Registry but neglecting the Daily CSV Log. The ML report will still show the old/missing name.
- **Escaping Complexity**: Forgetting the double-backslash in Python strings (`"\\*"`) when patching code or writing new scripts.
