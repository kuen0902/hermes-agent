#!/usr/bin/swift
import Foundation

// 設定檔路徑
let homeDir = FileManager.default.homeDirectoryForCurrentUser
let dataDir = homeDir.appendingPathComponent(".hermes/data")
let pnlSummaryFile = dataDir.appendingPathComponent("pnl_summary_today.json")

// Telegram 參數 (Star Platinum)
let token = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
let chatId = "6326497055"

func sendTelegram(message: String) async {
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
        if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode != 200 {
            let respStr = String(data: data, encoding: .utf8) ?? ""
            print("❌ 發送失敗 (HTTP \(httpResponse.statusCode)): \(respStr)")
        } else {
            print("✅ 損益報表發送成功！")
        }
    } catch {
        print("❌ 網路連線錯誤: \(error.localizedDescription)")
    }
}

func formatCurrency(_ value: Double) -> String {
    let formatter = NumberFormatter()
    formatter.numberStyle = .decimal
    formatter.maximumFractionDigits = 0
    return formatter.string(from: NSNumber(value: value)) ?? "\(Int(value))"
}

// 主程式邏輯
func generateAndSendReport() async {
    guard let jsonData = try? Data(contentsOf: pnlSummaryFile),
          let report = try? JSONSerialization.jsonObject(with: jsonData, options: []) as? [String: Any] else {
        print("⚠️ 找不到 pnl_summary_today.json 或格式錯誤，無法發送報表。")
        return
    }
    
    let dateStr = report["date"] as? String ?? ""
    let todayTotal = report["today_total_pnl"] as? Double ?? 0.0
    let histTotal = report["historical_total_pnl"] as? Double ?? 0.0
    
    let todayIcon = todayTotal >= 0 ? "🔴" : "🟢"
    let todaySign = todayTotal > 0 ? "+" : ""
    
    var msg = "📊 **Hermes 盤後損益總結 (\(dateStr))**\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += "💰 **今日已實現損益**：\(todayIcon) `\(todaySign)\(formatCurrency(todayTotal))` 元\n"
    
    if let trades = report["trades"] as? [[String: Any]], !trades.isEmpty {
        msg += "\n📝 **今日交易明細**：\n"
        for t in trades {
            let name = t["name"] as? String ?? "Unknown"
            let code = t["code"] as? String ?? "Unknown"
            let pnl = t["pnl"] as? Double ?? 0.0
            let qty = t["qty"] as? Double ?? 0.0
            let icon = pnl >= 0 ? "🔴" : "🟢"
            let sign = pnl > 0 ? "+" : ""
            msg += "▸ \(name) (`\(code)`) \(Int(qty))張: \(icon) `\(sign)\(formatCurrency(pnl))`\n"
        }
    } else {
        msg += "\n📝 **今日交易明細**：今日無任何平倉紀錄。\n"
    }
    
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    let histIcon = histTotal >= 0 ? "🔴" : "🟢"
    let histSign = histTotal > 0 ? "+" : ""
    msg += "🏆 **歷史總已實現損益**：\(histIcon) `\(histSign)\(formatCurrency(histTotal))` 元\n"
    
    await sendTelegram(message: msg)
}

// 執行
let dispatchGroup = DispatchGroup()
dispatchGroup.enter()
Task {
    await generateAndSendReport()
    dispatchGroup.leave()
}
dispatchGroup.wait()
