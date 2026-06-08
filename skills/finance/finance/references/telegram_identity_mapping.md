# Telegram Identity Mapping & Credentials

## Active Persona: 黃金體驗-鎮魂曲 (Gold Experience - Requiem)
*   **Username**: `@kuenmingBot`
*   **Token**: `8513436203:AAFgyNQja4cXVsyhFurVlKMOaKugyOJG1uM`
*   **Role**: Master Dialogue Channel / Core Logic Interface.
*   **Key ID**: Channel B.

## Subsidiary Persona: 白金之星 (Star Platinum)
*   **Username**: `@taiwangupiaoBot`
*   **Token**: `8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU`
*   **Role**: Portfolio Monitor / Data Distribution / Stock Alerts.
*   **Key ID**: Channel A.

## Master Target ID (Jojo)
*   **Chat ID**: `6326497055`
*   **Group ID (高潮不斷)**: `-1003744330314`

## Maintenance
When switching the system's primary bot (the one controlled by the gateway):
1. Update `TELEGRAM_BOT_TOKEN` in `~/.hermes/.env`.
2. Execute `hermes gateway restart`.
3. Verify status with `hermes gateway status`.
