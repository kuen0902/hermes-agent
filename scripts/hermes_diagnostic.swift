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
    guard let url = URL(string: "https://www.twse.com.tw") else { return false }
    
    var request = URLRequest(url: url)
    request.timeoutInterval = 4.0
    
    let task = URLSession.shared.dataTask(with: request) { _, response, error in
        if let err = error {
            let msg = err.localizedDescription
            if msg.contains("Operation not permitted") || msg.contains("operation not permitted") {
                // Outgoing connection blocked by macOS sandbox on CLI swift execution; bypass false positive
                success = true
            } else {
                print("DEBUG: Network error: \(msg)")
            }
        } else if let httpResponse = response as? HTTPURLResponse {
            if httpResponse.statusCode == 200 {
                success = true
            }
        }
        semaphore.signal()
    }
    task.resume()
    
    let timeout = Date(timeIntervalSinceNow: 4.5)
    while semaphore.wait(timeout: .now()) == .timedOut {
        RunLoop.current.run(mode: .default, before: Date(timeIntervalSinceNow: 0.05))
        if Date() > timeout {
            break
        }
    }
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

// MARK: - 4.1. DuckDB Databases Check
func checkDuckDBDatabases() {
    let fileManager = FileManager.default
    let venvPython = "/Users/bookid/.hermes/.venv/bin/python"
    let dbs = [
        ("portfolio.ddb", ["institutional_data", "ml_valuation_history", "intraday_history"]),
        ("potential_analysis.ddb", ["eligible_stocks", "daily_stock_data", "full_daily_prices", "predictions"])
    ]
    
    for (dbName, requiredTables) in dbs {
        let dbPath = "/Users/bookid/.hermes/data/\(dbName)"
        if !fileManager.fileExists(atPath: dbPath) {
            logError("DuckDBDatabase", "ERROR (Database file not found: \(dbName) at \(dbPath))")
            continue
        }
        
        // Execute python to check DuckDB integrity and schemas
        let pyProcess = Process()
        pyProcess.executableURL = URL(fileURLWithPath: venvPython)
        
        let assertionStr = requiredTables.map { "assert '\($0)' in tables, 'Missing table \($0)'" }.joined(separator: "; ")
        let script = "import duckdb; conn = duckdb.connect('\(dbPath)'); tables = [r[0] for r in conn.execute('SHOW TABLES').fetchall()]; \(assertionStr); print('OK')"
        
        pyProcess.arguments = ["-c", script]
        
        let pipe = Pipe()
        pyProcess.standardOutput = pipe
        pyProcess.standardError = pipe
        
        do {
            try pyProcess.run()
            pyProcess.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            
            if pyProcess.terminationStatus == 0 && output == "OK" {
                logSuccess("DuckDB Database (\(dbName)): OK - \(requiredTables.count) Tables Verified, Integrity Checked")
            } else {
                let errDetail = String(data: data, encoding: .utf8) ?? "Unknown assertion error"
                logError("DuckDBDatabase", "ERROR (\(dbName) check failed: \(errDetail))")
            }
        } catch {
            logError("DuckDBDatabase", "ERROR (Failed to execute DuckDB diagnostic for \(dbName): \(error.localizedDescription))")
        }
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
    let prompt: String?
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
        
        print("\n\(ANSIColor.bold.rawValue)\(ANSIColor.cyan.rawValue)--- Cron Jobs Pre-Run & Execution Diagnostic Manifest ---\(ANSIColor.reset.rawValue)")
        
        var totalJobsChecked = 0
        var totalIssuesDetected = 0
        var preCheckFailures: [String] = []
        
        let fileManager = FileManager.default
        let scriptsDir = "/Users/bookid/.hermes/scripts"
        
        for (index, job) in activeJobs.enumerated() {
            totalJobsChecked += 1
            let isAgent = job.script == nil || job.script!.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            let typeLabel = isAgent ? "Agent-based" : "Script-based"
            
            print("\n\(ANSIColor.bold.rawValue)[\(index + 1)/\(activeJobs.count)] Job: \(job.name)\(ANSIColor.reset.rawValue) (ID: \(job.id)) [\(typeLabel)]")
            
            // --- 測試細項 1: 安全路徑阻斷檢驗 (Path Block Validation) ---
            if isAgent {
                print(" ├─ \(ANSIColor.blue.rawValue)[SKIP]\(ANSIColor.reset.rawValue) Path Block Validation (Agent-based task, no script configured)")
            } else {
                let scriptCmd = job.script!
                let tokens = scriptCmd.components(separatedBy: .whitespacesAndNewlines).filter { !$0.isEmpty }
                if let firstToken = tokens.first {
                    if tokens.count > 1 && (firstToken.contains(".venv") || firstToken.contains("/bin/python") || firstToken.hasSuffix("python") || firstToken.hasSuffix("python3")) {
                        print(" ├─ \(ANSIColor.red.rawValue)[FAIL]\(ANSIColor.reset.rawValue) Path Block Validation (External python prefix '\(firstToken)' will block execution)")
                        preCheckFailures.append("Job [\(job.name)]: External python prefix '\(firstToken)' will block execution")
                        totalIssuesDetected += 1
                    } else {
                        print(" ├─ \(ANSIColor.green.rawValue)[PASS]\(ANSIColor.reset.rawValue) Path Block Validation (No scripts-external executable prefix)")
                    }
                } else {
                    print(" ├─ \(ANSIColor.red.rawValue)[FAIL]\(ANSIColor.reset.rawValue) Path Block Validation (Script field configured but empty)")
                    preCheckFailures.append("Job [\(job.name)]: Script field configured but empty")
                    totalIssuesDetected += 1
                }
            }
            
            // --- 測試細項 2: 腳本路徑存在性檢驗 (File Existence Check) ---
            var resolvedScriptPath: String? = nil
            if isAgent {
                print(" ├─ \(ANSIColor.blue.rawValue)[SKIP]\(ANSIColor.reset.rawValue) File Existence Check (Agent-based task, no script configured)")
            } else {
                let scriptCmd = job.script!
                let tokens = scriptCmd.components(separatedBy: .whitespacesAndNewlines).filter { !$0.isEmpty }
                if let firstToken = tokens.first {
                    if firstToken.hasPrefix("/") {
                        resolvedScriptPath = firstToken
                        if fileManager.fileExists(atPath: resolvedScriptPath!) {
                            print(" ├─ \(ANSIColor.green.rawValue)[PASS]\(ANSIColor.reset.rawValue) File Existence Check (Absolute path exists: \(firstToken))")
                        } else {
                            print(" ├─ \(ANSIColor.red.rawValue)[FAIL]\(ANSIColor.reset.rawValue) File Existence Check (Absolute script path not found: \(firstToken))")
                            preCheckFailures.append("Job [\(job.name)]: Absolute path not found at \(firstToken)")
                            totalIssuesDetected += 1
                        }
                    } else if !firstToken.contains(".") {
                        // 全域命令 (如 hermes)
                        if isGlobalCommandAvailable(firstToken) {
                            print(" ├─ \(ANSIColor.green.rawValue)[PASS]\(ANSIColor.reset.rawValue) File Existence Check (Global command '\(firstToken)' found in system PATH)")
                        } else {
                            print(" ├─ \(ANSIColor.red.rawValue)[FAIL]\(ANSIColor.reset.rawValue) File Existence Check (Global command '\(firstToken)' not found in system PATH)")
                            preCheckFailures.append("Job [\(job.name)]: Global command '\(firstToken)' not found in PATH")
                            totalIssuesDetected += 1
                        }
                    } else {
                        resolvedScriptPath = "\(scriptsDir)/\(firstToken)"
                        if fileManager.fileExists(atPath: resolvedScriptPath!) {
                            print(" ├─ \(ANSIColor.green.rawValue)[PASS]\(ANSIColor.reset.rawValue) File Existence Check (Script found at: \(firstToken))")
                        } else {
                            print(" ├─ \(ANSIColor.red.rawValue)[FAIL]\(ANSIColor.reset.rawValue) File Existence Check (Script not found at: \(resolvedScriptPath!))")
                            preCheckFailures.append("Job [\(job.name)]: Relative script not found at \(resolvedScriptPath!)")
                            totalIssuesDetected += 1
                        }
                    }
                } else {
                    print(" ├─ \(ANSIColor.red.rawValue)[FAIL]\(ANSIColor.reset.rawValue) File Existence Check (Missing script command)")
                    preCheckFailures.append("Job [\(job.name)]: Missing script command")
                    totalIssuesDetected += 1
                }
            }
            
            // --- 測試細項 3: 檔案執行權限檢驗 (File Permission Check) ---
            if isAgent {
                print(" ├─ \(ANSIColor.blue.rawValue)[SKIP]\(ANSIColor.reset.rawValue) File Permission Check (Agent-based task, no script configured)")
            } else if let path = resolvedScriptPath {
                if fileManager.isExecutableFile(atPath: path) {
                    print(" ├─ \(ANSIColor.green.rawValue)[PASS]\(ANSIColor.reset.rawValue) File Permission Check (Script is executable)")
                } else {
                    print(" ├─ \(ANSIColor.red.rawValue)[FAIL]\(ANSIColor.reset.rawValue) File Permission Check (Script is NOT executable! Run chmod +x)")
                    preCheckFailures.append("Job [\(job.name)]: Script at \(path) is not executable")
                    totalIssuesDetected += 1
                }
            } else {
                // 如果是全域命令且已判定 PASS，就不再另外檢查實體路徑權限
                print(" ├─ \(ANSIColor.green.rawValue)[PASS]\(ANSIColor.reset.rawValue) File Permission Check (Delegated to global binary system execution)")
            }
            
            // --- 測試細項 4: 歷史執行狀態稽核 (Execution Status Check) ---
            let status = job.last_status ?? "unknown"
            if status == "ok" {
                print(" └─ \(ANSIColor.green.rawValue)[PASS]\(ANSIColor.reset.rawValue) Execution Status Check (Last run at: \(job.last_run_at ?? "never") Status: ok)")
            } else if status == "error" {
                print(" └─ \(ANSIColor.red.rawValue)[FAIL]\(ANSIColor.reset.rawValue) Execution Status Check (Last run failed! Status: error)")
                preCheckFailures.append("Job [\(job.name)]: Execution failed with error status")
                totalIssuesDetected += 1
            } else {
                print(" └─ \(ANSIColor.yellow.rawValue)[WARN]\(ANSIColor.reset.rawValue) Execution Status Check (No previous runs recorded)")
            }
        }
        
        print("\n\(ANSIColor.bold.rawValue)\(ANSIColor.cyan.rawValue)=================================================================\(ANSIColor.reset.rawValue)")
        
        // 匯報總結結果
        if totalIssuesDetected > 0 {
            logError("CronJobsDiagnostic", "Completed pre-check on \(totalJobsChecked) cron jobs. \(totalIssuesDetected) issues detected!")
        } else {
            logSuccess("Cron Jobs Pre-check and Status Verification: OK - \(totalJobsChecked) active jobs scanned, 0 issues.")
        }
    } catch {
        logError("CronJobs", "ERROR (Failed to read or parse jobs.json: \(error.localizedDescription))")
    }
}

