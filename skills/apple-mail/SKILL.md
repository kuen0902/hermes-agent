---
name: apple-mail
description: Native macOS automation for Apple Mail. Read, search, list messages, and compose emails.
version: 1.0.0
author: Hermes
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [apple, macos, automation, applescript, mail]
---

# Apple Mail Automation

This skill captures native automation patterns for Apple Mail on macOS using AppleScript (`osascript`).

## Usage
- Read, search, and list messages.
- Compose emails with attachments.

## 1. Composition Patterns
- **Draft & Verify Pattern**: When composing an email, set `visible: true` and use `activate` to bring the window to the front. This allows manual review and sending when TCC (Transparency, Consent, and Control) blocks automated `send` actions.
- **Attachments**: When attaching files, always use the `posix file "/path/to/file"` coercion in AppleScript. Direct string paths are unreliable and frequently fail.

## 2. Security & TCC Pitfalls
- **The Send Command**: The `send` command is high-risk and often results in "User denied" or AppleEvent timeout errors. **Always fallback to showing the window for user confirmation** instead of failing silently.
- **Permission Diagnostics**: If you encounter "Permission denied", guide the user to **System Settings > Privacy & Security > Automation** and ensure the terminal has permissions for Mail.
