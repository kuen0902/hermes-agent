---
name: data-engineering
description: Umbrella skill for data orchestration, pipeline integrity, and interactive exploration.
category: data
version: 1.0.0
author: Hermes (Curator)
license: MIT
metadata:
  hermes:
    tags: [data-ops, data-science, data-engineering, pipelines, jupyter]
---

# Data Engineering & Operations

This umbrella skill governs the management of data lifecycles—from ingestion and validation to interactive exploration and orchestration.

## 1. Data Ingestion & Integrity
- **Mandatory Checks**: Minimum file size (>1KB), schema validation, and `dropna()` verification for yfinance data.
- **Unstructured Data**: Verify PDF magic bytes and readability via `pdfinfo`.

## 2. Pipeline Orchestration (Sync-Store-Dispatch)
- **Gatherer**: Central source fetching and normalization.
- **Store**: Centralized JSON truth (e.g., `central_data.json`).
- **Dispatch**: Multi-channel distribution (Telegram, Slack) from the store.
- **Lock-Based Debouncing**: Prevent redundant bursts using `.lock` files.

## 3. Interactive Exploration (Data Science)
- **Jupyter Workflows**: Iterative analysis using live Jupyter kernels.
- **Visualization**: Techniques for rendering CJK-compatible charts and aligned tables.

## 4. Backfilling & Scaling
- **Auditing**: Inventory checks and resampling integrity (e.g., 1m to 5m bar consistency).
- **Resilience**: Concurrency limits to avoid WAF blocks and self-healing logic for truncated files.
