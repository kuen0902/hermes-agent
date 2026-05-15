---
name: swift-mac-automation
description: Bridge Python logic with native Swift scripts for high-performance macOS automation.
platform: macOS
---

# Swift-Mac-Automation Bridge (SOP)

## 1. 核心哲學
當 AppleScript 過於緩慢或 Python 庫 (pyobjc) 過於臃腫時，使用 Swift 作為系統操作的「尖刀」。

## 2. 通知機制 (Notification Bypass)
由於 `UNUserNotificationCenter` 要求 Bundle ID，在命令行腳本中應優先使用 Swift 呼叫 `NSAppleScript` 或 `OSA` 引擎發送通知，或將 Swift 編譯為 App。

## 3. Numbers 互動
優先使用 Swift 的 `Foundation` 處理資料格式，並透過 `ScriptingBridge` 控制 Numbers.app。

## 4. 效能優勢
- 避免頻繁啟動 Python 虛擬環境。
- 直接讀取系統 API (AppKit/Foundation)。

## 5. 跨語言調用 (Swift 執行 Python)
當 Swift 作為編排器 (Orchestrator) 呼叫 Python 子腳本時，必須遵循以下規則：
- **絕對路徑**：使用 `Process()` 時，`executableURL` 必須指向特定的 Python 虛擬環境路徑（例如 `/Users/bookid/workspace/hermes-agent/venv_314/bin/python`），而非 `/usr/bin/env`。
- **原因**：Cron 任務環境變數極簡，使用環境路徑常會導致跳回系統 Python 並引發 `ModuleNotFoundError`。

## 6. Cron 執行陷阱
- **誤判風險**：Hermes Cron 執行器在某些環境下可能會將 `.swift` 誤植為 Python 執行。
- **最佳實踐**：對於所有 `no_agent` 的原生 Swift 任務，建議封裝入一個 `.sh` 腳本，透過 `/usr/bin/swift path/to/script.swift` 進行調用。
