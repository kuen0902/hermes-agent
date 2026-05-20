#!/usr/bin/swift
import Foundation

// MARK: - Configuration

struct ProfileConfig {
    let token: String
    let chatId: String
    let cacheFile: URL
    let openFile: URL
    let headerOpen: String
    let headerAlert: String
}

let homeDir = FileManager.default.homeDirectoryForCurrentUser
let dataDir = homeDir.appendingPathComponent(".hermes/data")

let PROFILES: [String: ProfileConfig] = [
    "personal": ProfileConfig(
        token: "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU",
        chatId: "6326497055",
        cacheFile: dataDir.appendingPathComponent("user_stock_last_prices.json"),
        openFile: dataDir.appendingPathComponent("user_day_open_report_sent.json"),
        headerOpen: "🎖️ **黃金體驗 - 09:00 開盤決報**",
        headerAlert: "⚖️ **白金之星 - 精密階梯波動警戒**"
    ),
    "william": ProfileConfig(
        token: "8678817340:AAHLd6ObYqUUTfygY-fPf57Rw6SfOO2WEGQ",
        chatId: "8695583357",
        cacheFile: dataDir.appendingPathComponent("william_stock_last_prices.json"),
        openFile: dataDir.appendingPathComponent("william_day_open_report_sent.json"),
        headerOpen: "🔷 **小智 (William) - 09:00 開盤快報**",
        headerAlert: "🔷 **小智 (William) - 階梯波動注意**"
    ),
    "group": ProfileConfig(
        token: "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU",
        chatId: "-1003744330314",
        cacheFile: dataDir.appendingPathComponent("group_stock_last_prices.json"),
        openFile: dataDir.appendingPathComponent("day_open_report_sent.json"),
        headerOpen: "☀️ **09:00 開盤即時戰報**",
        headerAlert: "⚡ **盤中階梯變動追蹤**"
    )
]

let CENTRAL_DATA_FILE = dataDir.appendingPathComponent("central_stock_data.json")
let TIERS: [Double] = [3.0, 5.0, 7.0, 9.0]

// MARK: - Logic Helpers

func getCurrentTier(pct: Double) -> Int {
    let absPct = abs(pct)
    var crossed = 0.0
    for t in TIERS {
        if absPct >= t {
            crossed = t
        }
    }
    return Int(crossed) * (pct >= 0 ? 1 : -1)
}

func sendTelegram(token: String, chatId: String, message: String) async -> Bool {
    let urlString = "https://api.telegram.org/bot\(token)/sendMessage"
    guard let url = URL(string: urlString) else { return false }
    
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
    
    var components = URLComponents()
    components.queryItems = [
        URLQueryItem(name: "chat_id", value: chatId),
        URLQueryItem(name: "text", value: message),
        URLQueryItem(name: "parse_mode", value: "Markdown")
    ]
    guard let query = components.percentEncodedQuery else { return false }
    request.httpBody = query.data(using: .utf8)
    
    do {
        let (data, response) = try await URLSession.shared.data(for: request)
        if let httpResponse = response as? HTTPURLResponse {
            if httpResponse.statusCode == 200 {
                return true
            } else {
                let respStr = String(data: data, encoding: .utf8) ?? ""
                print("Telegram Error (HTTP \(httpResponse.statusCode)): \(respStr)")
                return false
            }
        }
    } catch {
        print("Telegram Error: \(error.localizedDescription)")
    }
    return false
}

func getTargetStocks(profileName: String, centralStore: [String: Any]) -> [String: [String]] {
    if profileName == "personal" {
        if let personalData = centralStore["personal_data"] as? [String: Any] {
            let keys = Array(personalData.keys)
            return keys.isEmpty ? ["核心持股": ["2454", "3037", "2330"]] : ["核心持股": keys]
        }
        return ["核心持股": ["2454", "3037", "2330"]]
    } else if profileName == "william" {
        return ["William觀察名單": ["8996", "5289", "4966", "3583", "8210", "2327", "5347", "2402", "6510", "3211", "6290", "6669", "6147", "7828", "7815", "7769", "6877", "6683", "3709"]]
    } else if profileName == "group" {
        return [
            "Kim哥推薦組": ["1513", "2049", "5347", "6147", "3709"],
            "正體鍾文字組": ["2408", "2382", "2327"],
            "順風老師組": ["2313", "6285", "5289"],
            "進莫組": ["4543", "6125", "7828"],
            "大盤積分組": ["2330", "2454", "3037"]
        ]
    }
    return [:]
}

