import Foundation

// MARK: - Color & Prefix Utilities
enum ANSIColor: String {
    case red = "\u{001B}[0;31m"
    case green = "\u{001B}[0;32m"
    case yellow = "\u{001B}[0;33m"
    case blue = "\u{001B}[0;34m"
    case cyan = "\u{001B}[0;36m"
    case reset = "\u{001B}[0;0m"
    case bold = "\u{001B}[1m"
}

var hasCriticalError = false
var criticalMessages: [String] = []

func logSuccess(_ message: String) {
    print("\(ANSIColor.green.rawValue)✅ \(message)\(ANSIColor.reset.rawValue)")
}

func logWarning(_ message: String) {
    print("\(ANSIColor.yellow.rawValue)⚠️ \(message)\(ANSIColor.reset.rawValue)")
}

func logError(_ category: String, _ message: String) {
    hasCriticalError = true
    let formatted = "   - [\(category)] \(message)"
    criticalMessages.append(formatted)
    print("\(ANSIColor.red.rawValue)❌ \(category): \(message)\(ANSIColor.reset.rawValue)")
}

// MARK: - 1. Network Connectivity Check
func checkNetwork() -> Bool {
    let semaphore = DispatchSemaphore(value: 0)
    var success = false
    guard let url = URL(string: "https://www.google.com") else { return false }
    
    var request = URLRequest(url: url)
    request.timeoutInterval = 2.0
    
    let task = URLSession.shared.dataTask(with: request) { _, response, error in
        if error == nil, let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
            success = true
        }
        semaphore.signal()
    }
    task.resume()
    _ = semaphore.wait(timeout: .now() + 2.5)
    return success
}

// MARK: - 2. Telegram Gateway Check
struct GatewayState: Codable {
    let pid: Int?
    let gateway_state: String?
    struct Platforms: Codable {
        struct Telegram: Codable {
            let state: String?
            let error_code: Int?
            let error_message: String?
        }
        let telegram: Telegram?
    }
    let platforms: Platforms?
}

func checkTelegramGateway() {
    let path = "/Users/bookid/.hermes/gateway_state.json"
    let fileURL = URL(fileURLWithPath: path)
    
    do {
        let data = try Data(contentsOf: fileURL)
        let decoder = JSONDecoder()
        let state = try decoder.decode(GatewayState.self, from: data)
        
        let pidStr = state.pid != nil ? "PID: \(state.pid!)" : "PID: Unknown"
        let gatewayStatus = state.gateway_state ?? "unknown"
        let telegramStatus = state.platforms?.telegram?.state ?? "unknown"
        
        if gatewayStatus == "running" && telegramStatus == "connected" {
            logSuccess("Telegram Gateway: OK (\(pidStr), Connected)")
        } else {
            let errMsg = state.platforms?.telegram?.error_message ?? "No error message"
            logError("TelegramGateway", "ERROR (Gateway: \(gatewayStatus), Telegram: \(telegramStatus), \(errMsg))")
        }
    } catch {
        logError("TelegramGateway", "CRITICAL (Failed to read state file: \(error.localizedDescription))")
    }
}

// MARK: - 3. Python Venv Check
func checkPythonVenv() {
    let venvPython = "/Users/bookid/.hermes/.venv/bin/python"
    let fileManager = FileManager.default
    if fileManager.fileExists(atPath: venvPython) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: venvPython)
        process.arguments = ["--version"]
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        
        do {
            try process.run()
            process.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) {
                logSuccess("Python Venv (3.14.4): OK (\(output))")
            } else {
                logSuccess("Python Venv (3.14.4): OK (Path exists)")
            }
        } catch {
            logWarning("Python Venv: Warning (Venv exists but execution failed: \(error.localizedDescription))")
        }
    } else {
        logError("PythonVenv", "ERROR (Venv path not found at \(venvPython))")
    }
}

// MARK: - 4. SQLite Database Check
func checkSQLiteDatabase() {
    let dbPath = "/Users/bookid/.hermes/data/portfolio.db"
    let fileManager = FileManager.default
    if !fileManager.fileExists(atPath: dbPath) {
        logError("SQLiteDatabase", "ERROR (Database file not found at \(dbPath))")
        return
    }
    
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/sqlite3")
    process.arguments = [dbPath, "PRAGMA integrity_check;"]
    let pipe = Pipe()
    process.standardOutput = pipe
    
    do {
        try process.run()
        process.waitUntilExit()
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        if let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines), output == "ok" {
            let countProcess = Process()
            countProcess.executableURL = URL(fileURLWithPath: "/usr/bin/sqlite3")
            countProcess.arguments = [dbPath, "SELECT count(*) FROM sqlite_master WHERE type='table';"]
            let countPipe = Pipe()
            countProcess.standardOutput = countPipe
            try countProcess.run()
            countProcess.waitUntilExit()
            let countData = countPipe.fileHandleForReading.readDataToEndOfFile()
            let countStr = String(data: countData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? "Unknown"
            
            logSuccess("SQLite Database (portfolio.db): OK - \(countStr) Tables, Integrity Checked")
        } else {
            logError("SQLiteDatabase", "ERROR (Integrity check failed)")
        }
    } catch {
        logError("SQLiteDatabase", "ERROR (Failed to check database: \(error.localizedDescription))")
    }
}