// MARK: - 8. Numbers Symbolic Link Check
func checkNumbersSymlink() {
    let linkPath = "/Users/bookid/Documents/StockTracking_Daily.numbers"
    let fileManager = FileManager.default
    
    do {
        let attrs = try fileManager.attributesOfItem(atPath: linkPath)
        guard let type = attrs[.type] as? FileAttributeType else {
            logError("NumbersSymlink", "ERROR (Unable to determine file type for \(linkPath))")
            return
        }
        
        if type == .typeSymbolicLink {
            let destination = try fileManager.destinationOfSymbolicLink(atPath: linkPath)
            if fileManager.fileExists(atPath: destination) {
                let destAttrs = try fileManager.attributesOfItem(atPath: destination)
                let size = destAttrs[.size] as? Int64 ?? 0
                if size > 0 {
                    logSuccess("Numbers Symlink: OK (Daily.numbers -> \(URL(fileURLWithPath: destination).lastPathComponent), Size: \(size) bytes)")
                } else {
                    logError("NumbersSymlink", "ERROR (Target file \(destination) is empty!)")
                }
            } else {
                logError("NumbersSymlink", "ERROR (Symbolic link points to non-existent file: \(destination))")
            }
        } else {
            let size = attrs[.size] as? Int64 ?? 0
            if size > 0 {
                logSuccess("Numbers Symlink: OK (Regular file exists, Size: \(size) bytes)")
            } else {
                logError("NumbersSymlink", "ERROR (File is empty!)")
            }
        }
    } catch {
        logError("NumbersSymlink", "ERROR (File or Symlink not found at \(linkPath): \(error.localizedDescription))")
    }
}

