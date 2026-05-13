# Apple Mail Automation Patterns

This document details proven AppleScript (`osascript`) patterns for automating Apple Mail on macOS, specifically for scenarios where standard CLI tools (like `himalaya` or `mail`) are unavailable or unconfigured.

## 1. Composing Mail with Attachments

Automation of the `send` command is often blocked by macOS Transparency, Consent, and Control (TCC) security policies when running from a non-interactive terminal (returning `BLOCKED: User denied`). 

### The "Draft & Verify" Pattern (Recommended)
Instead of attempting fully automated sending, create the message, attach the file, and set `visible` to `true`. This allows the user to perform a final check and click "Send".

```applescript
tell application "Mail"
    set newMessage to make new outgoing message with properties {subject:"Subject Here", content:"Message body text." & return & return}
    tell newMessage
        set visible to true
        make new recipient at end of to recipients with properties {address:"recipient@example.com"}
        -- Use 'posix file' for file paths to ensure compatibility
        make new attachment with properties {file name:(posix file "/path/to/file.png")} at after last paragraph
    end tell
    activate -- Bring Mail to front
end tell
```

## 2. Detection & Fixes

### Pitfall: Attachment Path Format
- **Issue**: Simply passing a string like `"/tmp/file.png"` to `file name` may fail or result in a missing attachment.
- **Fix**: Wrap the path in `posix file`.
  - ✅ `make new attachment with properties {file name:(posix file "/tmp/img.png")}`
  - ❌ `make new attachment with properties {file name:"/tmp/img.png"}`

### Pitfall: AppleEvent Error (-10000)
- **Symptom**: `execution error: Mail got an error: Camera/Mail happened an error: cannot execute AppleEvent handler. (-10000)`
- **Common Cause**: Security/Sandbox restrictions or corrupted TCC database.
- **Troubleshooting**:
  1. **TCC Reset**: Execute `tccutil reset Automation` or `tccutil reset All` in a terminal (warning: resets all privacy prompts).
  2. **Full Disk Access**: Ensure the executing process (e.g., Terminal, iTerm2, or `hermes-gateway` service) has **Full Disk Access** in System Settings > Privacy & Security.
  3. **Path Permissions**: Files attached from `/tmp/` are generally safer, but attached files from inside `~/.hermes/` or `~/Documents/` might be blocked by Sandbox if the app isn't granted access.
  4. **Alternative**: If AppleScript consistently fails with `-10000`, fall back to sending via the `MEDIA:/path` command in Hermes to bypass the system mail agent entirely.

### Pitfall: Newline Characters
In AppleScript `content` strings, `\n` might literalize. Use the `return` constant for reliable line breaks.
- `content:"Line 1" & return & "Line 2"`

## 3. Quick Probes

List all accounts to verify setup:
```bash
osascript -e 'tell application "Mail" to get name of every account'
```

Check if there are unsent messages in Outbox:
```bash
osascript -e 'tell application "Mail" to count messages of mailbox "Outbox" of outgoing account 1'
```
