#!/usr/bin/env swift
import Foundation
import AppKit

// MARK: - Configuration
let homeDir = FileManager.default.homeDirectoryForCurrentUser.path
let NUMBERS_PATH = "\(homeDir)/Documents/StockTracking_Daily.numbers"
let CACHE_FILE = "\(homeDir)/.hermes/data/central_stock_data.json"
let HISTORY_LOG_FILE = "\(homeDir)/.hermes/data/intraday_data_log.csv"

// MARK: - Models
struct StockData: Codable {
    let symbol: String
    let price: Double
    let volume: Int
    let prev_close: Double
    let change: Double
    let pct: Double
    let time: String
}

struct PortfolioItem: Codable {
    let name: String
    let qty: Double
    let avg: Double
}

struct OutputMetadata: Codable {
    let last_sync: String
    let status: String
    let total_requested: Int
    let total_fetched: Int
}

struct OutputJSON: Codable {
    let metadata: OutputMetadata
    let personal_data: [String: PortfolioItem]
    let william_codes: [String]
    let group_codes: [String]
    let full_mapping: [String: String]
    let data: [String: StockData]
}

// MARK: - Numbers AppleScript
func getPersonalTickers() -> [String: PortfolioItem] {
    var portfolio = [String: PortfolioItem]()
    
    // Check if Numbers is running via pgrep
    let task = Process()
    task.executableURL = URL(fileURLWithPath: "/usr/bin/pgrep")
    task.arguments = ["Numbers"]
    
    let pipe = Pipe()
    task.standardOutput = pipe
    
    var isNumbersRunning = false
    do {
        try task.run()
        task.waitUntilExit()
        isNumbersRunning = task.terminationStatus == 0
    } catch {
        print("Failed to check if Numbers is running.")
    }
    
    if !isNumbersRunning {
        print("Numbers is not running. Attempting to open...")
        let openTask = Process()
        openTask.executableURL = URL(fileURLWithPath: "/usr/bin/open")
        openTask.arguments = [NUMBERS_PATH]
        do {
            try openTask.run()
        } catch {}
        print("Waiting 5 seconds for Numbers to launch and load the document...")
        Thread.sleep(forTimeInterval: 5.0)
    }
    
    let scriptString = """
    tell application "Numbers"
        set docPath to POSIX file "\(NUMBERS_PATH)"
        open docPath
        
        set targetDoc to missing value
        repeat with i from 1 to 10
            set allDocs to name of every document
            repeat with d in allDocs
                if d starts with "StockTracking" then
                    set targetDoc to d
                    exit repeat
                end if
            end repeat
            
            if targetDoc is not missing value then
                exit repeat
            end if
            delay 0.5
        end repeat
        
        if targetDoc is missing value then
            return "ERROR: Document not found or not loaded in time"
        end if
        
        set outputStr to ""
        tell document targetDoc to tell sheet "Portfolio" to tell table 1
            set rCount to row count
            if rCount > 200 then set rCount to 200
            
            repeat with i from 2 to rCount
                set code to value of cell 1 of row i
                if code is not missing value and code is not "" then
                    try
                        set nameVal to value of cell 2 of row i
                        set qtyVal to value of cell 3 of row i
                        set avgVal to value of cell 5 of row i
                        if nameVal is missing value then set nameVal to ""
                        if qtyVal is missing value then set qtyVal to 0
                        if avgVal is missing value then set avgVal to 0
                        set outputStr to outputStr & code & tab & nameVal & tab & qtyVal & tab & avgVal & linefeed
                    end try
                end if
            end repeat
        end tell
        return outputStr
    end tell
    """
    
    let osaTask = Process()
    osaTask.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
    osaTask.arguments = ["-e", scriptString]
    
    let outPipe = Pipe()
    let errPipe = Pipe()
    osaTask.standardOutput = outPipe
    osaTask.standardError = errPipe
    
    do {
        try osaTask.run()
        osaTask.waitUntilExit()
        
        let outData = outPipe.fileHandleForReading.readDataToEndOfFile()
        let errData = errPipe.fileHandleForReading.readDataToEndOfFile()
        
        if osaTask.terminationStatus == 0 {
            if let output = String(data: outData, encoding: .utf8) {
                if output.hasPrefix("ERROR:") {
                    print("Numbers Fetch Error (AppleScript): \\(output.trimmingCharacters(in: .whitespacesAndNewlines))")
                } else {
                    let lines = output.components(separatedBy: "\n")
                    for line in lines {
                        let parts = line.components(separatedBy: "\t")
                        if parts.count >= 4 {
                            var code = parts[0].trimmingCharacters(in: .whitespacesAndNewlines).replacingOccurrences(of: "'", with: "")
                            if code.contains("."), code.hasSuffix(".0") {
                                code = String(code.split(separator: ".")[0])
                            }
                            
                            let rawName = parts[1].trimmingCharacters(in: .whitespacesAndNewlines)
                            let cleanName = rawName.replacingOccurrences(of: "\u{1B}\\[[0-9;]*m", with: "", options: .regularExpression)
                            
                            let qtyStr = parts[2]
                            let avgStr = parts[3]
                            
                            let qty = (qtyStr != "missing value" && !qtyStr.isEmpty) ? (Double(qtyStr) ?? 0.0) : 0.0
                            let avg = (avgStr != "missing value" && !avgStr.isEmpty) ? (Double(avgStr) ?? 0.0) : 0.0
                            
                            portfolio[code] = PortfolioItem(name: cleanName, qty: qty, avg: avg)
                        }
                    }
                }
            }
        } else {
            let errorStr = String(data: errData, encoding: .utf8) ?? "Unknown error"
            print("Numbers Fetch Error (Exit \(osaTask.terminationStatus)): \(errorStr)")
        }
    } catch {
        print("Failed to run osascript: \(error)")
    }
    
    return portfolio
}

