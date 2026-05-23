# Platform Specifics: Taiwan MOPS (公開資訊觀測站)

## Navigation
Use MOPS (mops.twse.com.tw) -> 財務報告書 -> 單一公司.

## Date Formatting
MOPS queries strictly use Minguo (ROC) Years.
Formula: `Year - 1911` (e.g., 2026 = 115).

## Bot Detection & Fake PDFs
Watch for 13-15KB files. Some companies (e.g., 2382 Quanta) upload HTML files disguised with a `.pdf` extension. 
- **Verification**: Check file type via `file <path>` or check if content starts with `<!DOCTYPE html>`.
- **Extraction Fallback**: If `pdftotext` is missing, use Python's `PyPDF2` or `pdfplumber` via `execute_code`.
- **HTML-PDF Trap**: Don't count on `read_file` or `pdftext` alone. If a file fails to parse as PDF, check if it is raw HTML/text first.

## Secondary Source Fallback (The CDN Path)
When MOPS returns 403 or "查無資料" during board meeting week:
- **Search**: Query `"[Ticker] [Name] 2026 Q1 presentation pdf"` or `"[Ticker] [Name] investor conference"`.
- **Authoritative Domains**: Look for `webapi3.adata.com`, `investor.tsmc.com`, `mediatek.com/investor-relations`. 
- **Advantage**: Slide decks (Presentations) are often uploaded to company CDNs immediately after the conference call, hours or days before the massive 200-page auditor report appears on MOPS.
- **EPS Verification**: If no PDF is found, use the search snippet or PTT Stock board (`[情報] 2382 Q1財報`) to verify the EPS for immediate calendar updates.

## Timing & Deadlines
- Financial reports are legally approved during Board Meetings. Public release on MOPS often lags the meeting by 0-24 hours. If an announcement is made on Day X, check MOPS on Evening X or Morning X+1.
- **TAIEX Reporting Deadlines (Calendar Year)**: Q1 (May 15), Q2/H1 (Aug 14), Q3 (Nov 14), Q4/Annual (Mar 31 following year).
- **ETF Distinction**: When users ask for "earnings" for TAIEX tickers starting with `00` (e.g., 0050), they are ETFs. ETFs report dividends and NAV, not EPS/Earnings calls.