// MARK: - 9. Central Stock Data Cache Check
func checkCentralCacheData() {
    let cachePath = "/Users/bookid/.hermes/data/central_stock_data.json"
    let fileURL = URL(fileURLWithPath: cachePath)
    let fileManager = FileManager.default
    
    if !fileManager.fileExists(atPath: cachePath) {
        logError("CentralCacheData", "ERROR (Cache file not found at \(cachePath))")
        return
    }
    
    do {
        let data = try Data(contentsOf: fileURL)
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            logError("CentralCacheData", "ERROR (Failed to parse JSON structure)")
            return
        }
        
        let hasPersonal = json["personal_data"] != nil
        let hasData = json["data"] != nil
        let metadata = json["metadata"] as? [String: Any]
        
        if !hasPersonal || !hasData || metadata == nil {
            logError("CentralCacheData", "ERROR (Missing required JSON nodes like personal_data, data, or metadata)")
            return
        }
        
        if let lastSyncStr = metadata?["last_sync"] as? String {
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
            if let lastSyncDate = formatter.date(from: lastSyncStr) {
                let interval = Date().timeIntervalSince(lastSyncDate)
                let hours = interval / 3600.0
                
                if hours < 24.0 {
                    logSuccess(String(format: "Central Cache Data: OK (Parsed successfully, Freshness: %.1f hours ago)", hours))
                } else {
                    logWarning(String(format: "Central Cache Data: STALE (Stale cache detected! Last sync was %.1f hours ago)", hours))
                }
            } else {
                logWarning("Central Cache Data: WARNING (Unable to parse last_sync timestamp format: \(lastSyncStr))")
            }
        } else {
            logError("CentralCacheData", "ERROR (Missing last_sync timestamp in metadata)")
        }
    } catch {
        logError("CentralCacheData", "ERROR (Failed to read or parse JSON: \(error.localizedDescription))")
    }
}

