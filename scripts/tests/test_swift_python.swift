#!/usr/bin/swift
import Foundation

struct PythonResponse: Codable {
    let status: String
    let message: String
    let data: ResponseData
}

struct ResponseData: Codable {
    let received_args: [String]
    let calculated_value: Int
}

func runPythonScriptReturningJSON(scriptName: String, args: [String]) -> PythonResponse? {
    let fm = FileManager.default
    let scriptPath = fm.homeDirectoryForCurrentUser.appendingPathComponent(".hermes/scripts/\(scriptName)").path
    let pythonPath = fm.homeDirectoryForCurrentUser.appendingPathComponent(".hermes/.venv/bin/python").path
    
    let process = Process()
    process.executableURL = URL(fileURLWithPath: pythonPath)
    process.arguments = [scriptPath] + args
    
    let pipe = Pipe()
    process.standardOutput = pipe
    process.standardError = Pipe() // Ignore stderr or handle separately
    
    do {
        try process.run()
        process.waitUntilExit()
        
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        
        // Attempt to parse JSON output
        let decoder = JSONDecoder()
        let response = try decoder.decode(PythonResponse.self, from: data)
        return response
        
    } catch {
        print("Error executing Python script or parsing output: \(error.localizedDescription)")
        return nil
    }
}

// Test the bridge
print("Calling test_output.py from Swift...")
if let response = runPythonScriptReturningJSON(scriptName: "test_output.py", args: ["hello", "world"]) {
    print("--- Received Response from Python ---")
    print("Status: \(response.status)")
    print("Message: \(response.message)")
    print("Calculated Value: \(response.data.calculated_value)")
    print("Arguments passed back: \(response.data.received_args)")
} else {
    print("Failed to get a valid response.")
}
