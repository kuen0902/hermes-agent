# 󰄬 Hermes 系統健康檢查表 (Health Check SOP)

為確保 Hermes 代理系統在高強度運行下的穩定性，請定期（建議每週）執行以下健康檢查項目：

## 1. 󰅨 目錄與檔案結構檢查
- [ ] 確認 `~/.hermes/` 根目錄下沒有新增未分類的腳本 (`*.py`, `*.sh`)。
- [ ] 確認 `skills/` 下的模組沒有出現雙層嵌套（例如 `skills/xxx/xxx`）。
- [ ] 確認 `scripts/` 是系統唯一的執行邏輯中心。

## 2. 󰛨 Git 倉庫純淨度
- [ ] 執行 `git status`，確認沒有大容量二進位檔案（如 `*.db`, `*.db-wal`）被意外加入追蹤。
- [ ] 確認 `.gitignore` 的排除規則（如 `__pycache__`, `logs/`）正常運作。

## 3. 󰟥 日誌與錯誤排查 (Logs & Errors)
- [ ] 檢查 `logs/errors.log`：確認是否有高頻發生的 API 速率限制錯誤 (HTTP 429) 或未捕捉的異常。
- [ ] 檢查 `logs/gateway.log`：確認代理閘道 (Gateway) 在重啟或關閉時，是否能順利 `exit`，而非依賴 `SIGKILL` 暴力終止。

## 4. 󰚗 排程與資料同步
- [ ] 檢查 `cron/output/`：確認最重要的排程（如 `TAIEX Master Monitor`）的最新輸出日誌是否有資料異常或中斷。
- [ ] 檢查 `data/`：確認 `central_stock_data.json` 等快取檔案的修改時間 (Modified Time) 都有正常更新。

---
> [!TIP]
> **維護指令提示**：如發現系統卡死或環境異常，請至 `~/.hermes/maintenance/` 執行對應的 `cleanup_hermes.py` 或 `kill_hermes.sh`。
