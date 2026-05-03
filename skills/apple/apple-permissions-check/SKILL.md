---
name: apple-permissions-check
description: "Diagnose and guide users to fix macOS TCC/Automation permissions for Apple skills."
version: 1.0.0
author: Antigravity
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Permissions, TCC, macOS, Security, Automation, Setup]
    related_skills: [apple-notes, apple-mail, apple-reminders]
---

# macOS Permissions Diagnosis

Use this skill when Apple ecosystem tools (Notes, Mail, Reminders) fail with "Permission denied", "Execution error", or "Not authorized" messages.

## When to Use

- `apple-notes`, `apple-mail`, or `apple-reminders` fails with a permission error.
- The user asks "Why can't you access my mail/notes?".
- After a fresh installation or macOS update.

## Diagnostic Recipes

### 1. Check App Responsiveness
Test if the app can answer a simple query. If this fails with a "not allowed" error, permissions are missing.
```bash
# Test Notes
osascript -e 'tell application "Notes" to count folders'
# Test Mail
osascript -e 'tell application "Mail" to count messages of inbox'
# Test Reminders
osascript -e 'tell application "Reminders" to count lists'
```

### 2. Guide the User to System Settings
If diagnostic #1 fails, provide these exact steps to the user:
1. Open **System Settings** (系統設定).
2. Go to **Privacy & Security** (隱私權與安全性).
3. Select **Automation** (自動化).
4. Find the terminal or app running Hermes (e.g., `Terminal`, `iTerm2`, or `Code`).
5. Ensure the switches for **Notes**, **Mail**, and **Reminders** are all **ON**.

### 3. Reset Permissions (Advanced)
If the user previously denied access and the toggle is missing, use this to force a re-prompt:
```bash
tccutil reset AppleEvents
```

## Communication Rules

1. **Be Diagnostic, Not Apologetic**: Explain that this is a macOS security feature (TCC) designed to protect their privacy.
2. **Step-by-Step**: Provide clear, numbered steps as shown above.
3. **Verify**: After the user says they've granted permissions, re-run the diagnostic check in #1.

## Common Pitfalls

- **System Events**: Sometimes the "System Events" permission is also needed. If the above fails, check "Privacy & Security -> Accessibility" as well.
- **Background Processes**: If Hermes is running as a background daemon (via launchd), it may need "Full Disk Access".
