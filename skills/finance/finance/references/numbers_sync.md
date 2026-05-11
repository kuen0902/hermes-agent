# Numbers Spreadsheet Sync Logic (AppleScript)

To allow users to manage stock lists via a Numbers file without modifying code. The current implementation uses a tab-separated output string which is more reliable than AppleScript list serialization.

### 1. Robust Fetch Script
Target File: `~/Documents/StockTracking_Daily.numbers`

```python
def get_personal_tickers():
    """Fetches Ticker, Name, Qty, and Avg Cost from Numbers "Portfolio" sheet."""
    portfolio = {}
    script = """
    set output to ""
    tell application "Numbers"
        try
            set docName to "StockTracking_Daily.numbers"
            tell document docName to tell sheet "Portfolio" to tell table 1
                set rowCount to row count
                repeat with i from 2 to rowCount
                    set code to value of cell 1 of row i
                    if code is not missing value and code is not "" then
                        set nameVal to value of cell 2 of row i
                        set qtyVal to value of cell 3 of row i
                        set avgVal to value of cell 5 of row i
                        set output to output & code & tab & nameVal & tab & qtyVal & tab & avgVal & linefeed
                    end if
                end repeat
            end tell
        on error
            return ""
        end try
    end tell
    return output
    """
    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split('\t')
                if len(parts) >= 4:
                    c = parts[0].strip()
                    # Normalize code (handle AppleScript float conversion like "2330.0")
                    if "." in c and c.split(".")[-1] == "0": c = c.split(".")[0]
                    portfolio[c] = {
                        "name": parts[1].strip(),
                        "qty": float(parts[2]) if parts[2] != "missing value" and parts[2].strip() else 0,
                        "avg": float(parts[3]) if parts[3] != "missing value" and parts[3].strip() else 0
                    }
    except Exception as e:
        print(f"Numbers Fetch Error: {e}")
    return portfolio
```

### 2. Key Considerations
1. **Tab-Separated Output**: Prevents issues with commas in stock names and makes parsing trivial.
2. **Code Normalization**: AppleScript occasionally treats numeric strings (like `2330`) as floats (`2330.0`). Always strip trailing `.0` for stock code consistency.
3. **Sheet/Table Naming**: The document MUST be open for `tell document "Name"` to work reliably. If Numbers is closed, the script might fail or hang.
4. **Row Starts**: Portfolio tables usually have headers. Start the loop from row 2.
