#!/bin/bash
# Ensure PATH is correct to find the global hermes command
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:$PATH"
echo "=== Starting State Pruning ==="
hermes curator prune
echo "=== State Pruning Completed ==="
