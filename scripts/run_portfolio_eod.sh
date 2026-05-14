#!/bin/bash
python3 /Users/bookid/.hermes/scripts/day_market_gatekeeper.py || {
    RET=$?
    if [ $RET -eq 1 ]; then
        echo "Market closed, exiting gracefully."
        exit 0
    else
        exit $RET
    fi
}
set -e
python3 /Users/bookid/.hermes/scripts/daily_historical_sync.py --fast
python3 /Users/bookid/.hermes/scripts/confluence_eod_analysis.py
