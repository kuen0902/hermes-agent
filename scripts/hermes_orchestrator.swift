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
        process.executableURL = URL(fileURLWithPath: "/usr/bin/swift")
        process.arguments = [scriptPath] + args
    } else if name.hasSuffix(".sh") {
        // Shell scripts: use bash
        process.executableURL = URL(fileURLWithPath: "/bin/bash")
        process.arguments = [scriptPath] + args
    } else if name.hasSuffix(".py") {
        // Python scripts: use venv python
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["/Users/bookid/.hermes/.venv/bin/python", scriptPath] + args
    } else {
        // No extension (likely Swift Mach-O executables): run directly
        process.executableURL = URL(fileURLWithPath: scriptPath)
        process.arguments = args
    }
    
    let pipe = Pipe()
    process.standardOutput = pipe
    process.standardError = pipe
    
    let semaphore = DispatchSemaphore(value: 0)
    process.terminationHandler = { _ in
        semaphore.signal()
    }
    
    do {
        try process.run()
        
        let timeoutResult = semaphore.wait(timeout: .now() + 600) // 10 minutes timeout
        if timeoutResult == .timedOut {
            print("Timeout reached for \(name). Terminating process.")
            process.terminate()
        }
        
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
    runScript(name: "hermes_sync.swift")
    
    // 2. Distribute (The Bots)
    runScript(name: "hermes_monitor.swift", args: ["--profile", "personal"])
    runScript(name: "hermes_monitor.swift", args: ["--profile", "william"])
    runScript(name: "hermes_monitor.swift", args: ["--profile", "group"])
    
    // 3. Intraday Risk Monitor (Stop-Loss/Take-Profit check)
    print("--- Triggering Intraday Risk Monitor via ML Daemon ---")
    if let url = URL(string: "http://127.0.0.1:28888/risk_monitor") {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let semaphore = DispatchSemaphore(value: 0)
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            if let err = error {
                print("Failed to call ML Daemon API: \(err.localizedDescription)")
            } else if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                print("Risk Monitor API executed successfully.")
            } else {
                print("Risk Monitor API failed with response: \(String(describing: response))")
            }
            semaphore.signal()
        }
        task.resume()
        
        // Timeout 10 minutes
        let timeoutResult = semaphore.wait(timeout: .now() + 600)
        if timeoutResult == .timedOut {
            print("Risk Monitor API timeout.")
        }
    }
}

// Execute
main()
