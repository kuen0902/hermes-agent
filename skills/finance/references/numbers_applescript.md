# Numbers Automation & Data Updates

## Document Discovery (AppleScript)
Numbers often renames documents internally to the current date even if opened via a symlink. Avoid `document 1`. Search for the target by name prefix:
```applescript
tell application "Numbers"
    set docList to name of every document
    repeat with d in docList
        if d starts with "StockTracking" then
            set targetDoc to document d
            exit repeat
        end if
    end repeat
end tell
```

## Resilience & Pre-flight Checks
- **App Resilience**: If Numbers hangs or returns generic index errors, use `pkill -9 Numbers` followed by `open -a Numbers` and a 5s delay.
- **Pre-flight Check**: Numbers MUST be running for AppleScript `tell` blocks to succeed. If `pgrep Numbers` returns no PID, the gatherer should attempt a `subprocess.run(['open', path])` and wait 5-10s before proceeding.

## Data Extraction & Manipulation
- **Quick Extraction (Bulk)**: For smaller tables (e.g., Portfolio), retrieving all values at once is faster and less prone to indexing errors.
  ```applescript
  tell application "Numbers"
      open "/Users/bookid/Documents/StockTracking_Daily.numbers"
      tell document 1 to tell sheet "Portfolio" to tell table 1
          return value of every cell
      end tell
  end tell
  ```
- **Row Iteration (Precision)**: Use when filtering or updating specific tickers. Search 'cell 1' for ticker -> Update 'cell X' in the same row.
- **Safe Row Deletion (Backward Iteration)**: Always delete from bottom to top (e.g., `repeat with i from rowCount to 2 by -1`) to preserve index integrity.
- **Robust Append Logic**: Use `make new row at end of rows` to avoid calculation errors with `count + 1`.
- **Object Hierarchy Safety**: Always nested `tell document X -> tell sheet Y -> tell table Z`. Avoid `document X of table Y` errors.
- **Value Casting**: Explicitly cast using `as string` or `as real` for reliability in comparative logic.
