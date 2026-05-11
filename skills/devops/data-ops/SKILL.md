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

## Pitfalls
- **`__main__` Guard Corruption**: Ensure code generation correctly parses `"__main__"` without escaping errors.
- **File-Write Races**: Re-read file content before writing if sibling agents are active.
- **Sandbox Limits**: Use `terminal` for large-scale processing to leverage the user's local Python environment (Pandas/NumPy).
