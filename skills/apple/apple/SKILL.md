---
name: apple
description: Apple/macOS-specific skills — iMessage, Reminders, Notes, FindMy, and macOS automation.
version: 1.0.0
author: Hermes
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [apple, macos, automation, applescript, mail, calendar, numbers, permissions]
---

# Apple & macOS Automation

This umbrella skill captures native automation patterns for the Apple ecosystem on macOS, primarily using AppleScript (`osascript`) and native CLI tools.

## References

- `references/mail_automation.md` (Composing, attachments, and security workarounds)
- `references/macos_markdown_quicklook.md` (Enabling rich .md previews in Finder)

## 1. Core Applications

### Visual Reporting & Screen Capturing

- **User Preference (The "No Artifact" Rule)**: 
  - **Avoid Permanent Storage**: Unless explicitly instructed otherwise (e.g., "save this for email", "put it on my desktop"), do not permanently store screenshot files.
  - **The "MEDIA" Pipeline**: Generate the image into the `~/.hermes/scratch/` directory, trigger the `MEDIA:/path/to/file` response, and consider the task complete. 
  - **Clipboard First**: For screenshots, favor immediate display over file system pollution.

- **Screencapture TCC Errors & Fallbacks**:
  - **Problem**: `screencapture` often fails or returns a black image in non-interactive sessions. 
  - **Workaround (PIL/Pillow Rendering)**: If a visual of terminal output or a specific file is needed and native capture fails, use the `PIL` (Pillow) library to generate a simulated terminal window.
  - **Font Support**: On macOS, explicitly search for and use Chinese-compatible fonts (e.g., `/System/Library/Fonts/PingFang.ttc` or `Hiragino Sans GB.ttc`) to avoid "tofu" boxes (encoding blocks).
  - **Window Decoration**: Draw basic window chrome (red/yellow/green buttons) to distinguish simulated screenshots from raw data.

- **Terminal Rendering tools**: 
- **mdcat**: Default tool for opening `.md` files. When asked to "open a markdown file", always prefer `/opt/homebrew/bin/mdcat` in an `iterm2` window before attempting any screenshot.
  - **CJK Font Support**: When using PIL fallbacks, explicitly prioritize `/Library/Fonts/Arial Unicode.ttf` or `/System/Library/Fonts/STHeiti Light.ttc` for perfect Traditional Chinese rendering without garbled characters.
  - **Rich Alignment**: For complex tables (mixing CJK, English, and Emojis), standard CLI tools (mdcat, glow) often fail. Use Python's `rich` library or a manual PIL drawing script to guarantee physical alignment of columns.
    
### System Commands & Pitfalls

- **Screencapture TCC Errors**: `screencapture` often fails in headless or non-interactive terminal sessions on macOS (e.g., `could not create image from display`). 
  - **Workaround 1: Browser Vision**: For web content, use `browser_navigate` + `browser_vision`.
  - **Workaround 2: Terminal Simulation (PIL Fallback)**: If a visual of terminal output or a specific file (like `SOUL.md`) is requested and native screenshot fails (returns black), use Python's `PIL` (Pillow) to generate a high-fidelity rendering of the text in an iTerm-style frame. Use `ImageDraw` to simulate the window chrome (buttons, title bar) and `ImageFont` (e.g., `/System/Library/Fonts/Monaco.ttf`) for the monospaced look. This fulfills the user's need for a "visual confirmation" even when GUI access is restricted.
  - **Setup**: Instruct the user to grant "Screen Recording" permissions to the terminal application to attempt native capture again.
- **AppleScript (osascript) Keys**: `keystroke` automation via `System Events` often triggers security blocks ("not allowed to send keystrokes"). Prefer direct application object model manipulation over simulated keystrokes.

### Apple Mail
- **Usage**: Read, search, and list messages; compose with attachments.
- **Pattern**: For composing, use the **Draft & Verify** pattern (see `references/mail_automation.md`). Set `visible: true` and `activate` to allow manual sending when TCC blocks automated `send`.
- **Pitfall**: When attaching files, always use `posix file "/path/to/file"` in AppleScript. Direct string paths are unreliable.
- **Security**: The `send` command is high-risk and often results in "User denied" errors. Always fallback to showing the window for user confirmation.

### Apple Calendar
- **Usage**: Manage events (list, create, delete).
- **Pitfall**: Date strings (`date "..."`) are sensitive to system locale. Use the "List Calendars" probe before creating events in a specific calendar.

### Apple Numbers
- **Usage**: Manage spreadsheets, data entry, and reports.
- **Pattern**: Prepend a single quote (`'`) to strings that look like numbers (e.g., stock IDs) in AppleScript to force text formatting.
- **Optimization**: For large tables, build a tab-separated string in AppleScript and parse it in Python to avoid slow cell-by-cell retrieval.

## 2. Permissions & Diagnostics (TCC)

When tools fail with "Permission denied", "Execution error", or "Not authorized":
1. **Probe**: Run a simple count (e.g., `tell application "Mail" to count messages of inbox`).
2. **Setup**: Guide user to **System Settings > Privacy & Security > Automation** and ensure the terminal/app has permissions for the specific Apple app.
3. **Reset**: Use `tccutil reset AppleEvents` to force a priority re-prompt if toggles are missing.

## 3. High-Efficiency Patterns

### The Python Wrapper Pattern
Avoid multi-segment shell commands. Write the AppleScript logic inside a Python script:
```python
import subprocess
script = """
tell application "Numbers"
    -- logic here
end tell
"""
result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
```

### macOS Home Profile Access (Environment Mapping)
When a user refers to a name that matches their current username (e.g., `bookid`), they are typically referring to their Home Directory (`~`).
- **Strategy**: Always resolve via `pathlib.Path.home()` or `os.path.expanduser('~')`.
- **Enumeration**: Use `[f for f in root.iterdir() if f.is_dir()]` for a clean list of access points.
- **TCC Warnings**: Note that `Documents`, `Downloads`, and `Desktop` require explicit OS-level permissions. If a script returns 0 items for these but they exist, it's a TCC permission issue.

### Markdown & CLI Visualization
- **Finder Quick Look**: To enable rich Markdown previews in Finder (Spacebar), use the following setup:
  - **Tool**: `sbarex-qlmarkdown`.
  - **Install**: `brew install --cask qlmarkdown`.
  - **Rebuild Cache**: `qlmanage -r && qlmanage -r cache && killall Finder`.
  - **Permissions**: Grant "Screen Recording" or "Quick Look" permissions in System Settings -> Privacy & Security -> Extensions.
  - **Quirks**: If it fails, run `xattr -cr /Applications/QLMarkdown.app` to remove the quarantine flag and open the app once manually.

### The Lock-Based Debouncing Pattern
When running automated scripts via cron, use a timestamped `.lock` file (e.g., in `~/.hermes/data/`) to prevent overlapping executions.

## See Also
- `finance`: For TAIEX/Portfolio automation involving Numbers.
- `productivity`: For general utility automation.
