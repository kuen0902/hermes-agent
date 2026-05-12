# Multi-Bot Telegram Routing Map

As of 2026-05-12, the system uses a multi-bot architecture to separate architectural commands from high-frequency monitoring.

## 1. Bots & Personas

### 「黃金體驗-鎮魂曲」 (Gold Experience Requiem)
- **Primary Body**: `@kuenmingBot` (8513436203)
- **Role**: Command center, core dialogue, architecture commands, and Manual Deep Analysis reports.
- **Tone**: "無駄無駄無駄！", Result-oriented, cold.
- **Target Chat**: `6326497055` (Jojo Private).

### 「白金之星」 (Star Platinum)
- **Monitor Body**: `@taiwangupiaoBot` (8737129549)
- **Token**: `8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU`
- **Logic**: Handles **BOTH** Private and Group Monitoring for all day-market intraday alerts.
- **Home Channels**:
    - `6326497055` (Jojo Private): Receives personal holdings alerts (`stock_monitor.py`).
    - `-1003744330314` (高潮不斷 Group): Receives group watchlist alerts (`group_stock_monitor.py`).

### 「小智」 (William's Dedication)
- **Monitor Body**: `@williamHermes7788_bot` (8678817340)
- **Display Name**: 來自真新鎮的小智
- **Token**: `8678817340:AAHLV9zC67yis62W2126vNf9r7O_WEGQ` (✅ Verified May 12)
- **Role**: Private stock monitor for William.
- **Target Chat**: `8695583357` (William Private).

## 2. Routing Logic

- **Direct Send Preference**: Automated monitors (`stock_monitor.py`, etc.) should use native Python `urllib` or `requests` to send directly to the Telegram API. This bypasses Gateway "Silent Mode" (where the SP profile might be stopped) and avoids Shell expansion errors with currency symbols ($).
- **Format Constraint**: Use "精密波動警戒" format. Always hide `(較前次：+0.00%)` if the price hasn't changed since the last 20-minute check to minimize noise.
- **Deduplication**: Use `/Users/bookid/.hermes/data/*.lock` files to prevent the same price update from being sent to multiple channels simultaneously unless intended.

## 3. Contact IDs & Troubleshooting
- **Jojo (User)**: `6326497055`
- **William**: `8695583357`
- **Group (高潮不斷)**: `-1003744330314`

### Delivery Status (2026-05-12)
- **Personal/Group**: ✅ Healthy (via `@taiwangupiaoBot`).
- **William**: ✅ Healthy (via `@williamHermes7788_bot`).
- **Gateway Health**: If bots stop responding despite valid tokens, follow the **Gateway Recovery Protocol**. Check `~/.hermes/logs/agent.log` for 401 errors.
