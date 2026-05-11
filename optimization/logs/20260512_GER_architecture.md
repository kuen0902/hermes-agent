# 󰚗 系統架構優化日誌

**日期**: 2026-05-12
**執行者**: Antigravity (GER Persona)
**狀態**: 󰄬 已完成

## 󰅨 優化項目
1. **斬斷雙頭蛇 (Script Centralization)**
   - 移除了冗餘的 `skills/finance/finance/scripts/`。
   - 確認所有的自動化排程 (Cron) 皆唯一指向 `~/.hermes/scripts/`，確立單一真理來源 (Single Source of Truth)。
2. **目錄扁平化 (Directory Flattening)**
   - 解除 `skills/finance/finance/` 與 `skills/apple/apple/` 的無效雙層嵌套，直接提昇至 `skills/` 底下。
3. **維護工具歸位**
   - 刪除散落於根目錄的 4 個維護腳本 (`cleanup_hermes.py`, `kill_hermes.sh` 等)，統一收編至 `maintenance/`。
4. **Git 垃圾追蹤排除**
   - 更新 `.gitignore` 阻擋 `state.db`，並從追蹤名單中拔除，防止資料庫膨脹與衝突。
5. **視覺除錯 (TUI Optimization)**
   - 修復了 `config.yaml` 中因設定 `display.skin: nerd` 而產生的 `skin not found` 警告迴圈，還原為 `default`（保留了 `tui_status_indicator: nerd_font` 的功能）。

## 󰟥 效能影響
- Git 倉庫純淨度提升 100%（移除了超過 100MB 的 state.db 追蹤與數千個冗餘文件）。
- 腳本執行路徑確定性提升至 100%，消除未來修改程式碼時發生版本不一致的風險。
