# Hermes Context Handover (交接事項)

> **MANDATORY**: 此檔案為跨 Session 專用的最新開發進度與待辦事項交接區。
> 每次啟動對話時，請務必先閱讀此文件以取得最新的系統脈絡。

## 📅 最新更新日期
2026-05-18 (Session: 股票系統底層升級與 Telegram 防護強化)

## ✅ 近期已完成事項 (Completed)

1. **Portfolio 資料庫 SQLite 化**
   - 移除了過去極不穩定的 JSON 讀寫狀態，全面升級為 `portfolio.db`。
   - 重構 `portfolio_tool.py`，現在具備 `current_holdings`, `watchlist`, `pnl_history` 三大核心資料表。
   - 實作了「加碼 (add)」、「減碼/清單 (reduce)」功能，並完美支援計算**「千股單位 (張)」**的已實現損益 (Realized PnL)。

2. **Telegram 權限深度防護**
   - 發現並修復了 Telegram Bot 因為缺少 `HERMES_GOLD_EXPERIENCE_CHAT_ID` 而隱藏進階持股按鈕的致命權限 Bug。
   - 將防護機制檢查整合至 `hermes_diagnostic.swift` (第 7 條檢查規則)，確保未來能自動抓出 `.env` 中的設定遺漏。

3. **觀測清單 (Watchlist) 的細緻化群組**
   - 成功從 `master_stock_registry.json` 自動將追蹤股票與對應的子群組名稱 (例如: 「William哥推薦組」、「高潮不斷群 (Kim哥推薦組)」) 導入 SQLite `watchlist`。
   - 現在 Telegram 的「列出觀測清單」功能具備極致美觀的群組資料夾排版。
   - 同步修正了「查詢個股報價」功能，使其能即時從 `central_stock_data.json` 撈取並印出完整資訊。

4. **Git 環境最佳化**
   - 在 `.gitignore` 中追加了 `node_modules/` 與 `lsp/node_modules/`，解決了 VS Code 內出現 2000+ 個無效追蹤檔案的效能災難。

## 🎯 下階段待辦事項 (Pending / Next Steps)

1. **自動加減碼的 AI 聯動 (Agent Execution)**
   - **目標**：目前的加碼、減碼動作仍依賴使用者手動點擊 Telegram 按鈕。未來需將 Antigravity / Hermes Agent 與此操作綁定。
   - **細節**：當 AI 分析出進場或出場訊號時，應能自動執行 `portfolio_tool.py --add/--reduce`，並連動我們的「持股更新計畫」。
2. **Swift 引擎的進階報警**
   - 探討是否將 `pnl_history` (已實現損益) 透過 Swift 引擎轉發精美的圖表或日報表給 Telegram 頻道。
3. **優化夜盤 / 盤後資料更新排程**
   - 配合 SQLite，進一步強化 cron job 獲取資料並自動刷新 `central_stock_data.json` 的穩定度，防範 Yahoo Finance 的 Rate Limit 封鎖。

## 🧠 給下一位 Hermes 助理的交接箴言
> *「目前的股票模組 (`portfolio_tool.py`) 已經打下極度堅實的 SQLite 基礎，各種輸出排版也都已經調整到最符合 User 習慣的完美格式（包括千分位、🔴綠🟢紅顏色反轉）。接下來的開發請專注於 AI 自動化與策略執行的串接，並隨時使用 `swift ~/.hermes/scripts/hermes_diagnostic.swift` 確認環境健康度。無駄無駄無駄！」*
