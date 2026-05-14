# Automation Script Hardening (TAIEX Portfolio context)

When writing or fixing shell scripts and Python automation for the Finance workflow, follow these non-negotiable rules to ensure stability in Cron and limited PATH environments.

## 1. Absolute Path Integrity
Cron environments often have a stripped-down `PATH`. Implicit binary resolution is a primary cause of failure.
- **Rule**: Always use absolute paths for the `hermes` binary: `/Users/bookid/.local/bin/hermes`.
- **Rule**: Always use the absolute path of the project virtual environment (venv) for Python execution.
- **Venv Path**: `/Users/bookid/workspace/hermes-agent/venv/bin/python`.
- **Trap**: Do NOT use `python3` or `#!/usr/bin/env python3` in shell scripts; explicit path injection is required.

**Example Pattern (Shell Script):**
```bash
#!/bin/bash
PYTHON="/Users/bookid/workspace/hermes-agent/venv/bin/python"
HERMES="/Users/bookid/.local/bin/hermes"

# Use the variables
$PYTHON /path/to/script.py
$HERMES --profile star-platinum gateway start
- **Venv Path**: `/Users/bookid/workspace/hermes-agent/venv_314/bin/python`.

## 2. Python Version (3.14+)
The primary execution environment has been upgraded to **Python 3.14.4 (Arm64)** as of 2026-05-15.
- **Rule**: Use the performance-optimized `type` alias (PEP 695) where appropriate (e.g., `type PortfolioDict = dict[...]`).
- **Rule**: Leverage Python 3.14 features like enhanced error messages and typing improvements.
- **Verification**: Always run a syntax check before finishing a task: `[VENV_PYTHON] -c "import [script_name]"`.

## 3. Redirects & Logging
Ensure all cron outputs are redirected to the correct log directory for audit.
- **Log Directory**: `~/.hermes/logs/`
- **Pattern**: `[COMMAND] > /Users/bookid/.hermes/logs/[name].log 2>&1`
- **Service Verification**: After starting a service (like Star Platinum Gateway), immediately verify status via log inspection or `ps aux`.
