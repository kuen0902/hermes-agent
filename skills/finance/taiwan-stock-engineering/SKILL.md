---
name: taiwan-stock-engineering
description: Advanced engineering protocols for Taiwan stock monitoring and Hermes system synchronization.
category: finance
---

# Taiwan Stock Monitoring & System Operations

This skill governs the operational lifecycle of the Taiwan stock monitoring system, ensuring architectural alignment and reliable notification routing.

## 1. Mandatory Session Initialization
Before any analysis or development, you MUST read the following files from `~/.hermes/` (the Brain repository):
- `HANDOVER.md`: To resume the latest development state.
- `ARCHITECTURE.md`: To ensure virtual environment paths and tri-language patterns are followed.

## 2. Dual-Repo Strategy
- **Engine**: `~/workspace/hermes-agent` (Stay clean, track upstream).
- **Brain/Instance**: `~/.hermes` (Context, memory, custom scripts, and SQLite databases).
- **Rule**: All stateful updates (Sync files, logs, DBs) must happen in `~/.hermes`.

## 3. Telegram Notification Routing
- **Star Platinum (Bot 8737129549)**: The primary harvester for ALL stock-related alerts (Intraday, Group, PnL reports).
- **Gold Experience Requiem (GER)**: Command and control center for direct instructions.
- **Troubleshooting**: If `send_message` fails with "Chat not found", verify the default token in the configuration. If the environment token is misconfigured, fallback to using `curl` or Swift scripts with the hardcoded Star Platinum token.

## 4. Mandatory Post-Task Diagnostic
Every fix or feature update MUST conclude by running:
```bash
/usr/bin/swift /Users/bookid/.hermes/scripts/hermes_diagnostic.swift
```
Wait for all items to show "✅" before reporting completion to the user.

## 5. Stock Monitoring Pitfalls
- **Token Pollution**: Conflicting token entries in configuration files can break the `send_message` tool.
- **Path Isolation**: Never use relative paths in cron jobs; always use absolute paths starting from `/Users/bookid/.hermes`.
- **Naming Conventions**: Use TAIEX colors (🔴漲, 🟢跌).
