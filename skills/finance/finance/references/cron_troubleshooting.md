# Cron Troubleshooting & Execution Reports

In the Hermes environment, `no_agent=True` cron jobs write their execution logs to specific markdown files. This is the primary diagnostic data for automated monitoring failures.

## Log Locations
- **Job Metadata**: SQLite store managed by the `cronjob` tool.
- **Execution Output**: `~/.hermes/cron/output/<job_id>/<timestamp>.md`.

## Common Error Patterns (Found in output MDs)

### 1. Script Not Found
**Error**: `Script not found: /Users/bookid/.hermes/scripts/run_bin/hermes_monitor_personal.sh`
**Cause**: The `script` path in the cronjob configuration is incorrect or uses a relative path that doesn't resolve to `~/.hermes/scripts/`.
**Fix**:
1. Check the filesystem: `ls -la ~/.hermes/scripts/`.
2. Update the job: `cronjob(action='update', job_id='...', script='absolute_or_correct_relative_path')`.

### 2. ModuleNotFoundError (Python)
**Error**: `ModuleNotFoundError: No module named 'yfinance'`
**Cause**: The cron job is running the script with the default system Python instead of the project venv.
**Fix**: Ensure the `.sh` wrapper specifies the venv Python or the `script` field in cron is an absolute path to the venv binary.

### 3. Permission Denied
**Error**: `/bin/bash: path/to/script: Permission denied`
**Cause**: The script is not executable.
**Fix**: `chmod +x path/to/script`.

### 4. Database Integrity & Recovery
**Error**: `Cron database corrupted and unrepairable: Invalid \uXXXX escape`
**Cause**: The `jobs.json` file (usually at `~/.hermes/cron/jobs.json`) contains malformed Unicode escape sequences, often introduced when an LLM writes CJK characters or complex prompts.
**Fix**:
1. Locate the file: `~/.hermes/cron/jobs.json`.
2. Inspect lines around the error column (printed in the error message).
3. Repair invalid escapes (e.g., `\uXXXX` where XXXX is not 4 hex digits) or replace them with direct UTF-8 characters.
4. Verify JSON validity: `python3 -m json.tool ~/.hermes/cron/jobs.json`.

## 5. Verification Commands
```bash
# List last 5 outputs for a specific job
ls -lt ~/.hermes/cron/output/<job_id>/ | head -n 5

# Inspect the most recent error
cat $(ls -dt ~/.hermes/cron/output/<job_id>/*.md | head -1)
```
