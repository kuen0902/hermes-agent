---
name: apple-mail
description: "Read and search macOS Mail.app emails via AppleScript.⚠️ PILLARS/SCOPE: When querying large mailboxes, always LIMIT the scope (e.g., top 5 messages, or search by specific subject) to ensure performance and reliable output. Never attempt to read the entire mailbox at once."
version: 1.0.0
author: Antigravity
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Mail, Email, Apple, macOS, applescript]
    related_skills: [apple-notes]
---

# Apple Mail (Native)

Read and search emails from the native macOS Mail.app using AppleScript.

## When to Use

- User asks to read recent emails or search for specific messages.
- Checking for confirmation codes or technical notifications in the inbox.
- Summarizing recent communications.

## Quick Reference Recipes

### List Recent Subjects (Latest 5)
```bash
osascript -e 'tell application "Mail"
    set output to ""
    set theMessages to messages of inbox
    set msgCount to count of theMessages
    if msgCount > 5 then set msgCount to 5
    repeat with i from 1 to msgCount
        set msg to item i of theMessages
        set output to output & i & ". [" & (subject of msg) & "] From: " & (sender of msg) & "\n"
    end repeat
    return output
end tell'
```

### Search Emails by Subject
```bash
osascript -e 'tell application "Mail" to get subject of every message of inbox whose subject contains "Keyword"'
```

### Read Full Content of a Message
```bash
# Change '1' to the desired index from the list
osascript -e 'tell application "Mail" to get content of message 1 of inbox'
```

## Rules & Pitfalls

1. **Privacy**: Always inform the user before reading full email content.
2. **Mail.app State**: Mail.app must be running or allowed to launch.
3. **Index Sensitivity**: Indices in AppleScript are 1-based.
4. **Volume**: Large inboxes may take a few seconds to query; limit results to the latest 5-10 by default.

## Verification Checklist

- [ ] Command returns a list of subjects or text content.
- [ ] No "Permission denied" errors.
- [ ] Content matches user expectations for the specific query.
