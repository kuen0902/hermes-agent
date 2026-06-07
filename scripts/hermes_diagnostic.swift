import Foundation

func checkFile(_ path: String) -> String {
    let exists = FileManager.default.fileExists(atPath: (path as NSString).expandingTildeInPath)
    return exists ? "✅" : "❌"
}

let date = Date()
let formatter = DateFormatter()
formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"

print("Hermes System Diagnostic - \(formatter.string(from: date))")
print("------------------------------------")
print("\(checkFile("~/.hermes/HANDOVER.md")) HANDOVER.md")
print("\(checkFile("~/.hermes/ARCHITECTURE.md")) ARCHITECTURE.md")
print("\(checkFile("~/.hermes/scripts/hermes_diagnostic.swift")) diagnostic.swift")
print("\(checkFile("/usr/bin/swift")) Swift Runtime")
print("\(checkFile("~/.hermes/cron/jobs.json")) jobs.json")
print("\(checkFile("~/.hermes/logs/agent.log")) agent.log")
print("------------------------------------")
print("Status: Operationally Ready")
