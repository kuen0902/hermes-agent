# Robust AppleScript Patterns for Numbers.app

These patterns are proven to be more reliable than built-in range selectors which often fail with error `-10000`.

## 1. Robust Row-by-Row Data Extraction
Avoid `get value of cells in range`. Use a loop to build a data list.

```applescript
tell application "Numbers"
    tell document 1 to tell sheet "MySheet" to tell table 1
        set allData to {}
        set rowCount to row count
        repeat with i from 1 to rowCount
            set aRow to value of every cell of row i
            copy aRow to end of allData
        end repeat
        return allData
    end tell
end tell
```

## 2. Safe Row Deletion (Backward Iteration)
Always delete from bottom to top to preserve index integrity.

```applescript
tell application "Numbers"
    tell document 1 to tell sheet "Portfolio" to tell table 1
        set rowCount to row count
        repeat with i from rowCount to 2 by -1 -- Start from bottom, skip header (1)
            set cellValue to value of cell 2 of row i -- e.g. check "Name" column
            if (cellValue as string) contains "Outdated" then
                delete row i
            end if
        end repeat
    end tell
end tell
```

## 3. Targeted Cell Update via Symbol Search
Searching for a primary key (e.g., Stock Code) then updating adjacent cells.

```applescript
tell application "Numbers"
    tell document 1 to tell sheet "Portfolio" to tell table 1
        set rowCount to row count
        repeat with i from 2 to rowCount
            set sym to value of cell 1 of row i as string -- Column 1 is Code
            if sym is "2330" then
                set value of cell 4 of row i to 2275.0 -- Column 4 is Price
            end if
        end repeat
    end tell
end tell
```
