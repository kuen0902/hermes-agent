---
name: apple-calendar
description: Native macOS automation for Apple Calendar. Manage events (list, create, delete).
version: 1.0.0
author: Hermes
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [apple, macos, automation, applescript, calendar]
---

# Apple Calendar Automation

This skill captures native automation patterns for Apple Calendar on macOS using AppleScript (`osascript`).

## Usage
- Manage events (list, create, delete) locally without relying on Google Calendar APIs.

## 1. Core Patterns & Pitfalls
- **Date String Locales**: Date strings (e.g., `date "2026-05-13 14:00:00"`) in AppleScript are highly sensitive to the system's locale settings and often fail to parse correctly.
- **Verification Probe**: Always use a "List Calendars" probe before creating events in a specific calendar to ensure the target calendar name exists exactly as provided.
- **Creation Logic**: Instead of relying on raw string parsing, construct dates robustly or use the `make new event` command with clearly delineated properties.

## 2. Security & TCC Pitfalls
- **Permission Diagnostics**: If you encounter "Permission denied" or "Not authorized to send Apple events to Calendar", guide the user to **System Settings > Privacy & Security > Automation** and ensure the terminal has permissions for Calendar.
