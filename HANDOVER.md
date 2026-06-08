# Hermes Context Handover (交接事項)

> **MANDATORY**: 此檔案為跨 Session 專用的最新開發進度與待辦事項交接區。
> 每次啟動對話時，請務必先閱讀此文件以取得最新的系統脈絡。

## 📅 最新更新日期
2026-06-08 (Fixed Cron DB corruption and 8am Job 429)
8|
9|## ✅ 近期已完成事項 (Completed)
10|
11|1. **Cron 數據庫修復與 8am 任務復位**
12|   - 修復了 `~/.hermes/cron/jobs.json` 中的 `\u9edge` 非法轉義字符，恢復 cron 工具調用能力。
13|   - 將 8am 「Daily Architect Worklog」任務從受限的 `qwen3.6:35b` 切換回 `gemini-3-flash-preview` 以避免 HTTP 429 報錯。
14|   - 盤點並補發了 2026-06-08 的架構師工作日誌。
15|
16|2. **Persona 與推播路由精準定義 (Persona Routing)**
   - 確立 Star Platinum (白金之星, 8737129549) 為所有股票通知 (包含個人、群組與 William 泡泡) 的唯一發送者。
   - 確立 GER (黃金體驗-鎮魂曲) 為指令與對話控制中心，不再負責日常報價推播。
   - 更新了 `MEMORY.md` 與 `USER.md` 確保後續 AI 理解此分流機制。

2. **Swift 執行環境優化與開盤回報放寬**
   - 變更 `run_hermes_monitor_*.sh` 與 `run_hermes_sync.sh`，改為直接透過 `/usr/bin/swift` 執行 `.swift` 原始碼，避免因編譯檔 (Binaries) 遺失導致的執行錯誤。
   - 放寬 `hermes_monitor.swift` 中開盤報警的時間判定，將原先嚴格的 09:00~09:10 改為 `09:00 ~ 13:59` 皆可觸發。

3. **系統診斷與排程更新 (Diagnostics & Cron)**
   - 大幅簡化了 `hermes_diagnostic.swift`，改為輸出精簡的系統狀態檢查結果，去除過於繁雜的動態檢查代碼。
   - 同步更新了 cron job 的相關設定與狀態時間戳 (`jobs.json`)。

4. **防護盾建立 (API Rate-Limit Resilience)**
   - 解決了 `jobs.json` 中 Ollama HTTP 429 錯誤。將最頻繁的 13:30 休市判斷改由純 Python 腳本 (`run_market_close_report.py`) 獨立完成，實現 LLM 脫鉤。
   - 在 `taiex_central_data_sync.py` 內建了 Exponential Backoff 重試與 User-Agent 隨機輪替機制，成功防範 Yahoo Finance 封鎖。

5. **自動加減碼的 AI 聯動 (Agent Execution)**
   - 打通了 ML 預測與 SQLite 投資組合的最後一哩路。
   - `intraday_ml_pipeline.py` 現在能根據勝率生成 `trade_signals.json`。
   - 全新建立 `trade_execution_orchestrator.py` 會自動攔截訊號執行 `portfolio_tool.py --add/reduce`，並透過 Telegram 即時回報。

6. **Swift 引擎進階報警 (PnL Reporting)**
   - 實現了盤後已實現損益的自動通知。
   - 建立 `calculate_pnl_summary.py` 與 `send_pnl_report.swift` 聯合管線，將每日交易明細與歷史總損益整理成精美 Markdown 發送至您的 Telegram。

7. **腳本大掃除與架構重整 (Code Refactoring)**
   - 解決了 `scripts/` 目錄下高達 84 個檔案的混亂狀態。
   - 撰寫了 `refactor_phase4.py` 自動將 Swift 執行檔移入 `bin/`、ML 相關移入 `ml/`、抓價腳本移入 `fetchers/`。
   - 自動連動更新 `jobs.json` 排程中的絕對路徑，確保系統無縫接軌。

