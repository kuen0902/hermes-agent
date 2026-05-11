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

### Pitfall: Automated Send Blocked
- **Symptom**: `execution error: Mail got an error: User denied. (-128)`
- **Solution**: 
  1. Change `send` to `set visible to true` + `activate`.
  2. If fully automated sending is mandatory, the User must grant **Full Disk Access** and **Automation** permissions to the Terminal application in System Settings.

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