// MARK: - Date Formatting
func currentISO8601() -> String {
    let formatter = DateFormatter()
    formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
    return formatter.string(from: Date())
}

func currentCSVTime() -> String {
    let formatter = DateFormatter()
    formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
    return formatter.string(from: Date())
}

// MARK: - TWSE API
func fetchTWSE(codes: [String]) async -> [String: StockData] {
    var results = [String: StockData]()
    
    // Group into chunks of 50
    let chunkSize = 50
    var chunks = [[String]]()
    for i in stride(from: 0, to: codes.count, by: chunkSize) {
        let end = min(i + chunkSize, codes.count)
        chunks.append(Array(codes[i..<end]))
    }
    
    let session = URLSession.shared
    
    for chunk in chunks {
        var queryItems = [String]()
        for code in chunk {
            queryItems.append("tse_\(code).tw")
            queryItems.append("otc_\(code).tw")
        }
        
        let query = queryItems.joined(separator: "|")
        let urlString = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=\(query)&json=1&delay=0"
        
        guard let url = URL(string: urlString) else { continue }
        
        do {
            let (data, _) = try await session.data(from: url)
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let msgArray = json["msgArray"] as? [[String: Any]] {
                
                for item in msgArray {
                    guard let code = item["c"] as? String else { continue }
                    
                    let ex = item["ex"] as? String ?? "tse"
                    let symbol = ex == "tse" ? "\(code).TW" : "\(code).TWO"
                    
                    var priceStr = item["z"] as? String ?? "-"
                    if priceStr == "-" { priceStr = item["pz"] as? String ?? "-" }
                    if priceStr == "-" { priceStr = item["o"] as? String ?? "-" }
                    
                    guard let price = Double(priceStr) else { continue }
                    
                    let yStr = item["y"] as? String ?? priceStr
                    let yclose = Double(yStr) ?? price
                    
                    let vStr = item["v"] as? String ?? "0"
                    let volume = Int(vStr) ?? 0
                    
                    let change = price - yclose
                    let pct = yclose != 0 ? (change / yclose * 100) : 0
                    
                    if results[code] == nil {
                        results[code] = StockData(
                            symbol: symbol,
                            price: price,
                            volume: volume,
                            prev_close: yclose,
                            change: change,
                            pct: pct,
                            time: currentISO8601()
                        )
                    }
                }
            }
        } catch {
            print("TWSE API Fetch Error: \(error.localizedDescription)")
        }
    }
    return results
}

