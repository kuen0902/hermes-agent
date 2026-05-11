# Taiwan MOPS (公開資訊觀測站) Download Guide

For Taiwan listed stocks (e.g., 2330.TW, 3037.TW), MOPS is the authoritative source.

## Navigation Path
1. **Home**: `https://mops.twse.com.tw/mops/web/index`
2. **Search**: Enter stock code (e.g., `3037`).
3. **Menu**: Go to `財報資訊` -> `財務報告書`.
4. **Form**: 
   - Enter `年度` (Taiwan Year = AD - 1911, e.g., 2026 is 115).
   - Enter `公司代號`.
   - Click `查詢`.

## Link Extraction Pattern
Often, clicking the PDF link opens a landing page that looks like a viewer but doesn't trigger a download.

1. **Detection**: If `browser_snapshot` shows a page titled "電子資料查詢作業" with a single filename link.
2. **Extraction**: Use `browser_console` to find the hidden full PDF URL:
   ```javascript
   document.querySelector('a').href
   ```
   The actual URL usually starts with `https://doc.twse.com.tw/pdf/...`.
3. **Download**: Use `curl -L -o <path> "<extracted_url>"` in the terminal.

## Common Bot Detection
- MarketScreener and some IR sites (e.g., Unimicron's official site) may block automated navigation.
- MOPS is generally more accessible via the browser tool but requires specific interaction patterns (Form -> Query -> Link -> Console Extract).
