#!/usr/bin/swift
import Foundation

let fm = FileManager.default
let homeDir = fm.homeDirectoryForCurrentUser
let scriptsDir = homeDir.appendingPathComponent(".hermes/scripts")
let documentsDir = homeDir.appendingPathComponent("Documents")

func runScript(name: String, args: [String] = []) {
    let scriptPath = scriptsDir.appendingPathComponent(name).path
    let argsString = args.joined(separator: " ")
    print("--- Executing \(name) \(argsString) ---")
    
    let process = Process()
    
    if name.hasSuffix(".swift") {
        process.executableURL = URL(fileURLWithPath: scriptPath)
        process.arguments = args
    } else {
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["/Users/bookid/.hermes/.venv/bin/python", scriptPath] + args
    }
    
    let pipe = Pipe()
    process.standardOutput = pipe
    process.standardError = pipe
    
    do {
        try process.run()
        process.waitUntilExit()
        
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        if let output = String(data: data, encoding: .utf8) {
            let trimmed = output.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty {
                print(trimmed)
            }
        }
    } catch {
        print("Failed to run \(name): \(error.localizedDescription)")
    }
}

func syncNumbersFilename() {
    let now = Date()
    let formatter = DateFormatter()
    formatter.dateFormat = "yyyy-MM-dd"
    let todayStr = formatter.string(from: now)
    
    let targetFile = documentsDir.appendingPathComponent("StockTracking_\(todayStr).numbers")
    let linkPath = documentsDir.appendingPathComponent("StockTracking_Daily.numbers")
    
    print("--- Syncing Numbers Filename for \(todayStr) ---")
    
    if !fm.fileExists(atPath: targetFile.path) {
        do {
            let files = try fm.contentsOfDirectory(atPath: documentsDir.path)
            let trackingFiles = files.filter { $0.hasPrefix("StockTracking_20") && $0.hasSuffix(".numbers") }.sorted(by: >)
            
            if let latest = trackingFiles.first {
                let latestFile = documentsDir.appendingPathComponent(latest)
                print("Found latest: \(latestFile.path). Copying to \(targetFile.path) for today.")
                try fm.copyItem(at: latestFile, to: targetFile)
            }
        } catch {
            print("Error finding or copying latest tracking file: \(error.localizedDescription)")
        }
    }
    
    if fm.fileExists(atPath: targetFile.path) {
        do {
            let attrs = try fm.attributesOfItem(atPath: linkPath.path)
            if let type = attrs[.type] as? FileAttributeType {
                if type == .typeSymbolicLink {
                    try fm.removeItem(at: linkPath)
                } else if type == .typeRegular {
                    let backupPath = documentsDir.appendingPathComponent("StockTracking_Daily.numbers.bak")
                    if fm.fileExists(atPath: backupPath.path) {
                        try fm.removeItem(at: backupPath)
                    }
                    try fm.moveItem(at: linkPath, to: backupPath)
                }
            }
        } catch {
            // It's perfectly fine if the symlink doesn't exist yet
        }
        
        do {
            try fm.createSymbolicLink(at: linkPath, withDestinationURL: targetFile)
            print("Synced: \(linkPath.path) -> \(targetFile.path)")
        } catch {
            print("Warning: Failed to symlink \(targetFile.path) to \(linkPath.path): \(error.localizedDescription)")
        }
    } else {
        print("Warning: Target file \(targetFile.path) not found. Skipping filename sync.")
    }
}

func checkMarketOpen() -> Bool {
    let scriptPath = scriptsDir.appendingPathComponent("day_market_gatekeeper.py").path
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
    process.arguments = ["/Users/bookid/.hermes/.venv/bin/python", scriptPath]
    
    do {
        try process.run()
        process.waitUntilExit()
        return process.terminationStatus == 0
    } catch {
        print("Gatekeeper check failed: \(error.localizedDescription)")
        return false
    }
}

func main() {
    let now = Date()
    let calendar = Calendar.current
    let hour = calendar.component(.hour, from: now)
    let minute = calendar.component(.minute, from: now)
    
    let isLiveHours = (hour >= 9 && hour < 13) || (hour == 13 && minute <= 40)
    if isLiveHours {
        if !checkMarketOpen() {
            print("Market is closed. Orchestrator exiting gracefully.")
            return
        }
    }

    // 0. Sync Numbers Filename
    syncNumbersFilename()
    
    // 1. Sync Data (The Gatherer)
    runScript(name: "hermes_sync")
    
    // 2. Distribute (The Bots)
    runScript(name: "hermes_monitor", args: ["--profile", "personal"])
    runScript(name: "hermes_monitor", args: ["--profile", "william"])
    runScript(name: "hermes_monitor", args: ["--profile", "group"])
    
    // 3. Intraday Risk Monitor (Stop-Loss/Take-Profit check)
    runScript(name: "intraday_risk_monitor.py")
}

// Execute
main()
