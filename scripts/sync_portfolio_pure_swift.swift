import Foundation

let docPath = "/Users/bookid/Documents/StockTracking_2026-05-18.numbers"
let jsonPath = NSHomeDirectory() + "/.hermes/data/central_stock_data.json"

let appleScriptCode = """
tell application "Numbers"
    set theDoc to open (POSIX file "\(docPath)")
    set theSheet to sheet "Portfolio" of theDoc
    set theTable to table 1 of theSheet
    
    set rowCount to count rows of theTable
    set colCount to count columns of theTable
    
    set outText to ""
    repeat with r from 2 to rowCount
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

guard let script = NSAppleScript(source: appleScriptCode) else {
    print("Failed to compile AppleScript.")
    exit(1)
}

var errorInfo: NSDictionary? = nil
let result = script.executeAndReturnError(&errorInfo)

if let error = errorInfo {
    print("AppleScript Error: \(error)")
    exit(1)
}

guard let stringResult = result.stringValue else {
    print("No string result returned.")
    exit(1)
}

// --- 解析資料 ---
var personalData: [String: Any] = [:]

let lines = stringResult.components(separatedBy: "\n")
for line in lines {
    let parts = line.components(separatedBy: "|~|")
    if parts.count >= 4 {
        var code = parts[0].trimmingCharacters(in: .whitespaces)
        // 處理試算表常見的文字前綴單引號
        if code.hasPrefix("'") {
            code.removeFirst()
        }
        
        if code.lowercased() == "id" || code.isEmpty { continue }
        
        let name = parts[1].trimmingCharacters(in: .whitespaces)
        let qty = Double(parts[2].trimmingCharacters(in: .whitespaces)) ?? 0.0
        let price = Double(parts[3].trimmingCharacters(in: .whitespaces)) ?? 0.0
        
        if qty > 0 {
            personalData[code] = [
                "name": name,
                "qty": qty,
                "avg": price
            ]
        }
    }
}

print("✅ 已從 Numbers 成功提取 \(personalData.count) 檔持股資料。")

// --- 直接讀寫 Hermes JSON ---
let url = URL(fileURLWithPath: jsonPath)
var jsonData = [String: Any]()

do {
    let data = try Data(contentsOf: url)
    if let dict = try JSONSerialization.jsonObject(with: data, options: .mutableContainers) as? [String: Any] {
        jsonData = dict
    }
} catch {
    print("ℹ️ 找不到原有的 central_stock_data.json，將建立新檔。")
}

jsonData["personal_data"] = personalData
if jsonData["stock_private_flag"] == nil {
    jsonData["stock_private_flag"] = true
}

do {
    let newData = try JSONSerialization.data(withJSONObject: jsonData, options: [.prettyPrinted, .withoutEscapingSlashes])
    try newData.write(to: url)
    print("✅ 已成功將最新的 Portfolio 直接寫入 \(jsonPath)")
} catch {
    print("❌ 寫入 JSON 失敗: \(error)")
}
