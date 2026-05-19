#!/usr/bin/env swift
import Foundation

// Check if running in auto-heal mode from cron
let isAutoHeal = CommandLine.arguments.contains("--auto-heal")

print("==================================================")
print("🔍 Hermes Tri-Language Diagnostic & Healing System 啟動")
if isAutoHeal { print("🛠️  Auto-Heal Mode: ENABLED") }
print("==================================================\n")

let fm = FileManager.default
let homeDir = fm.homeDirectoryForCurrentUser.path
let scriptsDir = "\(homeDir)/.hermes/scripts"
let dataDir = "\(homeDir)/.hermes/data"
let venvPython = "\(homeDir)/.hermes/.venv/bin/python"

var allPassed = true
var criticalFailures = [String]()

func reportPass(_ msg: String) {
    print("[✅ PASS] \(msg)")
}

func reportFail(_ msg: String, advice: String) {
    print("[❌ FAIL] \(msg)")
    print("   💡 修復建議: \(advice)")
    allPassed = false
    criticalFailures.append(msg)
}

func reportWarn(_ msg: String, advice: String) {
    print("[⚠️ WARN] \(msg)")
    print("   💡 注意: \(advice)")
}

func executeAutoHeal(command: String, args: [String], description: String) -> Bool {
    print("   ⚡ [自動修復] 正在執行: \(description)...")
    let process = Process()
    process.executableURL = URL(fileURLWithPath: command)
    process.arguments = args
    do {
        try process.run()
        process.waitUntilExit()
        if process.terminationStatus == 0 {
            print("   ✅ [自動修復] 成功: \(description)")
            return true
        } else {
            print("   ❌ [自動修復] 失敗: 退出碼 \(process.terminationStatus)")
            return false
        }
    } catch {
        print("   ❌ [自動修復] 執行異常: \(error.localizedDescription)")
        return false
    }
}

// ---------------------------------------------------------
// 1. 引擎狀態檢查 (Binary & Environment Check)
// ---------------------------------------------------------
print("--- 1. 引擎狀態與環境檢查 ---")
if fm.fileExists(atPath: venvPython) {
    reportPass("Python 虛擬環境存在: \(venvPython)")
} else {
    reportFail("找不到 Python 虛擬環境", advice: "請執行 upgrade_python.sh 或重建 venv。")
}

let coreScripts = ["hermes_orchestrator", "hermes_sync", "hermes_monitor"]
var needsRecompile = false
for script in coreScripts {
    let sourcePath = "\(scriptsDir)/\(script).swift"
    let binaryPath = "\(scriptsDir)/\(script)"
    
    if fm.fileExists(atPath: sourcePath) && fm.fileExists(atPath: binaryPath) {
        do {
            let sourceAttrs = try fm.attributesOfItem(atPath: sourcePath)
            let binaryAttrs = try fm.attributesOfItem(atPath: binaryPath)
            
            if let sourceDate = sourceAttrs[.modificationDate] as? Date,
               let binaryDate = binaryAttrs[.modificationDate] as? Date {
                if sourceDate > binaryDate {
                    reportFail("\(script) 二進位檔過期", advice: "您修改了源碼但尚未編譯！")
                    needsRecompile = true
                } else {
                    reportPass("\(script) 編譯狀態正常")
                }
            }
        } catch {
            reportWarn("無法讀取 \(script) 的修改時間", advice: "請檢查檔案權限")
        }
    } else {
        reportWarn("\(script) 源碼或二進位檔缺失", advice: "如果是純 Python 腳本則忽略此警告。")
    }
}

if needsRecompile && isAutoHeal {
    let healed = executeAutoHeal(command: "/bin/bash", args: ["\(scriptsDir)/compile_swift.sh"], description: "重新編譯 Swift 二進位引擎")
    if healed {
        reportPass("自動修復完成: 二進位檔已更新至最新版本！")
        // Remove the latest failures added by the loops since we fixed it
        criticalFailures.removeAll { $0.contains("二進位檔過期") }
        // Note: allPassed might still be false globally, but we'll evaluate at the end based on criticalFailures
    }
}
print("")

