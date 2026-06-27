---
name: research
description: "Umbrella skill for academic and market research, paper discovery, and signal monitoring."
version: 1.0.0
author: "Hermes (Curator)"
license: MIT
metadata:
  hermes:
    tags: [research, arxiv, polymarket, signal-monitoring, literature-review]
---

# Research Operations & Signal Monitoring

This umbrella skill captures patterns for deep research, academic deep-dives, and real-time market/academic signal tracking.

## 1. Academic Research (arXiv)
- **Discovery**: Search by keywords, authors, or categories.
- **Extraction**: Extract content from PDF URLs directly via `web_extract`.

## 2. Market Signals (Polymarket)
- **Monitoring**: Track event contracts, orderbooks, and probability shifts.
- **Verification**: Cross-reference with standard news/web search to validate high-volatility shifts.

## 3. Feed Monitoring (Blogwatcher)
- Maintain RSS/Atom lists in `~/.hermes/research/feeds.json`.
- Alert on specific keywords or domain shifts.
