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

## Programmatic PDF Retrieval (The Reliable Path)

When `browser_navigate` directly to the PDF fails or results in a 404, use this `curl` POST method to bypass the MOPS landing page logic:

1. **Endpoint**: `https://doc.twse.com.tw/server-java/t57sb01`
2. **Payload**: `step=9&kind=A&co_id={STOCK_ID}&filename={FILENAME}`
3. **Filename Convention**: Usually `YYYY01_{STOCK_ID}_AI1.pdf` for Q1 (Ming-guo Year).
   - *Example*: `202601_2330_AI1.pdf` for TSMC 2026 Q1.
4. **Logic Flow**:
   - `POST` to the endpoint.
   - Extract the generated PDF link from the response (pattern: `href='(/pdf/.*\.pdf)'`).
   - `GET` the final URL: `https://doc.twse.com.tw` + `/pdf/...`.

```python
# Implementation Example
payload = f"step=9&kind=A&co_id={stock}&filename=202601_{stock}_AI1.pdf"
resp = terminal(f'curl -s -X POST https://doc.twse.com.tw/server-java/t57sb01 -d "{payload}"')["output"]
match = re.search(r"href='(/pdf/.*\.pdf)'", resp)
if match:
    pdf_url = f"https://doc.twse.com.tw{match.group(1)}"
    terminal(f'curl -s {pdf_url} -o {target_file}')
```

## Common Bot Detection
- MarketScreener and some IR sites (e.g., Unimicron's official site) may block automated navigation.
- MOPS is generally more accessible via the browser tool but requires specific interaction patterns (Form -> Query -> Link -> Console Extract).
