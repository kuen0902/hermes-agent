# Taiwan Stock Portfolio Lifecycle Management (Numbers + Python)

This reference documents the logic for common portfolio operations (Add, Sell, Update) using AppleScript and Python.

## Core Operations

### 1. Sell-All (Delete Row)
When the user says "Sell [Stock]", find the row by ID and delete it.
**AppleScript Logic:** (Iterate backwards to safely delete)
```applescript
set rCount to row count
repeat with i from rCount to 2 by -1
    set v to value of cell 1 of row i
    if (v as string) starts with "2313" then
        delete row i
        exit repeat
    end if
end repeat
```

### 2. Sell-Partial (Update Quantity)
Decrease the value in the "Qty" column.
**AppleScript Logic:**
```applescript
repeat with i from 2 to rCount
    set v to value of cell 1 of row i
    if (v as string) starts with "2049" then
        set currentQty to value of cell 3 of row i
        if currentQty > 1 then
            set value of cell 3 of row i to (currentQty - 1)
        else
            delete row i
        end if
        exit repeat
    end if
end repeat
```

### 3. Add-New (Append Row)
Add a new stock with ID, Name, Qty, and Cost.
**AppleScript Logic:**
```applescript
set newRow to make new row at end
-- Force ID as string to prevent scientific notation/truncation
set value of cell 1 of newRow to "'2344" 
set value of cell 2 of newRow to "華邦電"
set value of cell 3 of newRow to 1.0
set value of cell 5 of newRow to 114.0
```

## Python Integration Pitfalls
1. **The Quote Prefix**: If an ID was written as `'2344`, reading it back often yields `" '2344"`.
   ```python
   code = parts[0].strip().strip("'") # Removes both whitespace and the AppleScript text marker
   ```
2. **Float Normalization**: Numbers might return `2330.0` for a stock code.
   ```python
   if "." in code and code.split(".")[-1] == "0": 
       code = code.split(".")[0]
   ```