// ---------------------------------------------------------
// 2. SQLite 資料庫健康度檢查 (Portfolio DB Check)
// ---------------------------------------------------------
print("--- 2. SQLite (portfolio.db) 健康度測試 ---")
let dbPath = "\(dataDir)/portfolio.db"
if fm.fileExists(atPath: dbPath) {
    let sqliteProcess = Process()
    sqliteProcess.executableURL = URL(fileURLWithPath: venvPython)
    sqliteProcess.arguments = ["\(scriptsDir)/portfolio_tool.py", "--view"]
    
    let sqlitePipe = Pipe()
    sqliteProcess.standardOutput = sqlitePipe
    sqliteProcess.standardError = sqlitePipe
    
    do {
        try sqliteProcess.run()
        sqliteProcess.waitUntilExit()
        
        let sqliteData = sqlitePipe.fileHandleForReading.readDataToEndOfFile()
        if sqliteProcess.terminationStatus == 0 {
            reportPass("SQLite 資料庫連線與查詢成功")
        } else {
            let errorMsg = String(data: sqliteData, encoding: .utf8) ?? "Unknown Error"
            reportFail("SQLite 查詢失敗", advice: "可能是資料庫結構毀損：\(errorMsg)")
        }
    } catch {
        reportFail("無法執行 portfolio_tool.py", advice: error.localizedDescription)
    }
} else {
    reportWarn("找不到 portfolio.db", advice: "如果尚未建立，系統會在第一次操作時自動產生。")
}
print("")

// ---------------------------------------------------------
// 3. 資料中樞完整性 (Data Integrity Check)
// ---------------------------------------------------------
print("--- 3. 資料中樞完整性檢查 ---")
let jsonPath = "\(dataDir)/central_stock_data.json"
var needsPortfolioSync = false

if fm.fileExists(atPath: jsonPath) {
    do {
        let data = try Data(contentsOf: URL(fileURLWithPath: jsonPath))
        if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
            
            if let personalData = json["personal_data"] as? [String: Any] {
                if personalData.isEmpty {
                    reportFail("personal_data 持股清單為空！", advice: "之前的超時錯誤可能已清空資料。")
                    needsPortfolioSync = true
                } else {
                    reportPass("成功讀取 \(personalData.count) 檔個人持股資料")
                }
            } else {
                reportFail("central_stock_data.json 缺少 personal_data 節點", advice: "資料格式損毀。")
                needsPortfolioSync = true
            }
        } else {
            reportFail("JSON 格式無法解析", advice: "請檢查 \(jsonPath) 內容是否正確")
        }
    } catch {
        reportFail("讀取 JSON 失敗", advice: error.localizedDescription)
    }
} else {
    reportFail("找不到 central_stock_data.json", advice: "檔案遺失。")
    needsPortfolioSync = true
}

if needsPortfolioSync && isAutoHeal {
    let healed = executeAutoHeal(command: "/usr/bin/swift", args: ["\(scriptsDir)/sync_portfolio_pure_swift.swift"], description: "手動強制從 Numbers 同步持股資料")
    if healed {
        reportPass("自動修復完成: 持股資料已重新同步！")
        criticalFailures.removeAll { $0.contains("持股清單為空") || $0.contains("缺少 personal_data") || $0.contains("找不到 central_stock_data") }
    }
}
print("")

