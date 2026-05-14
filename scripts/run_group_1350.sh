#!/bin/bash
PYTHON="/Users/bookid/workspace/hermes-agent/venv_314/bin/python"
$PYTHON /Users/bookid/.hermes/scripts/day_market_gatekeeper.py || {
    RET=$?
    if [ $RET -eq 1 ]; then
        echo "Market closed, exiting gracefully."
        exit 0
    else
        exit $RET
    fi
}
set -e
$PYTHON /Users/bookid/.hermes/scripts/taiex_orchestrator.py
$PYTHON /Users/bookid/.hermes/scripts/group_stock_monitor.py
