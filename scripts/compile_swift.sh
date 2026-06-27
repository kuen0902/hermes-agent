#!/bin/bash
cd /Users/bookid/.hermes/scripts

mkdir -p bin

echo "編譯 hermes_orchestrator..."
swiftc -O hermes_orchestrator.swift -o bin/hermes_orchestrator

echo "編譯 hermes_sync..."
swiftc -O hermes_sync.swift -o bin/hermes_sync

echo "編譯 hermes_monitor..."
swiftc -O hermes_monitor.swift -o bin/hermes_monitor

echo "編譯完成！"
