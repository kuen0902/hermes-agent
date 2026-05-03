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
    related_skills: [obsidian, apple-mail]
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

## Rules & Pitfalls

1. **HTML Body**: Apple Notes uses HTML for the body. Use `<h1>` for titles and `<p>` for paragraphs.
2. **Folder Existence**: The target folder (e.g., "Notes") must exist. If unsure, list folders first.
3. **Accuracy**: When reading a note, use the exact title returned by a search.
4. **Permissions**: Requires "Automation" access to Notes.app. If it fails with a permissions error, remind the user to check System Settings -> Privacy & Security -> Automation.

## Verification Checklist

- [ ] Command executed via `terminal`.
- [ ] Output returns a note ID or the requested data.
- [ ] For creation, verify by searching for the new title.
