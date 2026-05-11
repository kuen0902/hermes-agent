# Data Fetch Reliability (Yahoo Finance / yfinance)

When building automated stock monitoring systems, data availability and API stability are the primary failure points.

## 1. Metadata vs. Fast Info (404 Not Found)

Using `yf.Ticker(symbol).info` often triggers a `404: Quote not found for symbol` error or is extremely slow because it fetches hundreds of properties from a specific Yahoo endpoint that is frequently throttled or broken.

**Recommended Approach:**
1.  **Prioritize `fast_info`**: `ticker.fast_info` provides essential metrics (last_price, previous_close) much faster and with fewer failures.
2.  **Fallback to `history`**: If `fast_info` is empty or NaN, use `ticker.history(period="1d")` to get the latest close price.
3.  **Avoid `.info` for high-frequency scripts**: Only use `.info` if you absolutely need metadata like "Industry" or "Sector" that doesn't change often.

## 2. Throttling (HTTP 429 Too Many Requests)

Yahoo Finance heavily throttles requests from cloud IPs or high-frequency scrapers.

**Mitigation:**
- **Centralize**: Fetch all tickers in ONE script (Sync) and save to a JSON cache. All other bots (Personal, William, Group) must read from this cache instead of making their own API calls.
- **Batched Fetch**: Use `yf.download(tickers)` or loop with small delays (`time.sleep(0.4)`) to stay under the radar.
- **User-Agent**: Always rotate or set a standard User-Agent (e.g., `Mozilla/5.0`).

## 3. Delisting / Symbol Errors
Symbols ending in `.TW` (TSE) or `.TWO` (OTC) sometimes shift. If both return 404, the stock might be delisted or renamed.
