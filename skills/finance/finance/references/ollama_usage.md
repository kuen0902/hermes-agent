# Ollama Cloud Usage Tracking (Ollama Pro)

As of May 2026, Ollama Cloud (Pro/Max) usage metrics (Session and Weekly limits) are visible in the web UI at `ollama.com/settings`, but are not yet exposed via a stable public API.

## Current Metrics (State of bookid2000)
- **Session Usage**: Short-term limit (resets every few hours).
- **Weekly Usage**: Main limit (resets weekly).
- **Model Efficiency**: Light models (e.g., Gemini-3-Flash) consume significantly less quota than large models (Gemma-4:31B).

## Monitoring Approaches
1. **Manual Screenshot**: The fastest way is to ask the user for a screenshot of the `ollama.com` usage page and use `vision_analyze` to extract the percentages (e.g., "Weekly: 27.9%").
2. **Key-based Exploration**: API Keys found in the "Keys" tab may eventually support usage queries at `https://ollama.com/api/v1/usage` (Experimental).
3. **Internal CLI**: `ollama list` and `ollama ps` track local model stats but NOT cloud quota.

## Usage History (Archive)
| Date | User | Session % | Weekly % | Status |
| :--- | :--- | :--- | :--- | :--- |
| 2026-05-04 | bookid2000 | 5.3% | 27.9% | Healthy |
