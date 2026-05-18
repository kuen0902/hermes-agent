#!/usr/bin/env swift
import Foundation
import AppKit

// MARK: - Configuration
// CHAOS TESTING: This comment makes the source newer than the binary!
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
    let stock_private_flag: Bool
    let data: [String: StockData]
}

// MARK: - Numbers AppleScript
func fetchPortfolio() async -> [String: PortfolioItem] {
    var portfolio = [String: PortfolioItem]()
    print("Fetching personal portfolio from SQLite (portfolio_tool.py)...")
    
    let portTask = Process()
    portTask.executableURL = URL(fileURLWithPath: "/Users/bookid/.hermes/.venv/bin/python")
    portTask.arguments = ["/Users/bookid/.hermes/scripts/portfolio_tool.py", "--export-json"]
    let portOutPipe = Pipe()
    portTask.standardOutput = portOutPipe
    
    do {
        try portTask.run()
        portTask.waitUntilExit()
        let portData = portOutPipe.fileHandleForReading.readDataToEndOfFile()
        if let json = try JSONSerialization.jsonObject(with: portData) as? [String: Any] {
            for (code, infoRaw) in json {
                if let info = infoRaw as? [String: Any],
                   let name = info["name"] as? String,
                   let qty = info["qty"] as? Double,
                   let avg = info["avg"] as? Double {
                    portfolio[code] = PortfolioItem(name: name, qty: qty, avg: avg)
                }
            }
            print("✓ 成功從 SQLite 載入 \(portfolio.count) 檔持股。")
        }
    } catch {
        print("⚠️ 無法載入 SQLite 持股資料: \(error)")
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
    var personalData = await fetchPortfolio()
    let t1 = CFAbsoluteTimeGetCurrent()
    print("✓ SQLite (portfolio_tool.py) 讀取時間: \(String(format: "%.2fs", t1 - t0))")
    
    if personalData.isEmpty {
        let cacheUrl = URL(fileURLWithPath: CACHE_FILE)
        if let data = try? Data(contentsOf: cacheUrl),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let existingPersonal = json["personal_data"] as? [String: Any] {
            
            for (code, infoObj) in existingPersonal {
                if let info = infoObj as? [String: Any],
                   let name = info["name"] as? String {
                   let qty = info["qty"] as? Double ?? 0.0
                   let avg = info["avg"] as? Double ?? 0.0
                   personalData[code] = PortfolioItem(name: name, qty: qty, avg: avg)
                }
            }
            print("⚠️ AppleScript returned empty or timed out. Restored \(personalData.count) personal stocks from cache.")
        }
    }
    
    // Read from master_stock_registry.json
    let registryUrl = URL(fileURLWithPath: "/Users/bookid/.hermes/data/master_stock_registry.json")
    var williamDefaults = [String: String]()
    var groupDefaults = [String: String]()
    var extraStocks = [String: String]()
    var officialNames = [String: String]()
    
    if let data = try? Data(contentsOf: registryUrl),
       let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
        
        if let names = json["official_names"] as? [String: String] {
            officialNames = names
        }
        
        if let wCodes = json["william_codes"] as? [String] {
            wCodes.forEach { williamDefaults[$0] = officialNames[$0] ?? $0 }
        }
        
        if let gCats = json["group_categories"] as? [String: [String]] {
            for (_, codes) in gCats {
                codes.forEach { groupDefaults[$0] = officialNames[$0] ?? $0 }
            }
        }
        
        if let eCodes = json["extra_codes"] as? [String] {
            eCodes.forEach { extraStocks[$0] = officialNames[$0] ?? $0 }
        }
    } else {
        print("⚠️ Failed to load master_stock_registry.json")
    }
    
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
        stock_private_flag: true,
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