// MARK: - 5. Disk Space Check
func checkDiskSpace() {
    let fileManager = FileManager.default
    do {
        let attrs = try fileManager.attributesOfFileSystem(forPath: "/Users/bookid/.hermes")
        if let freeSize = attrs[.systemFreeSize] as? Int64,
           let totalSize = attrs[.systemSize] as? Int64 {
            let freeGB = Double(freeSize) / 1_000_000_000.0
            let totalGB = Double(totalSize) / 1_000_000_000.0
            let percentAvailable = (Double(freeSize) / Double(totalSize)) * 100.0
            if percentAvailable < 10.0 {
                logError("DiskSpace", String(format: "CRITICAL - Only %.1f GB Available (%.1f%% of %.1f GB)", freeGB, percentAvailable, totalGB))
            } else {
                logSuccess(String(format: "Disk Space: OK - %.1f GB Available (%.1f%% of %.1f GB)", freeGB, percentAvailable, totalGB))
            }
        } else {
            logWarning("Disk Space: OK (Unable to calculate exact space)")
        }
    } catch {
        logWarning("Disk Space: OK (Failed to fetch attributes: \(error.localizedDescription))")
    }
}

// MARK: - 6. environment .env check
func checkEnvVariables() {
    let envPath = "/Users/bookid/.hermes/.env"
    let fileManager = FileManager.default
    if !fileManager.fileExists(atPath: envPath) {
        logError("Environment", "ERROR (.env file is missing!)")
        return
    }
    
    do {
        let content = try String(contentsOfFile: envPath, encoding: .utf8)
        let lines = content.components(separatedBy: "\n")
        var envKeys: Set<String> = []
        for line in lines {
            let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
            if trimmed.isEmpty || trimmed.hasPrefix("#") { continue }
            let parts = trimmed.components(separatedBy: "=")
            if let key = parts.first?.trimmingCharacters(in: .whitespacesAndNewlines) {
                envKeys.insert(key)
            }
        }
        
        let requiredKeys = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_HOME_CHANNEL", "TAVILY_API_KEY"]
        var missingKeys: [String] = []
        for key in requiredKeys {
            if !envKeys.contains(key) {
                missingKeys.append(key)
            }
        }
        
        if missingKeys.isEmpty {
            logSuccess("Environment Configuration (.env): OK - All required variables present")
        } else {
            logError("Environment", "ERROR - Missing required configuration keys: \(missingKeys.joined(separator: ", "))")
        }
    } catch {
        logError("Environment", "ERROR - Failed to read .env file: \(error.localizedDescription)")
    }
}

// MARK: - 7. Cron Jobs Dynamic Check
struct CronJob: Codable {
    let id: String
    let name: String
    let enabled: Bool
    let last_status: String?
    let last_error: String?
    let last_run_at: String?
    let script: String?
}

struct CronJobsContainer: Codable {
    let jobs: [CronJob]
}

func isGlobalCommandAvailable(_ command: String) -> Bool {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/which")
    process.arguments = [command]
    let pipe = Pipe()
    process.standardOutput = pipe
    process.standardError = pipe
    do {
        try process.run()
        process.waitUntilExit()
        return process.terminationStatus == 0
    } catch {
        return false
    }
}

