# Multi-Bot Telegram Routing Map

As of 2026-05-11, the system uses a multi-bot architecture to separate architectural commands from high-frequency monitoring.

## 1. Bots & Personas

### 「黃金體驗-鎮魂曲」 (Gold Experience Requiem)
- **Primary Body**: `@kuenmingBot` (8513436203)
- **Role**: Command center, deep financial analysis (Obsidian reports), and complex troubleshooting.
- **Tone**: "無駄無駄無駄！", Result-oriented, cold.

### 「白金之星」 (Star Platinum)
- **Monitor Body**: `@taiwangupiaoBot` (8737129549)
- **Token**: `8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU`
- **Role**: Dedicated stock monitoring for High-Frequency alerts and PDF reports.
- **Home Channels**: `6326497055` (Jojo Private) | `-1003744330314` (高潮不斷 Group).

### 「威廉專屬」 (William's Dedication)
- **Monitor Body**: `@WilliamClaw55667788_bot` (8563522559)
- **Token**: `8563522559:AAGhXvdteYk2qN8pm-hgQbCHSiLYBFNHbe8` (⚠️ Status: **EXPIRED/401** as of 2026-05-11)
- **Role**: Private stock monitor for William.
- **Target Chat**: `8695583357` (William Private).

## 2. Routing Logic

- **Default Home**: Automated reports from cron/orchestrator should target `6326497055`.
- **Manual Redirection**: If a message fails via the system's `send_message` tool, use the `taiwangupiaoBot` token with direct `requests.post` to ensure delivery to the secondary channel.
- **Deduplication**: Use `/Users/bookid/.hermes/data/*.lock` files to prevent the same price update from being sent to multiple channels simultaneously unless intended.

## 3. Contact IDs & Troubleshooting
- **Jojo (User)**: `6326497055`
- **William**: `8695583357` (Status: Needs new Token + /start)
- **Group (高潮不斷)**: `-1003744330314`

### Delivery Status (2026-05-11)
- **Personal/Group**: Healthy (via `@taiwangupiaoBot`).
- **William**: 🔴 Broken. Token `8563522559` is 401 Unauthorized. Script `william_stock_monitor.py` requires update.
- **Gateway Health**: If bots stop responding despite valid tokens, follow the **Gateway Recovery Protocol** in the `hermes-agent` skill (see `references/gateway_recovery_protocol.md` inside `hermes-agent`).
