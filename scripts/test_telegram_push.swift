#!/usr/bin/swift
import Foundation

// 讀取正式環境的設定
let homeDir = FileManager.default.homeDirectoryForCurrentUser
let dataDir = homeDir.appendingPathComponent(".hermes/data")
let centralDataFile = dataDir.appendingPathComponent("central_stock_data.json")

// 您個人專屬的 Bot Token 與 Chat ID
let token = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
let chatId = "6326497055" 

func sendTelegram(message: String) async {
    print("📡 正在嘗試透過 Swift 原生 URLSession 發送測試電報...")
    let urlString = "https://api.telegram.org/bot\(token)/sendMessage"
    guard let url = URL(string: urlString) else { return }
    
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
    
    var components = URLComponents()
    components.queryItems = [
        URLQueryItem(name: "chat_id", value: chatId),
        URLQueryItem(name: "text", value: message),
        URLQueryItem(name: "parse_mode", value: "Markdown")
    ]
    
    guard let query = components.percentEncodedQuery else { return }
    request.httpBody = query.data(using: .utf8)
    
    do {
        let (data, response) = try await URLSession.shared.data(for: request)
        if let httpResponse = response as? HTTPURLResponse {
            if httpResponse.statusCode == 200 {
                print("✅ 測試成功！請檢查您的 Telegram 手機 APP，應該已經收到來自【白金之星】的訊息了。")
            } else {
                let respStr = String(data: data, encoding: .utf8) ?? ""
                print("❌ 發送失敗 (HTTP \(httpResponse.statusCode)): \(respStr)")
            }
        }
    } catch {
        print("❌ 網路連線錯誤: \(error.localizedDescription)")
    }
}

// 產生測試訊息：抓取一檔您的核心持股來假裝發送
var testMessage = "⚠️ **【強制覆寫測試 V2】** ⚠️\n\n"
testMessage += "🎖️ **白金之星 - Swift 引擎通訊測試** 🎖️\n\n"
testMessage += "這是第二波由 Swift 原生發出的非同步電報測試！\n\n"

if let centralDataBytes = try? Data(contentsOf: centralDataFile),
   let centralStore = try? JSONSerialization.jsonObject(with: centralDataBytes, options: []) as? [String: Any],
   let marketData = centralStore["data"] as? [String: Any],
   let tsm = marketData["2330"] as? [String: Any],
   let price = tsm["price"] as? Double,
   let prev = tsm["prev_close"] as? Double {
   
   let pct = ((price - prev) / prev) * 100
   let sign = pct >= 0 ? "+" : ""
   testMessage += "🔎 **隨機抽取連線資料**：\n"
   testMessage += "台積電 (2330) 目前系統價格：`\(price)`\n"
   testMessage += "單日漲跌幅：`\(sign)\(String(format: "%.2f", pct))%`\n\n"
}

testMessage += "💡 如果您看到這則訊息，代表未來的盤中推播都能在 0.1 秒內送達您的手機！"

let dispatchGroup = DispatchGroup()
dispatchGroup.enter()
Task {
    await sendTelegram(message: testMessage)
    dispatchGroup.leave()
}
dispatchGroup.wait()
