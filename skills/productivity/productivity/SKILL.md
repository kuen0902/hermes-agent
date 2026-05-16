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

# Productivity & Utilities

This umbrella skill captures utility tools for managing API usage, environment configurations, and general productivity workflows.

## References

- `references/japan_travel_strategy.md` (Okinawa hotel tiers, platform optimization, and HSR-RMQ logistics)

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

## 3. Logistics & Travel Strategies
See `references/japan_travel_strategy.md` for specific regional optimizations (e.g., Okinawa, Taiwan HSR-Airport transfers).
