# Taiwan MOPS (Public Information Observatory) Nuances

## URL Patterns
- **Financial Reports (E-books)**: `https://mops.twse.com.tw/nas/t164sb01/[CODE]/[YEAR][SEASON]-[TYPE].pdf`
  - `TYPE`: C (Consolidated), I (Individual).
  - `SEASON`: 01, 02, 03, 04.
  - `YEAR`: ROC Year + 1911 (e.g., 114 -> 2025).

## Bot Detection (Radware)
- **Symptoms**: Returns `HTTP 200` but content is a < 15KB HTML snippet containing a script redirect or "Radware Bot Manager Block".
- **Workaround Attempts**:
  - `User-Agent`: Must be a full modern browser string.
  - `Referer`: `https://mops.twse.com.tw/mops/web/t57sb01_q5` or `https://mops.twse.com.tw/mops/web/t164sb01`.
  - `Delay`: Excessive requests trigger IP blocks.

## Timing
- **Release Schedule**: Taiwan listed companies (TWSE) typically release Q1 reports by May 15th, Q2 by Aug 14th, Q3 by Nov 14th, and Annual (Q4) by March 31st.
- **Announcement Delay**: The "Major News" (重大訊息) event usually precedes the PDF upload by a few days. If you find the news but the PDF is 404/Small, the file isn't uploaded yet.

## PDF Authenticity & Disguised HTML
- **Case: 2382 Quanta Q1 2026**: Downloaded `.pdf` might actually be a raw HTML file containing table data.
- **Detection**:
  ```bash
  head -c 5 report.pdf
  # If it returns '<!DOC' or '<html', it's HTML.
  ```
- **Parsing**: Do not use PDF readers. Treat as HTML/ASCII text and extract data using string matching or BeautifulSoup.

## Environment Constraints
- **Library Fallback**: If standard CLI tools like `pdftotext` are missing, use Python `PyPDF2` via `execute_code`:
  ```python
  import PyPDF2
  reader = PyPDF2.PdfReader("report.pdf")
  text = reader.pages[0].extract_text()
  ```

## Calendar Update Snippet (Dict-keyed Robust)
The calendar (`~/.hermes/data/earnings_calendar.json`) is typically a **dictionary** where keys are tickers (e.g., `2330.TW`).
```python
import json, os
path = os.path.expanduser('~/.hermes/data/earnings_calendar.json')
with open(path, 'r+') as f:
    calendar = json.load(f)
    # Update logic (ensure it's a dict)
    if not isinstance(calendar, dict):
        # Handle migration if needed
        pass
    if ticker in calendar:
        calendar[ticker]['downloaded_q1'] = True
    f.seek(0)
    json.dump(calendar, f, indent=4, ensure_ascii=False)
    f.truncate()
```
