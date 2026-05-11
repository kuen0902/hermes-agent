# Financial Data Quality Control (QC)

This reference defines the "System Architect" standards for financial data reliability.

## 1. Automated Health Checks
Every downloaded CSV or PDF must pass these gates before being marked as "Processed":
- **Size Check**: `> 1024 bytes`. (Prevents "File Not Found" HTML pages saved as .csv).
- **Schema Check**: Mandatory columns (Date, Close, Volume) must be present.
- **NaN Threshold**: Total null values in price columns must be `< 5%` of the total row count.
- **Symbol Match**: Ensure the data inside the file matches the filename/requested ticker.

## 2. The 3-Failure Escalation Protocol
Triggered when an automated job (Cron or Script) fails 3 times on the same target.

### Step 1: Broad Search
Perform a web search for `[Ticker] 財報 停止` or `[Ticker] Stock Delisted`.
Identify if the failure is due to:
- **Ticker Change**: (e.g., 2330.TW -> 2330.TWO).
- **Delisting**: Company no longer traded.
- **API Block**: Yahoo Finance/MOPS 429 errors.

### Step 2: Formatted Reporting
Send a report to `@kuenmingBot`:
> **[故障類型]**: (e.g., 下載失敗 - 檔案毀損)
> **[調查診斷]**: (e.g., 該公司 2026Q2 財報因更正延遲上傳)
> **[替代方案]**: (e.g., 已設定明日凌晨 05:00 重試或改從公開資訊觀測站抓取)

## 3. Historical Depth Verification
For "Deep History" projects (e.g., 2010 start):
- Check the first row date.
- If data starts *later* than requested (and it's not a new IPO), log a "Data Gap" warning and search for alternative sources (Yahoo vs. Investing.com).
