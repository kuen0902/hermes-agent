# Telegram Error: 403 Forbidden (Bot Can't Initiate Conversation)

## Root Cause
This error occurs when the bot attempts to send a message to a user or chat where it does not have the "right of first message." In Telegram, a bot generally cannot DM a user unless the user has first sent a `/start` message to the bot.

## Typical Scenarios in Hermes
1. **New Monitoring Channel**: The "William" bot or a similar auxiliary bot was added to a group, but the user setup hasn't completed the 1:1 handshake.
2. **Revoked Access**: The user blocked the bot or the bot was kicked from the target group ID.
3. **Ghost Notification**: An orchestrator is trying to poke a bot that has stale session data.

## Diagnostic Steps (The "GER Triage")
1. **Ping Test**: Execute `execute_code` with `requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe")`.
2. **Membership Check**: If the target is a group (negative Chat ID), verify the bot is still an admin or member.
3. **Handshake Verification**: Ask the user: "Have you messaged the specific bot (@BotUsername) first?"
4. **ID Conflict**: Check `~/.hermes/.env` to ensure the Telegram Token for the "William" profile matches the bot the user is actually talking to.

## Mitigation
- **Graceful Failure**: Catch the `403` exception in Python/Swift and log it to `errors.log`. Do NOT let it crash the `hermes_orchestrator` cycle.
- **User Instruction**: If the error persists, report to the user: "⚠️ Star Platinum/William Bot blocked. Please send a message to the bot first to re-establish the bridge."
