# References/Python Wrapper Execution for Complex Shell Logic

## 💡 Pattern: Overcoming AppleScript/Shell Instability

當 AppleScript 或 Bash 指令內部邏輯極為複雜 (例如：多個 if 判斷、大數據處理、或跨多個 API 呼叫)，直接在 `terminal` 或 `osascript` 中執行往往會因為 **環境語法限制** 或 **效能超載** 而失敗。

**解決方案：** 使用最穩定的環繞層 (Wrapper Layer) —— Python。

**流程步驟：**
1.  將複雜的 shell/script 邏輯，封裝成一個獨立的支援腳本 (`.py` 或 `.sh`)。
2.  使用 Python 的 `subprocess` 模組來同步執行這個腳本。
3.  Python 提供了更穩定的腳本運行環境，能夠更好地處理輸出和錯誤捕獲。
4.  這能讓 Agent 在處理複雜、多步驟的跨系統任務時，不會因為指令字串過長而中斷。

**示例：** 讀取郵件清單時，我們將 AppleScript 封裝進了 `mail_reader.py` 來確保穩定性和可控性。