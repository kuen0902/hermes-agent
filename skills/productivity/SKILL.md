---
name: productivity
description: Personal productivity and API consumption utilities.
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [productivity, api, usage, credits]
---

# Productivity & Workplace Operations

This umbrella skill handles the orchestration of office, planning, and information management tools.

## 1. Google Workspace & Office
- **GWS CLI**: Manage Gmail, Calendar, Drive, and Sheets.
- **PowerPoint**: Programmatic creation and editing of `.pptx` decks.
- **Meeting Summarization**: Teams meeting pipeline orchestration.

## 2. Planning & CRM
- **Linear**: Manage issues and projects via GraphQL.
- **Airtable**: Relational data management via REST API.
- **Notion**: Page and database operations using the Notion API.

## 3. Document Processing
- **PDF Manipulation**: Edit PDFs via `nano-pdf` or manipulate text/images.
- **Maps**: Geocoding, routing, and timezones.

## 1. API Usage Tracking

### Tavily API
Monitor consumption of search, crawl, and extract credits.
- **Credit Check**: Use `curl` to hit `https://api.tavily.com/usage`.
- **Mandatory Logging**: Whenever `web_search` is performed, call the local `record_usage.py` script to ensure local tracking remains in sync.
- **Sync Latency**: Be aware that the API endpoint may lag 10-15 minutes behind the web dashboard.

## 2. Terminal Environment & UX

### Markdown Rendering
- **Preferred Renderer**: Use `glow` (at `/opt/homebrew/bin/glow`) for files with complex tables or CJK characters (Traditional Chinese).
- **Secondary Renderer**: Use `mdcat` (at `/opt/homebrew/bin/mdcat`) for quick previews of standard text-heavy files.
- **Pitfall (CJK Width)**: `mdcat` often fails to align tables correctly when mixed with Chinese characters or Emojis. Switch to `glow` automatically if the user complains about "messy tables".

### Visual Media & Screenshots
- **Persistence Policy**: Screenshots are ephemeral; save to `~/.hermes/scratch/` and use `MEDIA:`. 
- **High-Precision Rendering**:
  - **Fallback for CJK**: When `mdcat` or `glow` fail on CJK table alignment, use the PIL-based rendering engine.
  - **Font**: Use `/System/Library/Fonts/PingFang.ttc` or `/Library/Fonts/Arial Unicode.ttf`.
  - **Dynamic Height**: Calculate height based on wrapped lines to prevent clipping.
  - **Templates**: `templates/render_md_v2.py`.

## 4. Document & Information Management

### OCR & PDF Processing
- Use `ocr-and-documents` patterns for extracting text from scans and layout-heavy PDFs.
- **Tools**: `pymupdf` (fast text) vs `marker-pdf` (better layout/math).

### Notion Integration
- Sync research and task logs to Notion databases using the `ntn` CLI or REST API.
- **Workflow**: Generate markdown locally -> upload blocks to Notion page.

## 5. Personal Knowledge Management (PKM)
- **Note-taking Systems**: Integrated workflows for Obsidian, Dendron, or Logseq style management.
- **Local Collections**: Search, link, and refactor markdown notes in `~/.hermes/brain/`.
- **Zettelkasten**: Automated backlinking and graph-aware research.