8. **通訊架構絕對隔離 (Information Segregation)**
   - 確立了三方分流協議：個人核心持股由 GER 發送、群組監控由白金之星 (Star Platinum) 發送、William 清單由專屬機器人發送。
   - 修正了 Cron Job 的 `deliver` 模式，將派送權力交還給腳本原生驅動，解決 Chat not found 報錯。

9. **核心 Token 復位與雙引擎重編譯**
   - 清除受污染的 Token，將真實的白金之星 Token (`8737...`) 物理注入 `intraday_risk_monitor.py` (Python) 與 `hermes_monitor.swift` (Swift)。
   - 重新編譯了 Swift 引擎，確保底層通訊網路 100% 暢通。

10. **股名映射修復與 Markdown 防呆**
   - 於 `master_stock_registry.json` 與 SQLite 資料庫中補齊了 2409 (友達)、6770 (力積電)、5443 (均豪) 的名稱。
   - 針對 `intraday_data_log.csv` 執行了歷史紀錄清洗，將代碼轉為中文。
   - 在 `intraday_ml_pipeline.py` 中加入了 Markdown 特殊字元 (如 `*`, `_`) 的轉義處理，徹底解決發送含特殊符號股名 (如國巨*) 時導致的 Telegram 400 Bad Request 錯誤。

11. **Portfolio 資料庫 SQLite 化**
   - 移除了過去極不穩定的 JSON 讀寫狀態，全面升級為 `portfolio.db`。
   - 重構 `portfolio_tool.py`，現在具備 `current_holdings`, `watchlist`, `pnl_history` 三大核心資料表。
   - 實作了「加碼 (add)」、「減碼/清單 (reduce)」功能，並完美支援計算**「千股單位 (張)」**的已實現損益 (Realized PnL)。

12. **Telegram 權限深度防護**
   - 發現並修復了 Telegram Bot 因為缺少 `HERMES_GOLD_EXPERIENCE_CHAT_ID` 而隱藏進階持股按鈕的致命權限 Bug。
   - 將防護機制檢查整合至 `hermes_diagnostic.swift` (第 7 條檢查規則)，確保未來能自動抓出 `.env` 中的設定遺漏。

13. **觀測清單 (Watchlist) 的細緻化群組**
   - 成功從 `master_stock_registry.json` 自動將追蹤股票與對應的子群組名稱 (例如: 「William哥推薦組」、「高潮不斷群 (Kim哥推薦組)」) 導入 SQLite `watchlist`。
   - 現在 Telegram 的「列出觀測清單」功能具備極致美觀的群組資料夾排版。
   - 同步修正了「查詢個股報價」功能，使其能即時從 `central_stock_data.json` 撈取並印出完整資訊。

14. **機器學習 (ML) 分析管線修復與強固**
   - 修復了 `pandas-ta-classic` 因 Yahoo Finance API 異常回傳字串而導致的 `TypeError`。
   - 在 `confluence_eod_analysis.py`, `portfolio_ml_analysis.py` 等核心分析腳本中實作了強制的型別轉換 (`pd.to_numeric`) 與空值處理 (`dropna`)，大幅提升了 ML 推理引擎在面對髒資料時的穩定性。

15. **Git 環境最佳化**
   - 在 `.gitignore` 中追加了 `node_modules/` 與 `lsp/node_modules/`，解決了 VS Code 內出現 2000+ 個無效追蹤檔案的效能災難。

