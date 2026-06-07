---
name: finance
description: Financial data automation — market queries, portfolio monitoring, earnings analysis, and TAIEX-specific workflows.
version: 1.0.0
author: "Hermes Agent (Curator)"
license: MIT
metadata:
  hermes:
    tags: [finance, stocks, taiex, investigation, earnings, portfolio, telegram]
    related_skills: [hermes-agent, data-ops]
---

# Finance & Investment Automation

This umbrella skill governs automated financial tracking, market data retrieval, and corporate reporting analysis. It consolidates the high-level logic for stock monitoring engines and portfolio management.

## 1. Market Data Retrieval (TAIEX & Global)
- **The Market Open Gatekeeper**: Mandatory for cron jobs. Verify market status via `2330.TW` or market state flags before reporting.
- **The Hybrid Fallback Pattern**: Use primary local APIs (FB/TWSE) with `yfinance` as a fallback.
- **Resilient Bridge**: Cache market prices locally to prevent API rate-limiting.

## 2. Infrastructure Operations (Hermes Monitor Engine)
- **Swift-Python Bridge**: Use strict JSON data transfer via `stdout`. See `references/swift_python_bridge.md` for architecture rules.
- **Binary Re-Compilation**: After patching `.swift` scripts, always re-compile: `swiftc -o path/to/binary script.swift`.
- **Cron Lifecycle**: Use `deliver: local` for orchestrator jobs to allow scripts to manage multi-channel dispatch.

## 3. Portfolio & Alert Management
- **Bubble Separation**: Split alerts into isolated message bubbles based on profile (e.g., Core vs. Watchlist) to prevent chat leakage and context pollution.
- **Markdown Sanitization**: Stock names with `*` or `_` (e.g., `國巨*`) MUST be escaped before sending via Telegram to avoid 400 Bad Request errors.
- **Physical Token Alignment**: Maintain tokens in a single canonical source; verify any new token with a `getMe` call before deployment.

## 4. Historical Data & Backfilling
- **Incremental Sync**: Daily at 05:00. Use absolute venv paths to ensure package availability.
- **Health Checks**: Validate CSV integrity (Size > 1KB, NaN count < 5%) before ingestion.