// ---------------------------------------------------------
// 4. Python 分析與取價測試 (Python Sub-process Check)
// ---------------------------------------------------------
print("--- 4. Python 取價網路測試 (均豪 5443.TWO) ---")
let pyScript = """
import sys
import json
try:
    import yfinance as yf
    ticker = yf.Ticker("5443.TWO")
    info = ticker.fast_info
    price = info.last_price
    print(json.dumps({"status": "ok", "price": price}))
except Exception as e:
    print(json.dumps({"status": "error", "message": str(e)}))
"""
let pyProcess = Process()
pyProcess.executableURL = URL(fileURLWithPath: venvPython)
pyProcess.arguments = ["-c", pyScript]
let pyPipe = Pipe()
pyProcess.standardOutput = pyPipe
pyProcess.standardError = pyPipe

do {
    try pyProcess.run()
    pyProcess.waitUntilExit()
    let pyData = pyPipe.fileHandleForReading.readDataToEndOfFile()
    if let pyOutput = String(data: pyData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) {
        if let pyJson = try? JSONSerialization.jsonObject(with: pyOutput.data(using: .utf8)!) as? [String: Any],
           let status = pyJson["status"] as? String {
            if status == "ok", let price = pyJson["price"] as? Double {
                reportPass("Python yfinance 抓取測試成功 (均豪 5443.TWO: \(price))")
            } else {
                let msg = pyJson["message"] as? String ?? "Unknown error"
                reportFail("Python yfinance 抓取失敗 (均豪 5443.TWO)", advice: "可能遭到 Cloudflare 阻擋、無網路連線，或 Ticker 代碼錯誤: \(msg)")
            }
        } else {
             reportWarn("Python 輸出非預期 JSON", advice: "輸出內容: \(pyOutput)")
        }
    }
} catch {
    reportFail("無法執行 Python", advice: error.localizedDescription)
}
print("")

// ---------------------------------------------------------
// 5. Telegram 網路與金鑰測試 (Notification Check)
// ---------------------------------------------------------
print("--- 5. Telegram 金鑰與網路連線測試 ---")
let envPath = "\(homeDir)/.hermes/.env"
var telegramToken: String? = nil

if fm.fileExists(atPath: envPath) {
    do {
        let envContent = try String(contentsOfFile: envPath, encoding: .utf8)
        let lines = envContent.components(separatedBy: .newlines)
        for line in lines {
            if line.hasPrefix("TELEGRAM_BOT_TOKEN=") {
                telegramToken = line.replacingOccurrences(of: "TELEGRAM_BOT_TOKEN=", with: "").trimmingCharacters(in: .whitespacesAndNewlines)
            }
        }
    } catch {
        reportFail("無法讀取 .env 檔案", advice: error.localizedDescription)
    }
} else {
    reportFail("找不到 .env 檔案", advice: "請確保配置檔存在於 \(envPath)")
}

if let token = telegramToken, !token.isEmpty {
    let dispatchGroup = DispatchGroup()
    dispatchGroup.enter()
    
    let urlString = "https://api.telegram.org/bot\(token)/getMe"
    if let url = URL(string: urlString) {
        let task = URLSession.shared.dataTask(with: url) { data, response, error in
            defer { dispatchGroup.leave() }
            
            if let error = error {
                reportFail("無法連線至 Telegram API", advice: "網路異常或 DNS 錯誤: \(error.localizedDescription)")
                return
            }
            
            if let httpResponse = response as? HTTPURLResponse {
                if httpResponse.statusCode == 200 {
                    if let data = data,
                       let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                       let result = json["result"] as? [String: Any],
                       let botName = result["first_name"] as? String {
                        reportPass("Telegram 金鑰有效！機器人名稱: \(botName)")
                    } else {
                        reportPass("Telegram 金鑰有效！(HTTP 200)")
                    }
                } else if httpResponse.statusCode == 401 {
                    reportFail("Telegram 金鑰無效 (HTTP 401 Unauthorized)", advice: ".env 中的 TELEGRAM_BOT_TOKEN 已過期或被撤銷，請更新。")
                } else {
                    reportFail("Telegram API 回傳異常狀態碼: \(httpResponse.statusCode)", advice: "請檢查網路環境或 Telegram 伺服器狀態。")
                }
            }
        }
        task.resume()
        _ = dispatchGroup.wait(timeout: .now() + 5.0)
    } else {
        reportFail("無效的 Telegram Token URL 格式", advice: "請檢查 Token 內是否包含特殊非預期字元")
    }
} else {
    reportFail("在 .env 找不到 TELEGRAM_BOT_TOKEN", advice: "請確保您已設定推播金鑰")
}
print("")

