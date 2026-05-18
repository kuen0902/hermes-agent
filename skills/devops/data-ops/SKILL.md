---
name: data-ops
description: Data engineering and operations — ingestion, integrity, validation, and orchestration patterns.
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [data, engineering, validation, integrity, pipeline, orchestration]
---

# Data Operations (DataOps)

This skill encompasses patterns for managing data life cycles: from ingestion and integrity checks to multi-source pipeline validation and orchestration.

## 1. Data Integrity & Health Checks

Mandatory validation before data is accepted into the filesystem or merged.

### CSV & Structured Data
- **Minimum Size**: Files < 1KB often indicate failed downloads or header-only data.
- **Schema Validation**: Verify presence of required headers.
- **yfinance Guard**: Downloaded CSVs containing only NaNs return `df.empty == False`. Always check `len(df.dropna()) > 0`.

### PDF & Unstructured Data
- **Magic Bytes**: Must start with `%PDF-`.
- **Readability**: Verify using `pdfinfo` or `PyMuPDF` (fitz).

## 2. Pipeline Validation (Multi-Source)

Workflow for merging datasets from different streams (e.g., historical vs. live logs).

1. **Source Collection**: Stage data in temporary directories.
2. **Pre-merge Metrics**: Check file counts and total row sums.
3. **Gate Check**: Abort if corruption rate > 5% or file count drop-off > 10%.
4. **Overlap Analysis**: Use `comm` or Python to identify common/unique keys between sources.
5. **Execution & Audit**: Verify the union count and date range coverage after merge.

## 3. Orchestration Architecture

The **"Sync-Store-Dispatch"** pattern prevents API rate-limiting and ensures consistency across multiple monitors.

- **The Gatherer (Sync)**: Single entry point that fetches source data (e.g., from Numbers or API) and normalizes it.
- **The Store (Cache)**: Centralized JSON representation of truth (e.g., `central_data.json`).
- **The Dispatchers (Monitors)**: Downstream consumers that read from the store and format for specific channels (Telegram, Slack, AI summary).

### Lock-Based Debouncing
Prevent flooding and redundant bursts by checking a `.lock` timestamp.
- **Recommended Window**: 8 minutes (`480s`) for 10-minute cron jobs.

### Swift Mach-O Binary Wrapping
When Cron jobs or orchestrators fail to run Swift-compiled Mach-O executables (common with `no_agent=True` scripts):
1. **Do NOT assume Python interpreter**: If a script has no extension (or is `.swift` but compiled to binary), **do not** invoke `python` or `python3`.
2. **Create a `.sh` wrapper**: Use `#!/bin/bash` directly calling the binary or Swift executable path.
   ```bash
   #!/bin/bash
   /path/to/SwiftBinary arg1 arg2
   ```
3. **Handle Empty Output in `no_agent` Mode**: Cron jobs with `no_agent=True` mark `error` if stdout is empty.
   - **Fix**: Add a fallback `echo "Status: OK - No alerts triggered"` if the binary produces no output.
4. **Orchestrator Logic Update**: If the orchestration script (Swift/Python) dynamically executes children, ensure it detects file types:
   - `.sh` → run with `/bin/bash`
   - `.py` → run with venv python
   - No extension / `.swift` binary → run directly
   - `.swift` source → run with `swift`

## Pitfalls
- `__main__` Guard Corruption: Ensure code generation correctly parses `"__main__"` without escaping errors.
- File-Write Races: Re-read file content before writing if sibling agents are active.
- Sandbox Limits: Use `terminal` for large-scale processing to leverage the user's local Python environment (Pandas/NumPy).
- Silent Failures in `no_agent` Mode: Always ensure scripts produce *some* stdout output, even if just "OK" or "No changes", to prevent Cron from marking the job as failed.
