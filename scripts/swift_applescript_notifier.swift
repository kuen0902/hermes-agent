import Foundation

let args = CommandLine.arguments
guard args.count >= 4 else {
    print("Usage: swift_applescript_notifier <title> <subtitle> <message>")
    exit(1)
}

let title = args[1]
let subtitle = args[2]
let message = args[3]

// Escape quotes for AppleScript
let safeTitle = title.replacingOccurrences(of: "\"", with: "\\\"")
let safeSubtitle = subtitle.replacingOccurrences(of: "\"", with: "\\\"")
let safeMessage = message.replacingOccurrences(of: "\"", with: "\\\"")

let appleScriptSource = """
display notification "\(safeMessage)" with title "\(safeTitle)" subtitle "\(safeSubtitle)" sound name "Ping"
"""

var error: NSDictionary?
if let scriptObject = NSAppleScript(source: appleScriptSource) {
    scriptObject.executeAndReturnError(&error)
    if let error = error {
        print("AppleScript Error: \(error)")
        exit(1)
    } else {
        print("Notification Dispatched via NSAppleScript Bridge.")
    }
} else {
    print("Failed to initialize NSAppleScript")
    exit(1)
}
