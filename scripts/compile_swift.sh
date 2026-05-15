#!/bin/bash
cd /Users/bookid/.hermes/scripts
echo "編譯 hermes_orchestrator..."
swiftc -O hermes_orchestrator.swift -o hermes_orchestrator

echo "編譯 hermes_sync..."
swiftc -O hermes_sync.swift -o hermes_sync

echo "編譯 hermes_monitor..."
swiftc -O hermes_monitor.swift -o hermes_monitor

echo "編譯完成！"
