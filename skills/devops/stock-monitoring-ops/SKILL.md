---
name: stock-monitoring-ops
description: "Standard Operating Procedure (SOP) for adding, removing, and updating monitored/held stocks and groups in the Hermes multi-language pipeline."
version: 1.0.0
author: "Antigravity Specialist"
license: MIT
metadata:
  hermes:
    tags: [stock, operations, registry, sync, swift, monitor]
---

# 📋 Hermes 商品與群組更新標準作業程序 (SOP)

本技能定義了在 Hermes 系統中「新增/刪除個股」或「調整個股分群（如 Kim哥組、AI推的組等）」時的標準維護流程。
每次有商品異動時，**必須**遵循以下 5 大步驟進行同步，以確保系統中「資料庫映射」、「行情同步」、「即時監報」及「編譯二進位執行檔」達成 100% 一致，杜絕戰報遺漏或設定分裂。

---

## 📅 商品變更 5 大同步步驟

### 1. 修改註冊表 (`master_stock_registry.json`)
*   **路徑**：`~/.hermes/data/master_stock_registry.json`
*   **操作**：
    *   **新增/修改分群**：在 `"group_categories"` 字典內，將代碼（字串格式）填入對應的群組陣列中。
    *   **移除個股**：直接自群組陣列中刪除該四碼代號。
    *   **增補中文名**：在 `"official_names"` 字典中補齊或修改代碼與「官方中文名稱」的對應（避免報價與 ML 預測日誌中出現 `Unknown`）。

### 2. 同步行情引擎設定 (`taiex_central_data_sync.py`)
*   **路徑**：`~/.hermes/scripts/taiex_central_data_sync.py`
*   **操作**：
    *   在 `sync()` 函數中的 `group_defaults`（或 `william_defaults`）字典內，**必須**補上或刪除該個股代號與中文名的對應。
    *   *重要性*：此字典是盤中抓取 TWSE/OTC 即時行情並同步寫入 CSV 快取資料庫的基礎。若此處遺漏，該股票將完全無法同步行情！

### 3. 更新 Swift 盤中監報清單 (`hermes_monitor.swift`)
*   **路徑**：`~/.hermes/scripts/hermes_monitor.swift`
*   **操作**：
    *   在 `getTargetStocks(profileName:String, ...)` 函數中，找到對應的 Profile 分支（如 `"group"` 或 `"william"`），增補或移除對應的群組個股陣列。

### 4. 重新編譯 Swift 執行二進位檔 (最核心 ⚠️)
*   **操作**：
    *   因為系統排程與背景監測器（如 `run_group_1350.sh`）執行的是**已編譯的二進位執行檔**而非 `.swift` 原始碼。若修改了 `.swift` 但未重新編譯，系統仍會繼續執行舊的邏輯！
*   **在 IDE 沙盒中重編譯的特殊指令**（因沙盒預設限制寫入系統 `/var/folders/` 的模組快取）：
    ```bash
    swiftc -O hermes_orchestrator.swift -o hermes_orchestrator -module-cache-path /Users/bookid/.hermes/cache/module
    swiftc -O hermes_sync.swift -o hermes_sync -module-cache-path /Users/bookid/.hermes/cache/module
    swiftc -O hermes_monitor.swift -o hermes_monitor -module-cache-path /Users/bookid/.hermes/cache/module
    ```

### 5. 一致性診斷驗證
*   **指令**：
    `/Users/bookid/.hermes/.venv/bin/python /Users/bookid/.hermes/scripts/review_jobs.py`
*   **確認指標**：
    *   系統內無任何 `ConfigConsistency: ERROR` 警告。
    *   診斷輸出中 `Watchlist Configuration Consistency: OK`。