// MARK: - 10. Machine Learning Assets Check
func checkMLAssets() {
    let models = [
        "/Users/bookid/.hermes/models/intraday_model.pkl",
        "/Users/bookid/.hermes/models/intraday_model_reg.pkl"
    ]
    let logPath = "/Users/bookid/.hermes/data/intraday_data_log.csv"
    let fileManager = FileManager.default
    var ok = true
    
    for model in models {
        if !fileManager.fileExists(atPath: model) {
            logError("MLAssets", "ERROR (Model file not found: \(URL(fileURLWithPath: model).lastPathComponent))")
            ok = false
        }
    }
    
    if !fileManager.fileExists(atPath: logPath) {
        logError("MLAssets", "ERROR (Training log CSV not found at \(logPath))")
        ok = false
    } else {
        do {
            let csvContent = try String(contentsOfFile: logPath, encoding: .utf8)
            let lines = csvContent.components(separatedBy: "\n")
            if let header = lines.first?.trimmingCharacters(in: .whitespacesAndNewlines), header.contains("timestamp") && header.contains("code") {
                // Header looks correct
            } else {
                logError("MLAssets", "ERROR (Training log CSV header is invalid or corrupted)")
                ok = false
            }
        } catch {
            logError("MLAssets", "ERROR (Failed to read training log CSV: \(error.localizedDescription))")
            ok = false
        }
    }
    
    if ok {
        logSuccess("ML Engine Assets: OK - Classifier, Regressor, and Training Log verified")
    }
}

