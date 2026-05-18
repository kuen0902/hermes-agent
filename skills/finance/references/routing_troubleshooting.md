# Telegram Routing & Delivery Troubleshooting

## 1. Symptom: Messages Sent to Wrong Chat
When a bot sends messages to a private chat instead of a group (or vice versa) even though the `cron` job or `send_message` tool is targetting the correct ID.

### Root Cause: Hardcoded Overrides
In high-performance Swift-based monitors (like `hermes_monitor.swift`), the chat destination is often hardcoded in a `ProfileConfig` or similar struct within the script itself. This internal logic overrides any external `deliver` parameters or environment variables.

### Diagnostic Steps
1. **Search for IDs**: Use `grep` to search for the "wrong" Chat ID in the `~/.hermes/scripts/` directory.
   ```bash
   grep -r "WRONG_CHAT_ID" ~/.hermes/scripts/
   ```
2. **Review Profile Configs**: In Swift scripts, look for a `PROFILES` dictionary or similar structure.
3. **Verify Cron Delivery**: Check the raw `jobs.json` or use `hermes cron edit` to ensure the `deliver` field matches the intended destination.

### Resolution Protocol
1. **Patch the Script**: Update the `chatId` in the source code.
2. **Recompile (Mandatory for Swift)**:
   ```bash
   swiftc -o ~/.hermes/scripts/hermes_monitor ~/.hermes/scripts/hermes_monitor.swift
   ```
3. **Update Cron Jobs**: Periodically verify and update existing Cron Job `deliver` targets to ensure they align with the system architecture.
   ```bash
   hermes cron edit <JOB_ID> --deliver telegram:<CORRECT_ID>
   ```

## 2. Verified Entities (2026-05-18)
- **Jojo (Private)**: `6326497055`
- **Group (高潮不斷)**: `-1003744330314`
- **William (Private)**: `8695583357`