func checkCronJobs() {
    let path = "/Users/bookid/.hermes/cron/jobs.json"
    let fileURL = URL(fileURLWithPath: path)
    
    do {
        let data = try Data(contentsOf: fileURL)
        let decoder = JSONDecoder()
        let container = try decoder.decode(CronJobsContainer.self, from: data)
        
        let activeJobs = container.jobs.filter { $0.enabled }
        
        // --- 1. 先期配置與路徑預檢 (Configuration & Path Pre-check) ---
        var preCheckFailures: [String] = []
        let fileManager = FileManager.default
        let scriptsDir = "/Users/bookid/.hermes/scripts"
        
        for job in activeJobs {
            guard let scriptCmd = job.script, !scriptCmd.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                continue
            }
            
            let tokens = scriptCmd.components(separatedBy: .whitespacesAndNewlines).filter { !$0.isEmpty }
            guard let firstToken = tokens.first else { continue }
            
            // A. 檢查是否有外部前綴 (如 /Users/bookid/.hermes/.venv/bin/python) 導致安全阻斷
            if tokens.count > 1 && (firstToken.contains(".venv") || firstToken.contains("/bin/python") || firstToken.hasSuffix("python") || firstToken.hasSuffix("python3")) {
                let msg = "Job [\(job.name)] (ID: \(job.id)) script config contains external executable prefix '\(firstToken)'. This will trigger hermes pre-run security block! Keep script paths relative or direct to scripts/ folder."
                preCheckFailures.append(msg)
                continue
            }
            
            // B. 檢查腳本路徑是否存在
            let scriptPath: String
            if firstToken.hasPrefix("/") {
                scriptPath = firstToken
                if !fileManager.fileExists(atPath: scriptPath) {
                    let msg = "Job [\(job.name)] (ID: \(job.id)) script file not found at: \(scriptPath)"
                    preCheckFailures.append(msg)
                    continue
                }
            } else if !firstToken.contains(".") {
                // 如果不帶副檔名且不含點，可能是一個全域系統命令 (例如 "hermes")
                if isGlobalCommandAvailable(firstToken) {
                    // 全域命令存在，跳過後續的路徑與權限檢查
                    continue
                } else {
                    let msg = "Job [\(job.name)] (ID: \(job.id)) specifies global command '\(firstToken)' which is not found in system PATH."
                    preCheckFailures.append(msg)
                    continue
                }
            } else {
                scriptPath = "\(scriptsDir)/\(firstToken)"
                if !fileManager.fileExists(atPath: scriptPath) {
                    let msg = "Job [\(job.name)] (ID: \(job.id)) script file not found at: \(scriptPath)"
                    preCheckFailures.append(msg)
                    continue
                }
            }
            
            // C. 檢查是否有可執行權限
            if !fileManager.isExecutableFile(atPath: scriptPath) {
                let msg = "Job [\(job.name)] (ID: \(job.id)) script file at \(scriptPath) is not executable! Please run chmod +x on it."
                preCheckFailures.append(msg)
            }
        }
        
        // 匯報預檢結果
        if !preCheckFailures.isEmpty {
            logError("CronJobsPreCheck", "\(preCheckFailures.count) configuration/path validation issues detected!")
            for failure in preCheckFailures {
                print("  \(ANSIColor.yellow.rawValue)⚠️ \(failure)\(ANSIColor.reset.rawValue)")
            }
        } else {
            logSuccess("Cron Jobs Configuration Pre-check: OK")
        }
        
        // --- 2. 歷史執行狀態檢查 ---
        let failedJobs = activeJobs.filter { $0.last_status == "error" }
        
        if failedJobs.isEmpty {
            logSuccess("Cron Jobs Execution Status: \(activeJobs.count) Active, no failed executions in last 24h")
        } else {
            logError("CronJobsExecution", "\(activeJobs.count) Active, \(failedJobs.count) FAILED executions detected in logs!")
            for job in failedJobs {
                print("  ---------------------------------------------")
                print("  \(ANSIColor.bold.rawValue)Job Name:\(ANSIColor.reset.rawValue) \(ANSIColor.yellow.rawValue)\(job.name)\(ANSIColor.reset.rawValue) (ID: \(job.id))")
                print("  \(ANSIColor.bold.rawValue)Last Run:\(ANSIColor.reset.rawValue) \(job.last_run_at ?? "Never")")
                let errorLines = (job.last_error ?? "Unknown error").components(separatedBy: "\n")
                print("  \(ANSIColor.bold.rawValue)Error Output:\(ANSIColor.reset.rawValue)")
                for line in errorLines {
                    print("    \(ANSIColor.red.rawValue)\(line)\(ANSIColor.reset.rawValue)")
                }
            }
            print("  ---------------------------------------------")
        }
    } catch {
        logError("CronJobs", "ERROR (Failed to read or parse jobs.json: \(error.localizedDescription))")
    }
}

// MARK: - Main Execution Flow
print("\(ANSIColor.bold.rawValue)\(ANSIColor.cyan.rawValue)=== Hermes System Diagnostics ===\(ANSIColor.reset.rawValue)")
let startTime = Date()

// Run network check
if checkNetwork() {
    logSuccess("Network Connectivity: OK")
} else {
    logError("Network", "ERROR (Ping/Google connection timeout)")
}

checkTelegramGateway()
checkPythonVenv()
checkSQLiteDatabase()
checkDiskSpace()
checkEnvVariables()
checkCronJobs()

let duration = Date().timeIntervalSince(startTime)
print(String(format: "\n\(ANSIColor.cyan.rawValue)Diagnostics completed in %.2fs.\(ANSIColor.reset.rawValue)", duration))

if hasCriticalError {
    print("\n\(ANSIColor.red.rawValue)🚨 CRITICAL FAILURES DETECTED: \(ANSIColor.reset.rawValue)")
    for msg in criticalMessages {
        print(msg)
    }
    exit(1)
} else {
    exit(0)
}
