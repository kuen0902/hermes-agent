---
name: apple-mail
description: "Manage Apple Mail via native AppleScript (osascript): send with attachments, read, search."
version: 1.0.0
author: System Architect
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Email, Apple, macOS, Communication, applescript]
    related_skills: [google-workspace, himalaya, apple-notes]
---

# Apple Mail (Native)

Manage Apple Mail directly using macOS native AppleScript. This is the preferred method on macOS when external SMTP/IMAP configurations are missing or broken, as it uses the user's already-configured accounts in Mail.app.

## Quick Reference Recipes

### Send Email with Attachment (Robust Pattern)
This pattern handles the common error `-10000` by ensuring recipients are added correctly and attachments are anchored after the text.

```bash
osascript -e '
tell application "Mail"
    set newMessage to make new outgoing message with properties {subject:"Subject Here", content:"Body Text\n\n", visible:true}
    tell newMessage
        make new recipient at end of to recipients with properties {address:"recipient@example.com"}
        make new attachment with properties {file name:POSIX file "/path/to/file.csv"} at after last paragraph
        send
    end tell
end tell'
```

### List Recent Sent Emails
Useful for auditing past actions or verifying successful delivery.

```bash
osascript -e '
tell application "Mail"
    set sentFolder to mailbox "Sent" of account 1
    set theMessages to messages of sentFolder
    set total to count of theMessages
    set output to ""
    repeat with i from 1 to (get total)
        if i > 5 then exit repeat
        set msg to item (total - i + 1) of theMessages
        set output to output & i & ". [" & (subject of msg) & "] To: " & (address of first recipient of msg) & "\n"
    end repeat
    return output
end tell'
```

### Read Message Content by Subject
```bash
osascript -e 'tell application "Mail" to get content of first message of inbox whose subject contains "SearchTerm"'
```

## Advanced Execution: Python Wrapper
For complex bodies or file paths, use Python to handle shell escaping:

```python
import subprocess
def send_mail(to, sub, body, attach=None):
    attach_line = f'make new attachment with properties {{file name:POSIX file "{attach}"}} at after last paragraph' if attach else ''
    as_code = f"""
    tell application "Mail"
        set msg to make new outgoing message with properties {{subject:"{sub}", content:"{body}\\n\\n"}}
        tell msg
            make new recipient at end of to recipients with properties {{address:"{to}"}}
            {attach_line}
            send
        end tell
    end tell
    """
    subprocess.run(['osascript', '-e', as_code])
```

## Rules & Pitfalls

1. **Recipients Plural**: Always use `make new recipient at end of to recipients`. Using `recipient` (singular) or omitting `to` often results in `-10000` or `execution error`.
2. **POSIX file**: When attaching, always use `POSIX file "/path/to/file"`. Raw strings will fail.
3. **Attachments Anchor**: Attachments must be placed `at after last paragraph` or a specific character index to avoid Mail crashing or losing the attachment.
4. **Permissions**: Requires "Automation" access to Mail.app. Check `System Settings -> Privacy & Security -> Automation`.
5. **Account Indexing**: Default scripts use `account 1`. If the user has multiple accounts, you may need to specify by name: `account "Work"`.

## Verification Checklist

- [ ] Command executed via `terminal` or `execute_code`.
- [ ] Output returns `SUCCESS` or message ID.
- [ ] Verify by listing the top of the "Sent" mailbox.