16. **盤中與夜盤監測介面優化與 API 強固 (Session 2026-05-20/21)**
   - 將 `hermes_monitor.swift` 的盤中警報升級為「緊湊單行風格」，並無縫整合 ML 腳本 (`intraday_ml_pipeline.py --silent`)，直接將看多看空機率附加在警報後方，大幅提升閱讀體驗。
   - 修正 `tw_night_session_hourly.py` 在觸發備援機制時重複輸出 `✅ 狀態：Healthy` 的排版 Bug。
   - 強化 `tw_night_monitor_adri.py` 的夜盤階梯式門檻邏輯，當股票未達 ±3% 門檻時不再輸出錯誤的 `[SILENT]`，而是優雅地在報表下方顯示「未達推播門檻」的清單與當下漲幅。
    - **關鍵修復**：為解決夜盤 ADR 監測頻繁遭到 `yfinance` Rate Limit 封鎖導致的 0.0% 漲幅誤判，已全面改寫 `tw_night_monitor_adri.py` 直連 Yahoo Finance Chart API (`query1.finance.yahoo.com/v8/finance/chart`)，完美取回正確的 `regularMarketPrice` 與 `previousClose`。

17. **手動交易 PnL 損益圖表生成與 Swift Telegram 圖片推播 (Session 2026-05-23)**
   - 依據 100% 手動交易原則，建立 `scripts/ml/generate_pnl_chart.py` 繪圖引擎，從 `portfolio.db` 讀取手動平倉歷史，利用 `matplotlib` 產生高解析度、漸層填滿、平滑的深色主題（Emerald Green 前景色）累計已實現損益（Cumulative Realized PnL）曲線圖。
   - 重構 `scripts/send_pnl_report.swift` 通知器，使用 Swift 原生 `multipart/form-data` 對接 Telegram `sendPhoto` 接口，實現「損益圖表圖片 + 手動交易明細文字 Caption」的一體化高階推播，並內建了極具韌性的純文字 Fallback 發送機制。
   - 於 `scripts/run_daily_pnl_report.sh` 整合此視覺化管線，透過 E2E 實測與 24 項系統健康度診斷全數亮綠燈驗收。

18. **夜盤報價橋接與監測報告自動化 (Session 2026-05-25)**
   - 建立了 `market_prices_bridge.json` 資料橋接機制，由 Agent 手動抓取 NQ, TSM, NVDA, SYNA, FITXP 即時報價並寫入。
   - 成功執行 `run_night_report.py` 利用此橋接資料生成夜盤監測報告，並發送至 Telegram。
   - 解決了夜盤期間 ADR 資料抓取不穩定導致的分析落差問題。

19. **商品與群組更新標準作業程序建立與分裂症修復 (Session 2026-05-27)**
   - 建立了 `stock-monitoring-ops` 技能，規範新增/修改自選個股分群時的多語言一致性同步與重編譯流程。
   - 修正了 `hermes_monitor.swift` 漏設「AI推的組（6806, 1591, 3349）」的問題，並使用自訂模組快取重導成功在 IDE 沙盒環境內將 Swift 引擎重新編譯為全新二進位檔，徹底修復 09:00 開盤即時戰報分群缺漏問題。

20. **新增「高潮不斷群 (HTNM森組)」個股分群與 00881 同步 (Session 2026-05-28)**
   - 於 `master_stock_registry.json` 中建立了全新分群「高潮不斷群 (HTNM森組)」並加入 00881。
   - 同步修正了 `hermes_monitor.swift` 中的 `getTargetStocks` 邏輯，確保開盤戰報與盤中監報能正確分組顯示。
   - 重新編譯了 Swift 引擎二進位檔。

## 🎯 下階段待辦事項 (Pending / Next Steps)

1. **持續觀察手動平倉交易曲線與視覺化排版調整**
   - 隨著手動交易資料的累積，可以視需求微調 Matplotlib 的繪圖參數（如網格密度、色彩對比），以最佳化各終端裝置上的圖表顯示美感。

## 🧠 給下一位 Hermes 助理的交接箴言
> *「目前的股票模組 (`portfolio_tool.py`) 已經打下極度堅實的 SQLite 基礎，各種輸出排版也都已經調整到最符合 User 習慣的完美格式（包括千分位、🔴綠🟢紅顏色反轉）。接下來的開發請專注於手動交易統計數據的視覺化美感優化，並隨時使用 `swift ~/.hermes/scripts/hermes_diagnostic.swift` 確認環境健康度。無駄無駄無駄！」*
