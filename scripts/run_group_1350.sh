#!/bin/bash
PYTHON="/Users/bookid/.hermes/.venv/bin/python"
SWIFT="/usr/bin/swift"
SCRIPTS="/Users/bookid/.hermes/scripts"

# Market Gatekeeper
$PYTHON $SCRIPTS/day_market_gatekeeper.py || {
    RET=$?
    if [ $RET -eq 1 ]; then
        echo "Market closed, exiting gracefully."
        exit 0
    else
        exit $RET
    fi
}

set -e

# Sync and Report using Swift
$SWIFT $SCRIPTS/hermes_sync.swift
$SWIFT $SCRIPTS/hermes_monitor.swift --profile group
