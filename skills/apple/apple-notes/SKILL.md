---
name: apple-notes
description: "Manage Apple Notes via native AppleScript (osascript): create, search, read."
version: 2.0.0
author: Antigravity
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Notes, Apple, macOS, note-taking, applescript]
    related_skills: [obsidian, apple-mail, apple-reminders]
---

# Apple Notes (Native)

Manage Apple Notes directly using macOS native AppleScript. This method is more robust than third-party CLI tools as it bypasses external dependencies.

## When to Use

- User asks to create, view, or search Apple Notes.
- Saving information to Notes.app for cross-device access (iPhone/iPad/Mac).
- When third-party tools like `memo` fail or are missing.

## Quick Reference Recipes

### Create a Note
```bash
osascript -e 'tell application "Notes" to make new note at folder "Notes" with properties {body:"<h1>Title</h1><p>Content here</p>"}'
```

### Search Notes by Title
```bash
osascript -e 'tell application "Notes" to get name of every note whose name contains "SearchTerm"'
```

### Read Note Content
```bash
osascript -e 'tell application "Notes" to get body of note "Exact Note Title"'
```

### List Folders
```bash
osascript -e 'tell application "Notes" to get name of every folder'
```

## Advanced Execution: Python Wrapper

When creating notes with complex HTML bodies or special characters, raw shell escaping via `osascript -e` is brittle. Use a Python script with `subprocess` to pass the body as a clean string.

```python
import subprocess
body = "<h1>Title</h1><p>Content with 'quotes' and <b>formatting</b>.</p>"
cmd = f'tell application "Notes" to make new note with properties {{body:"{body}"}}'
subprocess.run(['osascript', '-e', cmd])
```

## Rules & Pitfalls

1. **HTML Body**: Apple Notes uses HTML for the body. Use `<h1>` for titles and `<p>` for paragraphs.
2. **Folder Existence**: The target folder (e.g., "Notes") must exist. If unsure, list folders first.
3. **Accuracy**: When reading a note, use the exact title returned by a search.
4. **Permissions**: Requires "Automation" access to Notes.app. If it fails with a permissions error, remind the user to check System Settings -> Privacy & Security -> Automation.
5. **No Backgrounding**: Never add `&` to the end of a shell command to avoid backgrounding errors in the agent environment.

## Verification Checklist

- [ ] Command executed via `terminal`.
- [ ] Output returns a note ID or the requested data.
- [ ] For creation, verify by searching for the new title.
