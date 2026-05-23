#!/usr/bin/swift
import Foundation

// 設定檔路徑
let homeDir = FileManager.default.homeDirectoryForCurrentUser
let dataDir = homeDir.appendingPathComponent(".hermes/data")
let pnlSummaryFile = dataDir.appendingPathComponent("pnl_summary_today.json")
let pnlCurveFile = dataDir.appendingPathComponent("pnl_curve.png")

// Telegram 參數 (Star Platinum)
let token = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
let chatId = "6326497055"

// 📌 純文字發送 (備援降級方案)
func sendTelegramText(message: String) async {
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
            print("❌ [備援方案] 發送純文字失敗 (HTTP \(httpResponse.statusCode)): \(respStr)")
        } else {
            print("✅ [備援方案] 損益文字報表發送成功！")
        }
    } catch {
        print("❌ [備援方案] 網路連線錯誤: \(error.localizedDescription)")
    }
}

// 📌 圖片與說明文字一體發送 (核心高質感方案)
func sendTelegramPhoto(photoURL: URL, message: String) async -> Bool {
    let urlString = "https://api.telegram.org/bot\(token)/sendPhoto"
    guard let url = URL(string: urlString) else { return false }
    
    let boundary = "Boundary-\(UUID().uuidString)"
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
    
    var body = Data()
    
    // 1. chat_id
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"chat_id\"\r\n\r\n".data(using: .utf8)!)
    body.append("\(chatId)\r\n".data(using: .utf8)!)
    
    // 2. caption (Markdown 格式)
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"caption\"\r\n\r\n".data(using: .utf8)!)
    body.append("\(message)\r\n".data(using: .utf8)!)
    
    // 3. parse_mode
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"parse_mode\"\r\n\r\n".data(using: .utf8)!)
    body.append("Markdown\r\n".data(using: .utf8)!)
    
    // 4. photo 檔案二進制數據
    do {
        let photoData = try Data(contentsOf: photoURL)
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"photo\"; filename=\"pnl_curve.png\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/png\r\n\r\n".data(using: .utf8)!)
        body.append(photoData)
        body.append("\r\n".data(using: .utf8)!)
    } catch {
        print("❌ 讀取圖片檔案失敗: \(error.localizedDescription)")
        return false
    }
    
    body.append("--\(boundary)--\r\n".data(using: .utf8)!)
    request.httpBody = body
    
    do {
        let (data, response) = try await URLSession.shared.data(for: request)
        if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode != 200 {
            let respStr = String(data: data, encoding: .utf8) ?? ""
            print("❌ 圖片發送失敗 (HTTP \(httpResponse.statusCode)): \(respStr)")
            return false
        } else {
            print("✅ 損益圖表與明細發送成功！")
            return true
        }
    } catch {
        print("❌ 圖片發送網路連線錯誤: \(error.localizedDescription)")
        return false
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
    
    var msg = "📊 **Hermes 手動交易損益總結 (\(dateStr))**\n"
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
    
    if let topTrades = report["top_3_trades"] as? [[String: Any]], !topTrades.isEmpty {
        msg += "\n🔥 **歷史手動交易最強損益 Top 3**：\n"
        for t in topTrades {
            let name = t["name"] as? String ?? "Unknown"
            let code = t["code"] as? String ?? "Unknown"
            let pnl = t["pnl"] as? Double ?? 0.0
            let returnPct = t["return_pct"] as? Double ?? 0.0
            let icon = pnl >= 0 ? "🔴" : "🟢"
            let sign = pnl > 0 ? "+" : ""
            let pctSign = returnPct > 0 ? "+" : ""
            msg += "▸ \(name) (`\(code)`): \(icon) `\(sign)\(formatCurrency(pnl))` 元 (\(pctSign)\(String(format: "%.2f", returnPct))%)\n"
        }
    }
    
    // 檢查是否有損益曲線圖片，有的話優先發送圖片，無則降級純文字
    if FileManager.default.fileExists(atPath: pnlCurveFile.path) {
        let success = await sendTelegramPhoto(photoURL: pnlCurveFile, message: msg)
        if !success {
            print("⚠️ 圖片推送失敗，自動啟動備援純文字發送...")
            await sendTelegramText(message: msg)
        }
    } else {
        print("⚠️ 未檢測到損益曲線圖 \(pnlCurveFile.path)，使用純文字發送。")
        await sendTelegramText(message: msg)
    }
}

// 執行
let dispatchGroup = DispatchGroup()
dispatchGroup.enter()
Task {
    await generateAndSendReport()
    dispatchGroup.leave()
}
dispatchGroup.wait()