// ---------------------------------------------------------
// 6. 股名與股號一致性檢查 (Stock Name Audit Check)
// ---------------------------------------------------------
print("--- 6. 股名與股號一致性稽核 ---")
let auditorPath = "\(scriptsDir)/stock_name_auditor.py"
if fm.fileExists(atPath: auditorPath) {
    let auditProcess = Process()
    auditProcess.executableURL = URL(fileURLWithPath: venvPython)
    auditProcess.arguments = [auditorPath]
    if isAutoHeal {
        auditProcess.arguments?.append("--auto-heal")
    }
    
    let auditPipe = Pipe()
    auditProcess.standardOutput = auditPipe
    auditProcess.standardError = auditPipe
    
    do {
        try auditProcess.run()
        auditProcess.waitUntilExit()
        let auditData = auditPipe.fileHandleForReading.readDataToEndOfFile()
        if let auditOutput = String(data: auditData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) {
            let lines = auditOutput.components(separatedBy: .newlines)
            for line in lines {
                print("   > \(line)")
            }
            if auditProcess.terminationStatus == 0 {
                if auditOutput.contains("修復完成") {
                    reportPass("股名不一致已自動修復 (Auto-Healed)")
                } else {
                    reportPass("股名一致性稽核通過")
                }
            } else {
                reportFail("發現股名不一致", advice: "請加上 --auto-heal 參數讓 AI 自動幫您修正！")
            }
        }
    } catch {
        reportFail("無法執行股名稽核", advice: error.localizedDescription)
    }
} else {
    reportWarn("找不到 stock_name_auditor.py", advice: "跳過股名一致性檢查。")
}
print("")

// ---------------------------------------------------------
// 7. Telegram 權限防護機制檢查
// ---------------------------------------------------------
print("--- 7. Telegram 權限防護機制檢查 ---")
if fm.fileExists(atPath: envPath) {
    do {
        let envContent = try String(contentsOfFile: envPath, encoding: .utf8)
        var allowedUsers: [String] = []
        var goldUsers: [String] = ["0"] // SILENCED (Formerly -1003744330314)
        
        for line in envContent.components(separatedBy: .newlines) {
            let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
            if trimmed.hasPrefix("TELEGRAM_ALLOWED_USERS=") {
                let val = trimmed.dropFirst("TELEGRAM_ALLOWED_USERS=".count)
                allowedUsers = val.split(separator: ",").map { String($0).trimmingCharacters(in: .whitespaces) }
            } else if trimmed.hasPrefix("HERMES_GOLD_EXPERIENCE_CHAT_ID=") {
                let val = trimmed.dropFirst("HERMES_GOLD_EXPERIENCE_CHAT_ID=".count)
                goldUsers = val.split(separator: ",").map { String($0).trimmingCharacters(in: .whitespaces) }
            }
        }
        
        if allowedUsers.isEmpty {
            reportWarn("未設定 TELEGRAM_ALLOWED_USERS", advice: "建議設定以提升安全性。")
        } else {
            var allGold = true
            for user in allowedUsers {
                if !goldUsers.contains(user) {
                    allGold = false
                    reportFail("Telegram 權限不一致: 用戶 \(user) 沒有 Gold Experience 權限！", advice: "這會導致進階持股功能 (買進/賣出/清單) 的按鈕被防護機制隱藏。請將該 ID 加入 HERMES_GOLD_EXPERIENCE_CHAT_ID。")
                }
            }
            if allGold {
                reportPass("Telegram UI 權限健康 (Allowed Users 皆已通過 Gold Experience 防護判定)")
            }
        }
    } catch {
        reportFail("無法讀取 .env", advice: "檢查權限。")
    }
} else {
    reportWarn("找不到 .env 檔案", advice: "跳過權限檢查。")
}
print("")