// MARK: - Yahoo Finance Fallback
func fetchYFinanceFallback(codes: [String]) async -> [String: StockData] {
    var results = [String: StockData]()
    let session = URLSession.shared
    
    // Concurrent fetch using TaskGroup
    await withTaskGroup(of: (String, StockData?).self) { group in
        for code in codes {
            group.addTask {
                for suffix in [".TW", ".TWO"] {
                    let sym = "\(code)\(suffix)"
                    let urlString = "https://query1.finance.yahoo.com/v8/finance/chart/\(sym)?range=2d&interval=1d"
                    guard let url = URL(string: urlString) else { continue }
                    
                    do {
                        let (data, _) = try await session.data(from: url)
                        if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                           let chart = json["chart"] as? [String: Any],
                           let resultArr = chart["result"] as? [[String: Any]],
                           let firstResult = resultArr.first,
                           let indicators = firstResult["indicators"] as? [String: Any],
                           let quote = indicators["quote"] as? [[String: Any]],
                           let firstQuote = quote.first,
                           let closes = firstQuote["close"] as? [Double?],
                           let volumes = firstQuote["volume"] as? [Int?] {
                            
                            let validCloses = closes.compactMap { $0 }
                            let validVolumes = volumes.compactMap { $0 }
                            
                            if !validCloses.isEmpty {
                                let price = validCloses.last!
                                let prev = validCloses.count > 1 ? validCloses.first! : price
                                let volume = validVolumes.last ?? 0
                                
                                let change = price - prev
                                let pct = prev != 0 ? (change / prev * 100) : 0
                                
                                let stockData = StockData(
                                    symbol: sym,
                                    price: price,
                                    volume: volume,
                                    prev_close: prev,
                                    change: change,
                                    pct: pct,
                                    time: currentISO8601()
                                )
                                return (code, stockData)
                            }
                        }
                    } catch {
                        continue
                    }
                }
                return (code, nil)
            }
        }
        
        for await (code, stockData) in group {
            if let data = stockData {
                results[code] = data
            }
        }
    }
    
    return results
}

// MARK: - CSV Logger
func logToCSV(data: [String: StockData], mapping: [String: String]) {
    let fileManager = FileManager.default
    let url = URL(fileURLWithPath: HISTORY_LOG_FILE)
    
    do {
        let dir = url.deletingLastPathComponent()
        try fileManager.createDirectory(at: dir, withIntermediateDirectories: true)
        
        let fileExists = fileManager.fileExists(atPath: url.path)
        let now = currentCSVTime()
        var csvString = ""
        
        if !fileExists {
            csvString += "timestamp,code,name,price,volume,pct_change\n"
        }
        
        for (code, info) in data {
            let name = mapping[code] ?? "Unknown"
            csvString += "\(now),\(code),\(name),\(info.price),\(info.volume),\(String(format: "%.4f", info.pct))\n"
        }
        
        if fileExists {
            let handle = try FileHandle(forWritingTo: url)
            handle.seekToEndOfFile()
            if let d = csvString.data(using: .utf8) {
                handle.write(d)
            }
            handle.closeFile()
        } else {
            try csvString.write(to: url, atomically: true, encoding: .utf8)
        }
    } catch {
        print("CSV Log Error: \(error.localizedDescription)")
    }
}

