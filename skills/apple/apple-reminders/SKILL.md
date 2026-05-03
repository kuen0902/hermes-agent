---
name: apple-reminders
description: "Manage Apple Reminders via native AppleScript (osascript): add, list, complete."
version: 2.0.0
author: Antigravity
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Reminders, tasks, todo, macOS, Apple, applescript]
    related_skills: [apple-notes, apple-mail]
---

# Apple Reminders (Native)

Manage Apple Reminders directly using macOS native AppleScript. This method is more robust than third-party CLI tools like `remindctl`.

## When to Use

- User mentions "reminder" or "Reminders app".
- Creating personal to-dos with due dates that sync to iOS (iPhone/iPad/Mac).
- Managing Apple Reminders lists.

## Quick Reference Recipes

### List Active Reminders
```bash
osascript -e 'tell application "Reminders"
    set output to ""
    set todoList to reminders of list "Reminders" whose completed is false
    repeat with todo in todoList
        set output to output & "- " & (name of todo) & "\n"
    end repeat
    return output
end tell'
```

### Create a Reminder
```bash
osascript -e 'tell application "Reminders" to make new reminder at end of list "Reminders" with properties {name:"Task Name"}'
```

### Create a Reminder with Due Date
```bash
# Note: Date string format depends on system locale (e.g., "2026/05/04 09:00:00")
osascript -e 'tell application "Reminders" to make new reminder at end of list "Reminders" with properties {name:"Call Mom", due date:date "2026/05/04 09:00:00"}'
```

### Complete a Reminder
```bash
osascript -e 'tell application "Reminders" to set completed of first reminder of list "Reminders" whose name is "Task Name" to true'
```

### List All Reminder Lists
```bash
osascript -e 'tell application "Reminders" to get name of every list'
```

## Rules & Pitfalls

1. **List Names**: Default list is usually "Reminders". Verify list names using the "List All Reminder Lists" command if the default fails.
2. **Date Format**: The `date` string in AppleScript is highly dependent on the user's macOS system locale (e.g., MM/DD/YYYY vs DD/MM/YYYY).
3. **Permissions**: Requires "Automation" access to Reminders.app. Check System Settings -> Privacy & Security -> Automation if commands hang or fail.
4. **Completion**: Marking a reminder as completed will hide it from the active list view.

## Verification Checklist

- [ ] Command executed via `terminal`.
- [ ] Output returns the list of tasks or confirmation of creation.
- [ ] New reminder is visible in the Reminders app.
