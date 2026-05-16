---
name: apple
description: General macOS-specific automation — Finder, TCC permissions, screenshots, and system tasks.
version: 1.1.0
author: Hermes
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [apple, macos, automation, applescript, permissions, system]
---

# Apple & macOS System Automation

This core skill covers general macOS system automation, terminal fallbacks, and security troubleshooting. 
*Note: For app-specific automation, use `apple-mail`, `apple-calendar`, etc.*

## 1. Visual Reporting & Screen Capturing

- **User Preference (The "No Artifact" Rule)**: 
  - **Avoid Permanent Storage**: Do not permanently store screenshot files unless explicitly instructed.
  - **The "MEDIA" Pipeline**: Generate images into `~/.hermes/scratch/`, trigger `MEDIA:/path/to/file`, and consider it done. 
- **Screencapture TCC Errors & Fallbacks**:
  - `screencapture` often fails in headless sessions. 
  - **Workaround (PIL/Pillow Rendering)**: Use the `PIL` (Pillow) library to generate a simulated terminal window.
  - **Font Support**: Explicitly use Chinese-compatible fonts (e.g., `/System/Library/Fonts/PingFang.ttc` or `Hiragino Sans GB.ttc`).
- **Terminal Rendering tools**: 
  - **mdcat**: Default tool for opening `.md` files in iTerm2 (`/opt/homebrew/bin/mdcat`).
  - **Rich Alignment**: For complex tables mixing CJK and Emojis, use Python's `rich` library or a manual PIL drawing script to guarantee column alignment.

## 2. Native App Automation (Mail & Calendar)

### Apple Mail (`apple-mail`)
- **Composition Patterns**:
  - **Draft & Verify**: When composing, set `visible: true` and use `activate` to allow manual review if automated `send` is blocked by TCC.
  - **Attachments**: Always use `posix file "/path/to/file"` coercion.
- **TCC Pitfalls**: The `send` command often fails; fallback to showing the window instead of failing silently.

### Apple Calendar (`apple-calendar`)
- **Date String Locales**: Dates in AppleScript are locale-sensitive; avoid raw string parsing.
- **Verification Probe**: Use "List Calendars" before creation to ensure exact name matching.
- **Robust Creation**: Construct dates property-by-property or use `make new event` with clear types.

## 3. Permissions & Diagnostics (TCC)

When tools fail with "Permission denied", "Execution error", or "Not authorized":
1. **Setup**: Guide user to **System Settings > Privacy & Security > Automation** and ensure the terminal/app has permissions.
2. **Reset**: Use `tccutil reset AppleEvents` to force a priority re-prompt if toggles are missing.

## 3. High-Efficiency Patterns

### The Python Wrapper Pattern
Avoid multi-segment shell commands. Write the AppleScript logic inside a Python script:
```python
import subprocess
script = """
tell application "Finder"
    -- logic here
end tell
"""
result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
```

### Swift-Mac-Automation Bridge
- **When to use**: Use Swift when AppleScript is too slow or `pyobjc` is too bloated.
- **Rules**:
  - **Swift-to-Python**: Use absolute paths for the Python executable (e.g., `/Users/bookid/workspace/hermes-agent/venv_314/bin/python`).
  - **Cron Execution**: Wrap `.swift` scripts in a `.sh` file and call via `/usr/bin/swift` to avoid the agent misidentifying the file as Python.
  - **Notification Bypass**: Prefer calling `NSAppleScript` from Swift to send notifications without a Bundle ID.

### macOS Home Profile Access (Environment Mapping)
When a user refers to a name that matches their current username (e.g., `bookid`), they mean their Home Directory (`~`).
- **Strategy**: Always resolve via `pathlib.Path.home()` or `os.path.expanduser('~')`.
- **TCC Warnings**: Note that `Documents`, `Downloads`, and `Desktop` require explicit OS-level permissions.

### Markdown & CLI Visualization
- **Finder Quick Look**: To enable rich Markdown previews in Finder (Spacebar):
  - **Tool**: `sbarex-qlmarkdown` (`brew install --cask qlmarkdown`).
  - **Permissions**: Grant "Screen Recording" or "Quick Look" permissions in System Settings -> Privacy & Security -> Extensions.