// ---------------------------------------------------------
// 8. 通訊分流協議與路由隔離檢查 (Information Segregation Check)
// ---------------------------------------------------------
print("--- 8. 通訊分流協議與路由隔離檢查 ---")
if fm.fileExists(atPath: "\(scriptsDir)/intraday_risk_monitor.py") {
    let routeScript = """
import sys
sys.path.append('\(scriptsDir)')
try:
    import intraday_risk_monitor as irm
    p = irm.PROFILES
    assert p['personal']['chat_id'] == '6326497055', 'Personal Chat ID mismatch'
    assert p['group']['chat_id'] == '-1003744330314', 'Group Chat ID mismatch'
    assert p['william']['chat_id'] == '8695583357', 'William Chat ID mismatch'
    assert p['personal']['token'].startswith('8737'), 'Personal Token mismatch'
    assert p['group']['token'].startswith('8737'), 'Group Token mismatch'
    assert p['william']['token'].startswith('8678'), 'William Token mismatch'
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
"""
    let routeProcess = Process()
    routeProcess.executableURL = URL(fileURLWithPath: venvPython)
    routeProcess.arguments = ["-c", routeScript]
    let routePipe = Pipe()
    routeProcess.standardOutput = routePipe
    routeProcess.standardError = routePipe
    
    do {
        try routeProcess.run()
        routeProcess.waitUntilExit()
        let routeData = routePipe.fileHandleForReading.readDataToEndOfFile()
        if let output = String(data: routeData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) {
            if output == "OK" {
                reportPass("通訊分流協議完整！(個人/群組/William 路由皆已隔離)")
            } else {
                reportFail("通訊分流協議異常", advice: "PROFILES 字典參數遭竄改或設定錯誤：\(output)")
            }
        }
    } catch {
        reportFail("無法驗證通訊分流", advice: error.localizedDescription)
    }
} else {
    reportWarn("找不到 intraday_risk_monitor.py", advice: "跳過通訊分流協議檢查。")
}
print("")

// ---------------------------------------------------------
// 9. 多重路由 Token 活體驗證 (Multi-Token Liveness Check)
// 10. 群組在籍與發送權限驗證 (Membership & Access Check)
// ---------------------------------------------------------
print("--- 9 & 10. 多重路由 Token 與群組權限驗證 ---")
if fm.fileExists(atPath: "\(scriptsDir)/intraday_risk_monitor.py") {
    let multiTokenScript = """
import sys
import json
import urllib.request
import ssl

sys.path.append('\(scriptsDir)')
try:
    import intraday_risk_monitor as irm
    profiles = irm.PROFILES
    ctx = ssl._create_unverified_context()
    
    errors = []
    
    for name, cfg in profiles.items():
        token = cfg.get('token', '')
        chat_id = cfg.get('chat_id', '')
        
        # 1. 驗證 Token (/getMe)
        getme_url = f"https://api.telegram.org/bot{token}/getMe"
        try:
            req = urllib.request.Request(getme_url)
            with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if not data.get('ok'):
                    errors.append(f"[{name}] Token 驗證失敗")
        except Exception as e:
            errors.append(f"[{name}] Token 無效 (HTTP 401/404)或網路錯誤")
            continue
            
        # 2. 驗證權限 (/getChat)
        getchat_url = f"https://api.telegram.org/bot{token}/getChat?chat_id={chat_id}"
        try:
            req = urllib.request.Request(getchat_url)
            with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if not data.get('ok'):
                    errors.append(f"[{name}] 無法存取 Chat ID {chat_id}")
        except Exception as e:
            errors.append(f"[{name}] Chat ID {chat_id} 找不到或無權限存取 (404/403)")
            
    if errors:
        print("FAIL|" + " ; ".join(errors))
    else:
        print("OK")
except Exception as e:
    print(f"FAIL|Script execution error: {e}")
"""
    let tokenProcess = Process()
    tokenProcess.executableURL = URL(fileURLWithPath: venvPython)
    tokenProcess.arguments = ["-c", multiTokenScript]
    let tokenPipe = Pipe()
    tokenProcess.standardOutput = tokenPipe
    tokenProcess.standardError = tokenPipe
    
    do {
        try tokenProcess.run()
        tokenProcess.waitUntilExit()
        let tokenData = tokenPipe.fileHandleForReading.readDataToEndOfFile()
        if let output = String(data: tokenData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) {
            if output == "OK" {
                reportPass("多重路由 Token 皆有效，且全部成功綁定對應的 Chat ID！")
            } else if output.hasPrefix("FAIL|") {
                let errs = output.replacingOccurrences(of: "FAIL|", with: "")
                reportFail("通訊層連線或權限異常", advice: errs)
            } else {
                reportFail("未知的驗證錯誤", advice: output)
            }
        }
    } catch {
        reportFail("無法驗證多重 Token", advice: error.localizedDescription)
    }
} else {
    reportWarn("找不到 intraday_risk_monitor.py", advice: "跳過 Token 驗證。")
}
print("")