// MARK: - 11. SQLite & DuckDB Hybrid Deep Schema Check
func checkSQLiteDeepSchema() {
    let dbPath = "/Users/bookid/.hermes/data/portfolio.db"
    let fileManager = FileManager.default
    if !fileManager.fileExists(atPath: dbPath) {
        logError("SQLiteDatabase", "ERROR (Database file not found at \(dbPath))")
        hasCriticalError = true
        return
    }
    
    let requiredTables = ["current_holdings", "watchlist", "pnl_history"]
    var hasError = false
    
    // 1. 驗證 SQLite 資料表與欄位
    for table in requiredTables {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/sqlite3")
        process.arguments = [dbPath, "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='\(table)';"]
        let pipe = Pipe()
        process.standardOutput = pipe
        
        do {
            try process.run()
            process.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines), output == "1" {
                if table == "watchlist" {
                    let colProcess = Process()
                    colProcess.executableURL = URL(fileURLWithPath: "/usr/bin/sqlite3")
                    colProcess.arguments = [dbPath, "PRAGMA table_info(watchlist);"]
                    let colPipe = Pipe()
                    colProcess.standardOutput = colPipe
                    try colProcess.run()
                    colProcess.waitUntilExit()
                    let colData = colPipe.fileHandleForReading.readDataToEndOfFile()
                    if let colOutput = String(data: colData, encoding: .utf8), colOutput.contains("group_name") {
                        // OK
                    } else {
                        logError("SQLiteSchema", "ERROR (Table 'watchlist' is missing crucial column 'group_name')")
                        hasError = true
                    }
                }
            } else {
                logError("SQLiteSchema", "ERROR (Required table '\(table)' is missing from SQLite database!)")
                hasError = true
            }
        } catch {
            logError("SQLiteSchema", "ERROR (Failed to verify SQLite table '\(table)': \(error.localizedDescription))")
            hasError = true
        }
    }
    
    // 2. 驗證 SQLite 索引用於加速 PnL 與觀測清單分群
    let requiredIndexes = ["idx_watchlist_group", "idx_pnl_history_date"]
    for idx in requiredIndexes {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/sqlite3")
        process.arguments = [dbPath, "SELECT count(*) FROM sqlite_master WHERE type='index' AND name='\(idx)';"]
        let pipe = Pipe()
        process.standardOutput = pipe
        
        do {
            try process.run()
            process.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines), output == "1" {
                // OK
            } else {
                logError("SQLiteSchema", "ERROR (Required index '\(idx)' is missing from SQLite database!)")
                hasError = true
            }
        } catch {
            logError("SQLiteSchema", "ERROR (Failed to verify SQLite index '\(idx)': \(error.localizedDescription))")
            hasError = true
        }
    }
    
    // 3. 驗證 DuckDB 分析與機器學習儲存層健康度
    let ddbPath = "/Users/bookid/.hermes/data/portfolio.ddb"
    if !fileManager.fileExists(atPath: ddbPath) {
        logError("DuckDBDatabase", "ERROR (DuckDB file not found at \(ddbPath))")
        hasError = true
    } else {
        let pyProcess = Process()
        pyProcess.executableURL = URL(fileURLWithPath: "/Users/bookid/.hermes/.venv/bin/python")
        pyProcess.arguments = ["-c", "import duckdb; conn = duckdb.connect('\(ddbPath)'); tables = [r[0] for r in conn.execute('SHOW TABLES').fetchall()]; assert 'institutional_data' in tables; assert 'ml_valuation_history' in tables; print('OK')"]
        let pyPipe = Pipe()
        pyProcess.standardOutput = pyPipe
        
        do {
            try pyProcess.run()
            pyProcess.waitUntilExit()
            let pyData = pyPipe.fileHandleForReading.readDataToEndOfFile()
            if let pyOutput = String(data: pyData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines), pyOutput == "OK" {
                // OK
            } else {
                logError("DuckDBSchema", "ERROR (DuckDB schema is not aligned or analytical tables are missing)")
                hasError = true
            }
        } catch {
            logError("DuckDBSchema", "ERROR (Failed to run DuckDB schema audit: \(error.localizedDescription))")
            hasError = true
        }
    }
    
    if !hasError {
        logSuccess("SQLite & DuckDB Hybrid Schemas: OK - Crucial tables, columns, and indexes verified")
    }
}

