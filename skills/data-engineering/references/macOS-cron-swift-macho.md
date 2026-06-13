# Hermes Cron Job & Orchestrator Troubleshooting (macOS Swift/Mach-O)

## Context
Swift-compiled scripts on macOS produce Mach-O 64-bit ARM64 executables. These binaries have no extension (or are `.swift` but compiled). Cron or Python-based orchestrators often misidentify them as Python scripts, leading to `SyntaxError: Non-UTF-8` or `invalid UTF-8` errors.

## Detection
```bash
file /path/to/script
# Output: Mach-O 64-bit executable arm64
```

## Resolution Steps

### 1. Do NOT Use Python Interpreter
Never invoke `python` or `python3` on a Mach-O binary. It will fail with UTF-8 errors.

### 2. Create Shell Wrappers
For every Swift binary used in Cron (`no_agent=True`), create a `.sh` wrapper:

**Template:**
```bash
#!/bin/bash
/path/to/SwiftBinary --arg1 value1 --arg2 value2
```

**Example:**
```bash
# run_hermes_monitor_group.sh
#!/bin/bash
/Users/bookid/.hermes/scripts/hermes_monitor --profile group
```

### 3. Handle `no_agent=True` Empty Output
Cron jobs with `no_agent=True` expect **non-empty stdout**. If the script runs successfully but produces no output (silent success), Cron marks it as `error`.

**Fix:**
Wrap the call to ensure output:
```bash
#!/bin/bash
OUTPUT=$(/hermes_monitor --profile group 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    if [ -n "$OUTPUT" ]; then
        echo "$OUTPUT"
    else
        echo "OK - No alerts triggered"
    fi
    exit 0
else
    echo "ERROR: $OUTPUT"
    exit $EXIT_CODE
fi
```

### 4. Orchestrator Type Detection
If orchestrating multiple script types (Swift, Python, Shell), implement dynamic dispatch:

**Swift Logic:**
```swift
if name.hasSuffix(".sh") {
    process.executableURL = URL(fileURLWithPath: "/bin/bash")
    process.arguments = [scriptPath] + args
} else if name.hasSuffix(".py") {
    process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
    process.arguments = ["/Users/bookid/.hermes/.venv/bin/python", scriptPath] + args
} else {
    // No extension or .swift binary: run directly
    process.executableURL = URL(fileURLWithPath: scriptPath)
    process.arguments = args
}
```

## Architecture Alignment
- **Orchestrator Pattern**: "Sync-Store-Dispatch"
- **Cron Schedule**: Typically `*/10 9-12 * * 1-5` (10-min intervals during market hours)
- **Delivery Mode**: 
  - `local`: Only log (silent if no alert)
  - `telegram:CHAT_ID`: Push to Telegram (recommended for real-time alerts)

## Common Pitfalls
1. **Mach-O treated as Python**: Always check file type with `file` command.
2. **Silent Success**: `no_agent=True` scripts must output *something* (even "OK").
3. **Hardcoded Paths**: Use `~/.hermes/scripts/` relative paths in Cron, not absolute paths (Cron rejects absolute paths).
4. **Encoding Errors**: Swift source files must be UTF-8. BOM or non-UTF-8 will cause compile/runtime errors.
