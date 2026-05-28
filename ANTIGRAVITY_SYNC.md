# Antigravity Sync Index
Ref: ARCHITECTURE.md

## 最新同步摘要 (2026-05-18)
1. **模型遷移**: 已從 Qwen 遷移至 Gemini-3-Flash-Preview。
2. **權限隔離**: 完成「白金之星」在「高潮不斷」群組的靜默封裝。
    - Config: `~/.hermes/profiles/star-platinum/config.yaml`
    - Env: `~/.hermes/profiles/star-platinum/.env`
3. **腳本修補**: `stock_alert.py` 已更新 Token 並加入靜默邏輯。
4. **Cron 優化**: 大量任務已從系統遞送修改為腳本直接 API 遞送，避開 Gateway 權限衝突。

**詳細架構與路徑請參閱 ARCHITECTURE.md。**
2026-05-27: Technical Audit Completed. Saved to Obsidian.
