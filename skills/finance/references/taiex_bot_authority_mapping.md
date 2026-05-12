# TAIEX Bot Authority & Routing Mapping (v1.0)

This document defines the authoritative routing for all TAIEX-related automation as of May 12, 2026.

## 1. Bot Roles & Tokens
| Bot Persona | Token Source | Primary Responsibility |
| :--- | :--- | :--- |
| **黃金體驗-鎮魂曲 (GER)** | `GER_TOKEN` / `@kuenmingBot` | 1-on-1 Dialogue, Architecture control, and High-Fidelity Manual Reports. |
| **白金之星 (Star Platinum)** | `STAR_PLATINUM_TOKEN` / `@taiwangupiaoBot` | **Automated High-Frequency Monitoring.** Handles both group (`-1003744330314`) and private (`6326497055`) alerts. |

## 2. Channel Targets
- **Private Alerts**: Target `6326497055`. Must use **Star Platinum** for intraday status updates.
- **Group Alerts**: Target `-1003744330314`. Use **Star Platinum**.
- **System Commands**: Interaction occurs via **GER**.

## 3. Critical Failure Modes (Session Learning)
- **Token Redaction**: Automated patches or manual code reviews often replace active tokens with `...REDACTED`. If a script (e.g., `stock_monitor.py`) reports "Unauthorized 401", the token inside the script is likely the issue.
- **Numbers Lockout**: If `pgrep Numbers` is false, `personal_data` will be empty. The sync gatherer MUST ensure Numbers is open with the specific `StockTracking_Daily.numbers` file.
- **Identity Drift**: Do not assume the "Architect" bot (GER) sends all private messages. The user specifically wants **Star Platinum** to provide the status updates for holdings to keep the "Architect" channel clean for specialized commands.

## 4. Recovery Routine
1. Run `hermes gateway list` to check which bots are active.
2. Check `~/.hermes/scripts/lib_market_delivery.py` for the current valid tokens.
3. Verify Numbers is running: `open ~/Documents/StockTracking_Daily.numbers`.
4. Trigger Orchestrator: `python3 ~/.hermes/scripts/taiex_orchestrator.py`.
