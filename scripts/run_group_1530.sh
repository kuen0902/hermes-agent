#!/bin/bash
set -e
python3 /Users/bookid/.hermes/scripts/taiex_central_data_sync.py
python3 /Users/bookid/.hermes/scripts/group_confluence_analysis.py