// ---------------------------------------------------------
// 11. 股名 Markdown 地雷掃描 (Markdown Payload Check)
// ---------------------------------------------------------
print("--- 11. 股名 Markdown 地雷掃描 ---")
if fm.fileExists(atPath: "\(dataDir)/master_stock_registry.json") {
    let mdScript = """
import json
import sys

registry_path = '\(dataDir)/master_stock_registry.json'
try:
    with open(registry_path, 'r') as f:
        data = json.load(f)
    
    names = data.get('official_names', {}).values()
    dangerous_chars = ['*', '_', '`', '[']
    
    issues = []
    for name in names:
        for char in dangerous_chars:
            if char in name:
                issues.append(name)
                break
                
    if issues:
        print("WARN|" + ",".join(issues))
    else:
        print("OK")
except Exception as e:
    print(f"FAIL|Error parsing registry: {e}")
"""
    let mdProcess = Process()
    mdProcess.executableURL = URL(fileURLWithPath: venvPython)
    mdProcess.arguments = ["-c", mdScript]
    let mdPipe = Pipe()
    mdProcess.standardOutput = mdPipe
    mdProcess.standardError = mdPipe
    
    do {
        try mdProcess.run()
        mdProcess.waitUntilExit()
        let mdData = mdPipe.fileHandleForReading.readDataToEndOfFile()
        if let output = String(data: mdData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) {
            if output == "OK" {
                reportPass("無發現 Markdown 危險股名字元。")
            } else if output.hasPrefix("WARN|") {
                let stocks = output.replacingOccurrences(of: "WARN|", with: "")
                reportWarn("發現可能導致 Telegram 崩潰的股名", advice: "這些股名包含特殊符號 (*, _, [, `)：\(stocks)")
            } else {
                reportFail("Markdown 檢查失敗", advice: output)
            }
        }
    } catch {
        reportFail("無法執行 Markdown 掃描", advice: error.localizedDescription)
    }
} else {
    reportWarn("找不到 registry", advice: "跳過掃描。")
}
print("")

print("==================================================")
if criticalFailures.isEmpty {
    print("🌟 診斷完成：系統全鏈路完美健康，三語言協同架構運作正常！")
    exit(0)
} else {
    print("⚠️ 診斷完成：發現無法自動修復的嚴重錯誤，請立即介入！")
    for failure in criticalFailures {
        print("   - \(failure)")
    }
    exit(1)
}
print("==================================================")
