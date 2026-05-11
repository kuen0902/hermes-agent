#!/bin/bash
echo "🛑 Killing all Hermes and OpenClaw related processes..."
ps aux | grep -Ei "hermes|openclaw|gateway" | grep -v "grep" | awk '{print $2}' | xargs kill -9 2>/dev/null
echo "🗑️ Removing lock files..."
rm -f ~/.hermes/*.lock ~/.hermes/data/*.lock ~/.hermes/run/*.lock ~/.hermes/gateway.pid
echo "✅ Cleanup complete."