// Format double nicely
func formatDouble(_ value: Double) -> String {
    let formatter = NumberFormatter()
    formatter.numberStyle = .decimal
    formatter.minimumFractionDigits = 2
    formatter.maximumFractionDigits = 2
    return formatter.string(from: NSNumber(value: value)) ?? String(format: "%.2f", value)
}

func formatDoubleSign(_ value: Double) -> String {
    let formatter = NumberFormatter()
    formatter.numberStyle = .decimal
    formatter.positivePrefix = "+"
    formatter.minimumFractionDigits = 2
    formatter.maximumFractionDigits = 2
    return formatter.string(from: NSNumber(value: value)) ?? String(format: "%+.2f", value)
}

// MARK: - Main Runner

func run(profileName: String, captureOnly: Bool) async {
    guard let cfg = PROFILES[profileName] else {
        print("Invalid profile: \(profileName)")
        return
    }
    
    if !FileManager.default.fileExists(atPath: CENTRAL_DATA_FILE.path) {
        print("Central data file missing.")
        return
    }
    
    guard let centralDataBytes = try? Data(contentsOf: CENTRAL_DATA_FILE),
          let centralStore = try? JSONSerialization.jsonObject(with: centralDataBytes, options: []) as? [String: Any] else {
        print("Failed to parse central_stock_data.json")
        return
    }
    
    let mapping = centralStore["full_mapping"] as? [String: String] ?? [:]
    let marketData = centralStore["data"] as? [String: Any] ?? [:]
    let targetCategories = getTargetStocks(profileName: profileName, centralStore: centralStore)
    
    let now = Date()
    let formatter = DateFormatter()
    formatter.dateFormat = "yyyy-MM-dd"
    let todayStr = formatter.string(from: now)
    
    let calendar = Calendar.current
    let hour = calendar.component(.hour, from: now)
    let isOpening = hour >= 9 && hour <= 13
    
    // 1. OPENING REPORT LOGIC
    var openState: [String: Any] = [:]
    if let openData = try? Data(contentsOf: cfg.openFile),
       let parsed = try? JSONSerialization.jsonObject(with: openData, options: []) as? [String: Any] {
        openState = parsed
    }
    
    if isOpening && (openState["date"] as? String) != todayStr {
        let header = "\(cfg.headerOpen)\n📅 日期：`\(todayStr)`\n"
        var body = ""
        var currentCache: [String: Any] = [:]
        
        for (cat, codes) in targetCategories {
            if profileName == "group" { body += "\n📌 **\(cat)**\n" }
            for code in codes {
                guard let dataDict = marketData[code] as? [String: Any],
                      let price = dataDict["price"] as? Double,
                      let prev = dataDict["prev_close"] as? Double,
                      let sym = dataDict["symbol"] as? String else { continue }
                
                let openP = dataDict["open"] as? Double ?? price
                let pct = prev > 0 ? ((price - prev) / prev * 100) : 0
                
                currentCache[sym] = ["price": price, "tier": getCurrentTier(pct: pct)]
                
                let emoji = price > prev ? "🔴" : (price < prev ? "🟢" : "⚪")
                let name = mapping[code] ?? (dataDict["name_en"] as? String ?? code)
                body += "\(emoji) **\(name)**\n   ▸ 價：`\(formatDouble(price))` | 開：`\(formatDouble(openP))` | 昨收：`\(formatDouble(prev))` | 差：`\(formatDoubleSign(pct))%`\n"
            }
        }
        
        let reportContent = header + body
        if !captureOnly {
            if await sendTelegram(token: cfg.token, chatId: cfg.chatId, message: reportContent) {
                let newOpenState = ["date": todayStr]
                if let newData = try? JSONSerialization.data(withJSONObject: newOpenState, options: []),
                   let newCacheData = try? JSONSerialization.data(withJSONObject: currentCache, options: []) {
                    try? newData.write(to: cfg.openFile)
                    try? newCacheData.write(to: cfg.cacheFile)
                }
            }
        } else {
            print(reportContent)
        }
        return
    }
    
    // 2. TIERED MILESTONE MONITORING
    var lastCache: [String: Any] = [:]
    if let cacheData = try? Data(contentsOf: cfg.cacheFile),
       let parsed = try? JSONSerialization.jsonObject(with: cacheData, options: []) as? [String: Any] {
        lastCache = parsed
    }
    
    // Migrate legacy float dict
    for (k, v) in lastCache {
        if let vNum = v as? NSNumber {
            lastCache[k] = ["price": vNum.doubleValue, "tier": 0]
        }
    }
    
    var reportLines: [String] = []
    var currentCache = lastCache
    
    for (_, codes) in targetCategories {
        for code in codes {
            guard let dataDict = marketData[code] as? [String: Any],
                  let price = dataDict["price"] as? Double,
                  let prev = dataDict["prev_close"] as? Double,
                  let sym = dataDict["symbol"] as? String else { continue }
            
            let cached = lastCache[sym] as? [String: Any] ?? ["price": prev, "tier": 0]
            let lastTier = cached["tier"] as? Int ?? 0
            
            let pct = prev > 0 ? ((price - prev) / prev * 100) : 0
            let currentTier = getCurrentTier(pct: pct)
            
            if currentTier != 0 && currentTier != lastTier {
                let emoji = pct > 0 ? "🔴" : "🟢"
                let trend = abs(currentTier) > abs(lastTier) ? "🚀" : "📉"
                let name = mapping[code] ?? (dataDict["name_en"] as? String ?? code)
                
                let line = "\(emoji)\(trend) **\(name)** (`\(sym)`)\n   ▸ 現價：`\(formatDouble(price))` | 昨收比：`\(formatDoubleSign(pct))%` (突破 `\(currentTier)%` 門檻)\n"
                reportLines.append(line)
            }
            
            currentCache[sym] = ["price": price, "tier": currentTier]
        }
    }
    
    if !reportLines.isEmpty {
        let timeFormatter = DateFormatter()
        timeFormatter.dateFormat = "HH:mm"
        let ts = timeFormatter.string(from: now)
        
        let header = "\(cfg.headerAlert) (\(ts))\n💡 *條件：跨越 ±3%, ±5%, ±7%, ±9% 絕對里程碑*\n\n"
        let reportContent = header + reportLines.joined()
        
        if !captureOnly {
            if await sendTelegram(token: cfg.token, chatId: cfg.chatId, message: reportContent) {
                if let newCacheData = try? JSONSerialization.data(withJSONObject: currentCache, options: []) {
                    try? newCacheData.write(to: cfg.cacheFile)
                }
            }
        } else {
            print(reportContent)
        }
    } else {
        if captureOnly {
            print("[SILENT]")
        }
    }
}

// MARK: - Entry Point

let args = CommandLine.arguments
var profile: String? = nil
var reportOnly = false

var i = 1
while i < args.count {
    if args[i] == "--profile", i + 1 < args.count {
        profile = args[i + 1]
        i += 1
    } else if args[i] == "--report-only" {
        reportOnly = true
    }
    i += 1
}

guard let p = profile else {
    print("Usage: ./hermes_monitor.swift --profile <personal|william|group> [--report-only]")
    exit(1)
}

let dispatchGroup = DispatchGroup()
dispatchGroup.enter()
Task {
    await run(profileName: p, captureOnly: reportOnly)
    dispatchGroup.leave()
}
dispatchGroup.wait()
