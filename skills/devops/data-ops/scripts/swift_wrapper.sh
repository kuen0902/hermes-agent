#!/bin/bash
# Universal Shell Wrapper for Swift Mach-O Binaries
# Usage: ./swift_wrapper.sh <binary_name> [args...]

BINARY_NAME="$1"
shift
ARGS="$@"

if [ -z "$BINARY_NAME" ]; then
    echo "Usage: swift_wrapper.sh <binary_name> [args...]"
    exit 1
fi

SCRIPTS_DIR="$HOME/.hermes/scripts"
BINARY_PATH="$SCRIPTS_DIR/$BINARY_NAME"

if [ ! -x "$BINARY_PATH" ]; then
    echo "ERROR: Binary not found or not executable: $BINARY_PATH"
    exit 1
fi

# Execute and capture output
OUTPUT=$("$BINARY_PATH" $ARGS 2>&1)
EXIT_CODE=$?

# Handle no_agent=True empty output requirement
if [ $EXIT_CODE -eq 0 ]; then
    if [ -n "$OUTPUT" ]; then
        echo "$OUTPUT"
    else
        echo "OK - Execution successful, no alerts triggered"
    fi
    exit 0
else
    echo "ERROR: Execution failed with code $EXIT_CODE"
    echo "$OUTPUT"
    exit $EXIT_CODE
fi
