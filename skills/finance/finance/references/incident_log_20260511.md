# Incident Report: Telegram Gateway Identity Misalignment (2026-05-11)

## 1. 故障回顧 (Root Cause)
- **錯誤現象**: 使用者反應「黃金體驗-鎮魂曲」在 Telegram 無回覆，但 Gateway 顯示 `connected`。
- **根本原因**: 
    1. **Token 錯位**: `.env` 中的 `TELEGRAM_BOT_TOKEN` 被設定為 `@taiwangupiaoBot` (白金之星)，導致主體 Bot 未被正確初始化。
    2. **頻道權限鎖死**: `config.yaml` 中的 `allowed_channels` 被限制在單一群組 ID，導致 Bot 自動過濾所有來自私訊 (DM) 的更新。
    3. **殭屍程序**: 存在多個 `hermes-gateway` 殘留程序競爭 API 存取權。

## 2. 診斷指令集 (Diagnostic Toolbox)
- **檢查 Webhook 狀態**: 
  ```python
  resp = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo").json()
  # 若 url 不為空，則 polling 模式會失效；若 pending_update_count > 0 則代表 Bot 有收到訊息但程序未接手。
  ```
- **檢查程序競爭**: 
  ```bash
  ps aux | grep hermes-gateway
  ```

## 3. 修復標準作業程序 (Fix SOP)
1. **清場 (Flush)**: `pkill -9 hermes`。
2. **校時 (Validate Identity)**: 比對 `multi_bot_routing_map.md` 確認 `.env` 中的 Token 是否正確。
3. **解除鎖定 (Unlock)**: 清空 `config.yaml` 中的 `allowed_channels`。
4. **重啟 (Rebuild)**: `hermes gateway run --replace`。

## 4. 學習點 (Architect's Note)
- **無駄無駄無駄！** 以後遇到「不回覆」問題，優先檢查身分 (Token) 與權限 (allowed_channels)，而非單純重啟。
