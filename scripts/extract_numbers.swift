import Foundation

let docPath = "/Users/bookid/Documents/StockTracking_2026-05-18.numbers"

let appleScriptCode = """
tell application "Numbers"
    -- Try to open the document, Numbers will handle it if it's already open
    set theDoc to open (POSIX file "\(docPath)")
    
    set theSheet to sheet "Portfolio" of theDoc
    set theTable to table 1 of theSheet
    
    set rowCount to count rows of theTable
    set colCount to count columns of theTable
    
    set outText to ""
    repeat with r from 1 to rowCount
        set rowText to ""
        repeat with c from 1 to colCount
            set val to value of cell c of row r of theTable
            if val is missing value then
                set strVal to ""
            else
                set strVal to val as string
            end if
            
            if c > 1 then
                set rowText to rowText & "|~|"
            end if
            set rowText to rowText & strVal
        end repeat
        set outText to outText & rowText & "\\n"
    end repeat
    
    return outText
end tell
"""

if let script = NSAppleScript(source: appleScriptCode) {
    var errorInfo: NSDictionary? = nil
    let result = script.executeAndReturnError(&errorInfo)
    
    if let error = errorInfo {
        print("AppleScript Error:")
        print(error)
        exit(1)
    }
    
    if let stringResult = result.stringValue {
        print(stringResult)
    } else {
        print("No string result returned.")
    }
} else {
    print("Failed to compile AppleScript.")
    exit(1)
}