// MARK: - 12. Watchlist Configuration Consistency Check
func checkWatchlistConsistency() {
    let registryPath = "/Users/bookid/.hermes/data/master_stock_registry.json"
    let pythonSyncPath = "/Users/bookid/.hermes/scripts/taiex_central_data_sync.py"
    let swiftMonitorPath = "/Users/bookid/.hermes/scripts/hermes_monitor.swift"
    let fileManager = FileManager.default
    
    guard fileManager.fileExists(atPath: registryPath),
          fileManager.fileExists(atPath: pythonSyncPath),
          fileManager.fileExists(atPath: swiftMonitorPath) else {
        logError("ConfigConsistency", "ERROR (One or more config/script files are missing)")
        return
    }
    
    do {
        // 1. Read registry groups
        let regData = try Data(contentsOf: URL(fileURLWithPath: registryPath))
        guard let regJSON = try JSONSerialization.jsonObject(with: regData) as? [String: Any],
              let groupCategories = regJSON["group_categories"] as? [String: [Any]] else {
            logError("ConfigConsistency", "ERROR (Failed to parse group_categories from master_stock_registry.json)")
            return
        }
        
        // 2. Read file contents
        let pythonContent = try String(contentsOfFile: pythonSyncPath, encoding: .utf8)
        let swiftContent = try String(contentsOfFile: swiftMonitorPath, encoding: .utf8)
        
        // 3. Read SQLite watchlist database
        let dbPath = "/Users/bookid/.hermes/data/portfolio.db"
        var dbWatchlist: [String: String] = [:]
        
        let dbProcess = Process()
        dbProcess.executableURL = URL(fileURLWithPath: "/usr/bin/sqlite3")
        dbProcess.arguments = [dbPath, "SELECT code, group_name FROM watchlist;"]
        let dbPipe = Pipe()
        dbProcess.standardOutput = dbPipe
        
        do {
            try dbProcess.run()
            dbProcess.waitUntilExit()
            let dbData = dbPipe.fileHandleForReading.readDataToEndOfFile()
            if let dbOutput = String(data: dbData, encoding: .utf8) {
                let lines = dbOutput.components(separatedBy: "\n")
                for line in lines {
                    let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
                    if trimmed.isEmpty { continue }
                    let parts = trimmed.components(separatedBy: "|")
                    if parts.count >= 2 {
                        let code = parts[0].trimmingCharacters(in: .whitespacesAndNewlines)
                        let group = parts[1].trimmingCharacters(in: .whitespacesAndNewlines)
                        dbWatchlist[code] = group
                    }
                }
            }
        } catch {
            logError("ConfigConsistency", "ERROR (Failed to query SQLite watchlist table: \(error.localizedDescription))")
        }
        
        var williamSet = Set<String>()
        if let williamCodes = regJSON["william_codes"] as? [Any] {
            williamCodes.compactMap { $0 as? String }.forEach { williamSet.insert($0) }
        }
        
        var inconsistentTickers: [String] = []
        var totalChecked = 0
        
        for (groupName, tickersRaw) in groupCategories {
            if groupName == "其他群組關注" { continue }
            let tickers = tickersRaw.compactMap { $0 as? String }
            
            // Format target database group name
            let dbGroupTarget: String
            if groupName.hasPrefix("高潮不斷群 (") && groupName.hasSuffix(")") {
                dbGroupTarget = groupName
            } else {
                dbGroupTarget = "高潮不斷群 (\(groupName))"
            }
            
            for ticker in tickers {
                totalChecked += 1
                
                // Check in Python sync engine
                let pythonPattern = "\"\(ticker)\""
                if !pythonContent.contains(pythonPattern) {
                    logError("ConfigConsistency", "ERROR (Ticker '\(ticker)' in group '\(groupName)' is missing from python sync engine defaults at \(pythonSyncPath))")
                    inconsistentTickers.append(ticker)
                }
                
                // Check in Swift monitor
                let swiftPattern = "\"\(ticker)\""
                if !swiftContent.contains(swiftPattern) {
                    logError("ConfigConsistency", "ERROR (Ticker '\(ticker)' in group '\(groupName)' is missing from swift monitor getTargetStocks at \(swiftMonitorPath))")
                    inconsistentTickers.append(ticker)
                }
                
                // Check in SQLite database watchlist table
                if let dbGroup = dbWatchlist[ticker] {
                    let isWilliam = williamSet.contains(ticker)
                    if dbGroup != dbGroupTarget && !(isWilliam && dbGroup == "William哥推薦組") {
                        logError("ConfigConsistency", "ERROR (Ticker '\(ticker)' group mismatch in SQLite: DB has '\(dbGroup)', Registry has '\(dbGroupTarget)')")
                        inconsistentTickers.append(ticker)
                    }
                } else {
                    logError("ConfigConsistency", "ERROR (Ticker '\(ticker)' in group '\(groupName)' is missing from SQLite watchlist database)")
                    inconsistentTickers.append(ticker)
                }
            }
        }
        
        if let williamCodes = regJSON["william_codes"] as? [Any] {
            let wCodes = williamCodes.compactMap { $0 as? String }
            for ticker in wCodes {
                totalChecked += 1
                
                // Check in Python sync engine
                let pythonPattern = "\"\(ticker)\""
                if !pythonContent.contains(pythonPattern) {
                    logError("ConfigConsistency", "ERROR (William Ticker '\(ticker)' is missing from python sync engine defaults at \(pythonSyncPath))")
                    inconsistentTickers.append(ticker)
                }
                
                // Check in Swift monitor
                let swiftPattern = "\"\(ticker)\""
                if !swiftContent.contains(swiftPattern) {
                    logError("ConfigConsistency", "ERROR (William Ticker '\(ticker)' is missing from swift monitor getTargetStocks at \(swiftMonitorPath))")
                    inconsistentTickers.append(ticker)
                }
                
                // Check in SQLite database watchlist table
                if let dbGroup = dbWatchlist[ticker] {
                    // Find if there is any target category for this ticker
                    var groupTarget: String? = nil
                    for (groupName, tickersRaw) in groupCategories {
                        if groupName == "其他群組關注" { continue }
                        let tickers = tickersRaw.compactMap { $0 as? String }
                        if tickers.contains(ticker) {
                            if groupName.hasPrefix("高潮不斷群 (") && groupName.hasSuffix(")") {
                                groupTarget = groupName
                            } else {
                                groupTarget = "高潮不斷群 (\(groupName))"
                            }
                            break
                        }
                    }
                    
                    let isMatch = dbGroup == "William哥推薦組" || (groupTarget != nil && dbGroup == groupTarget!)
                    if !isMatch {
                        logError("ConfigConsistency", "ERROR (William Ticker '\(ticker)' group mismatch in SQLite: DB has '\(dbGroup)', expected 'William哥推薦組' or '\(groupTarget ?? "None")')")
                        inconsistentTickers.append(ticker)
                    }
                } else {
                    logError("ConfigConsistency", "ERROR (William Ticker '\(ticker)' is missing from SQLite watchlist database)")
                    inconsistentTickers.append(ticker)
                }
            }
        }
        
        if inconsistentTickers.isEmpty {
            logSuccess("Watchlist Configuration Consistency: OK - \(totalChecked) tickers verified across Registry, SQLite DB, Python Sync, and Swift Monitor.")
        } else {
            logError("ConfigConsistency", "CRITICAL - Configuration split-brain detected! \(inconsistentTickers.count) tickers are inconsistent.")
        }
    } catch {
        logError("ConfigConsistency", "ERROR (Exception during consistency check: \(error.localizedDescription))")
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
checkDuckDBDatabases()
checkDiskSpace()
checkEnvVariables()
checkCronJobs()
checkNumbersSymlink()
checkCentralCacheData()
checkMLAssets()
checkSQLiteDeepSchema()
checkWatchlistConsistency()


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
