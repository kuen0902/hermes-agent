#!/bin/bash
SWIFT="/usr/bin/swift"
SCRIPTS="/Users/bookid/.hermes/scripts"

# 1. Sync Data
$SWIFT $SCRIPTS/hermes_sync.swift

# 2. Daily Report (Profile Group)
$SWIFT $SCRIPTS/hermes_monitor.swift --profile group