// MARK: - Main Execution
func sync() async {
    let startTime = CFAbsoluteTimeGetCurrent()
    print("Starting Central Stock Data Sync (Swift Native Engine)...")
    let t0 = CFAbsoluteTimeGetCurrent()
    let personalData = getPersonalTickers()
    let t1 = CFAbsoluteTimeGetCurrent()
    print("✓ Numbers AppleScript Time: \(String(format: "%.2fs", t1 - t0))")
    
    let williamDefaults: [String: String] = [
        "8996": "高力", "5289": "宜鼎", "4966": "譜瑞", "3583": "辛耘", 
        "8210": "勤誠", "2327": "國巨", "5347": "世界", "2402": "毅嘉", 
        "6510": "精測", "3211": "順達", "6290": "良維", "6669": "緯穎", 
        "6147": "頎邦", "7828": "創新服務", "7815": "家登自動", "7769": "進能服", 
        "6877": "鏵友益", "6683": "雍智科技", "3709": "鑫聯大"
    ]
    let groupDefaults: [String: String] = [
        "1513": "中興電", "2049": "上銀", "5347": "世界", "6147": "頎邦", "3709": "鑫聯大",
        "2408": "南亞科", "2382": "廣達", "2327": "國巨",
        "2313": "華通", "6285": "啟碁", "5289": "宜鼎",
        "4543": "萬在", "6125": "廣運", "7828": "創新服務",
        "2330": "台積電", "2454": "聯發科", "3037": "欣興"
    ]
    let extraStocks: [String: String] = [
        "0050": "元大台灣50",
        "0052": "富邦科技",
        "00981A": "中信優息投資級債",
        "00965": "元大高股息",
        "2002": "中鋼",
        "2344": "華邦電",
        "2368": "金像電",
        "2413": "環科",
        "3260": "威剛",
        "1802": "台玻"
    ]
    
    var allCodesSet = Set<String>()
    personalData.keys.forEach { allCodesSet.insert($0) }
    williamDefaults.keys.forEach { allCodesSet.insert($0) }
    groupDefaults.keys.forEach { allCodesSet.insert($0) }
    extraStocks.keys.forEach { allCodesSet.insert($0) }
    
    let allCodes = Array(allCodesSet)
    
    var mapping: [String: String] = williamDefaults
    groupDefaults.forEach { mapping[$0.key] = $0.value }
    extraStocks.forEach { mapping[$0.key] = $0.value }
    for (code, info) in personalData {
        if mapping[code] == nil { mapping[code] = info.name }
    }
    
    print("Tracking \(allCodes.count) unique stocks.")
    
    // Fetch TWSE
    let t2 = CFAbsoluteTimeGetCurrent()
    var marketData = await fetchTWSE(codes: allCodes)
    let t3 = CFAbsoluteTimeGetCurrent()
    print("✓ TWSE API Fetch Time: \(String(format: "%.2fs", t3 - t2))")
    
    // Check Failures
    let failedCodes = allCodes.filter { marketData[$0] == nil }
    if !failedCodes.isEmpty {
        print("Attempting YFinance fallback for: \(failedCodes.joined(separator: ", "))")
        let t4 = CFAbsoluteTimeGetCurrent()
        let fallbackData = await fetchYFinanceFallback(codes: failedCodes)
        let t5 = CFAbsoluteTimeGetCurrent()
        print("✓ YFinance API Fetch Time: \(String(format: "%.2fs", t5 - t4))")
        for (k, v) in fallbackData {
            marketData[k] = v
        }
    }
    
    for code in allCodes {
        if let res = marketData[code] {
            let pctStr = res.pct >= 0 ? String(format: "+%.2f%%", res.pct) : String(format: "%.2f%%", res.pct)
            print("Done: \(code) -> \(res.price) (\(pctStr))")
        } else {
            print("Failed: \(code)")
        }
    }
    
    logToCSV(data: marketData, mapping: mapping)
    
    let healthyCount = marketData.count
    let status = healthyCount > Int(Double(allCodes.count) * 0.8) ? "Healthy" : "Degraded"
    
    let metadata = OutputMetadata(
        last_sync: currentISO8601(),
        status: status,
        total_requested: allCodes.count,
        total_fetched: healthyCount
    )
    
    let outputJSON = OutputJSON(
        metadata: metadata,
        personal_data: personalData,
        william_codes: Array(williamDefaults.keys),
        group_codes: Array(groupDefaults.keys),
        full_mapping: mapping,
        data: marketData
    )
    
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .withoutEscapingSlashes]
    
    do {
        let jsonData = try encoder.encode(outputJSON)
        let cacheUrl = URL(fileURLWithPath: CACHE_FILE)
        let dir = cacheUrl.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try jsonData.write(to: cacheUrl)
        let timeElapsed = CFAbsoluteTimeGetCurrent() - startTime
        print(String(format: "Sync Complete: %d stocks updated. Status: %@. Process Time: %.2fs", healthyCount, status, timeElapsed))
    } catch {
        print("JSON Serialization Error: \(error.localizedDescription)")
    }
}

// MARK: - Entry Point
Task {
    await sync()
    exit(0)
}
RunLoop.main.run()
