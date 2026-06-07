# Skill: Swift-Python JSON Bridge

**Category**: Software Development / Architecture Integration
**Goal**: Safely execute Python data-analysis scripts from Swift orchestrator via strict JSON data transfer.

## 1. When to Use (使用時機)
- **Migration**: 當需要將 Python 的排程邏輯或 Orchestrator 遷移至 Swift 時。
- **Library Dependency**: 當 Swift 需要呼叫依賴 `pandas`, `numpy`, `ta-lib` 等特定資料科學套件的 Python 腳本時。
- **Data Transfer**: 當 Python 子行程與 Swift 父行程之間需要跨語言傳遞結構化資料時。

## 2. Architecture Pattern (架構模式)

### Phase 1: Python Script Execution (`test_output.py`)
**Rule**: The Python script MUST output a strict JSON string to `stdout`. All debug logs MUST be redirected to `stderr`.
*(規則：Python 必須嚴格輸出 JSON 字串至 `stdout`。所有的除錯日誌必須寫入 `stderr`，以免破壞 JSON 解析。)*

```python
import json
import sys

def main():
    # 接收從 Swift 傳遞過來的參數
    args = sys.argv[1:]
    
    # 在這裡執行複雜的資料處理與計算邏輯...
    result = {
        "status": "success",
        "data": {
            "value": 42
        }
    }
    
    # 嚴格將結果轉為 JSON 格式並輸出至 stdout
    print(json.dumps(result))

if __name__ == "__main__":
    main()
```

### Phase 2: Swift Bridge Implementation
**Rule**: Swift MUST use `Process()` with the absolute python path, read `stdout` via `Pipe`, and parse with `JSONDecoder`.
*(規則：Swift 必須使用絕對路徑呼叫 `Process()`，透過資料管線讀取 `stdout`，並使用 `JSONDecoder` 進行強型別解析。)*

```swift
import Foundation

// 定義與 Python JSON 輸出完全吻合的資料結構 (Codable)
struct PythonResponse: Codable {
    let status: String
    let data: ResponseData
}

struct ResponseData: Codable {
    let value: Int
}

func callPython() -> PythonResponse? {
    // 必須使用 ARCHITECTURE.md 中定義的絕對路徑
    let pythonPath = "/Users/bookid/.hermes/.venv/bin/python"
    let scriptPath = "/Users/bookid/.hermes/scripts/test_output.py"
    
    let process = Process()
    process.executableURL = URL(fileURLWithPath: pythonPath)
    process.arguments = [scriptPath, "arg1"]
    
    let pipe = Pipe()
    process.standardOutput = pipe
    // 建議：也可以設定 process.standardError 來單獨捕捉 Python 的錯誤日誌
    
    do {
        try process.run()
        process.waitUntilExit()
        
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        let decoder = JSONDecoder()
        
        // 嘗試將 Python 回傳的 JSON 解碼為原生 Swift Struct
        return try decoder.decode(PythonResponse.self, from: data)
    } catch {
        print("Failed to execute or decode Python output: \\(error)")
        return nil
    }
}
```

## 3. Critical Rules (重要守則)
1. **Absolute Path Required (必須使用絕對路徑)**: Never assume `python3` works. Always use `/Users/bookid/.hermes/.venv/bin/python`. 
   *(嚴禁依賴系統環境變數，永遠使用指定的絕對路徑。)*
2. **Zero `stdout` Pollution (零 stdout 污染)**: If using `print()` for debugging in Python, you MUST redirect to `sys.stderr`. 
   *(Python 程式碼中用來除錯的 `print` 必須導向至標準錯誤輸出，否則 JSON 酬載會因格式錯誤而無法被 Swift 解析。)*
