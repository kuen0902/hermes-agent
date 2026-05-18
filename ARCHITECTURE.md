# ARCHITECTURE.md (Hermes Core Architecture & Memory Bridge)

This document is the **Single Source of Truth** for Hermes system architecture. 
**MANDATORY**: Hermes must consult this document before writing scripts, evaluating architecture, or diagnosing issues.

## 1. System Environment (系統環境)

- **Python Runtime Path**: `/Users/bookid/.hermes/.venv/bin/python`
  - *Detail*: 所有 Python 腳本**必須**使用此絕對路徑的虛擬環境執行。嚴禁使用系統原生的 `python3` 或舊版工作區路徑，以避免環境相依性錯誤。

## 2. Core Capabilities & Design Patterns (核心能力與設計模式)

### Pattern 1: Tri-Language Data Pipeline (三語言協同架構)
**MANDATORY RULE (骨架紀律):**
Hermes 的底層運作必須嚴格遵守以下語言的職責分離，不得混用或越權：
1. **Swift**: 負責「高效能系統調度 (Orchestration)」與「發送 Telegram 即時通知 (Notification)」。(例如：`hermes_orchestrator.swift`, `hermes_monitor.swift`)
2. **AppleScript**: 專職負責「精準取資料 (Data Extraction)」，特別是針對 Numbers 試算表等需要 GUI 引擎解析公式的閉源格式。
3. **Python**: 負責「複雜的資料運算 (Complex Calculations, TA-Lib, ML)」、「歷史回測」與「呼叫外部 API 抓取即時/歷史股價 (Data Fetching)」。

### Pattern 2: Swift-Python JSON Bridge
Hermes is migrating to a high-performance Swift monitoring engine. To interact with legacy Python scripts (e.g., pandas/TA-Lib analysis), we strictly use the Swift-Python JSON Bridge.

**Key Principles (核心原則):**
1. **Swift Orchestrates (Swift 負責協調)**: Swift acts as the central orchestrator using `Process()`.
2. **Python Executes (Python 負責執行)**: Python acts as a sub-process, takes arguments via `sys.argv`, and outputs strictly formatted JSON to `stdout`.
3. **Strict Decoding (嚴謹解碼)**: Swift uses `JSONDecoder` to parse the `stdout` string into strongly-typed `Codable` native structs.

*(註：詳細的程式碼範例與實作細節，請查閱 `skills/software-development/swift_python_bridge.md`)*

## 3. Communication Guidelines (開發與溝通規範)

- **Enforce Defined Paths**: 撰寫或修改程式碼時，必須強制使用本文件中定義的環境路徑。
- **No Unrecorded Dependencies**: 嚴禁引入未在此記錄的外部相依套件或架構。
- **Trust ARCHITECTURE.md**: 所有新架構的變更都會由系統工程師 (Antigravity) 記錄於此。當你的內部假設與此文件衝突時，永遠以本文件的內容為準。
