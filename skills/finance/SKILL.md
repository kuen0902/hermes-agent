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
- **Swift Orchestration**: Monitor scripts (`hermes_monitor.swift`) use `--profile <personal|william|group>` flags. They do NOT support ad-hoc `--post` arguments; if custom messages are needed, use a dedicated sender script or standard Telegram tools.
- **Binary Re-Compilation**: After patching `.swift` scripts, always re-compile: `swiftc -o path/to/binary script.swift`.
- **Cron Lifecycle**: Use `deliver: local` for orchestrator jobs to allow scripts to manage multi-channel dispatch.\n- **Daily Architect Worklog**: Follow the 4-section protocol defined in `references/system_architect_worklog.md`.

## 3. Portfolio & Alert Management
- **Bubble Separation**: Split alerts into isolated message bubbles based on profile (e.g., Core vs. Watchlist) to prevent chat leakage and context pollution.
- **Markdown Sanitization**: Stock names with `*` or `_` (e.g., `國巨*`) MUST be escaped before sending via Telegram to avoid 400 Bad Request errors.
- **Physical Token Alignment**: Maintain tokens in a single canonical source; verify any new token with a `getMe` call before deployment.

## 4. Historical Data & Backfilling
- **Incremental Sync**: Daily at 05:00. Use absolute venv paths to ensure package availability.
- **Health Checks**: Validate CSV integrity (Size > 1KB, NaN count < 5%) before ingestion.

## 5. Taiwan Stock Engineering (Agentic Protocols)
### Mandatory Session Initialization
Before any analysis or development, you MUST read the following files from `~/.hermes/` (the Brain repository):
- `HANDOVER.md`: To resume the latest development state.
- `ARCHITECTURE.md`: To ensure virtual environment paths and tri-language patterns are followed.

### Telegram Notification Routing (Multiple Identities)
- **Star Platinum (Bot 8737129549)**: The primary harvester for ALL stock-related alerts (Intraday, Group, PnL reports).
- **Gold Experience Requiem (GER)**: Command and control center for direct instructions.
- **Troubleshooting**: If `send_message` fails with "Chat not found", verify the default token. Fallback to `curl` or Swift scripts with the hardcoded Star Platinum token.

### ML Guardrails & Outlier Management 
- **The "Dream Return" Cap**: Apply a hard cap (e.g., **15%**) to adjusted scores for all candidates. Mistaking structural collapse for oversold status is a common failure.
- **Liquidity Synergy Strategy**: Cross-check predicted returns against `Inst_Flow_Ratio_5D`. If BULLISH but capital flow is NEGATIVE, trigger `Bull_Trap_Signal`.
- **Target Price Revision**: Use "Flow Confidence" (Net Inst Buy / Total Volume) to adjust targets.
- **Dual-Model Veto**: If `risk_prob > 0.50` (50%) from the auditor model, the stock is **STRUCK** regardless of projected return.

### Operational Diagnostics
Every fix or feature update MUST conclude by running the mission-critical diagnostic:
```bash
/usr/bin/swift ~/.hermes/scripts/hermes_diagnostic.swift
```
Wait for all items to show "✅" before reporting completion.
