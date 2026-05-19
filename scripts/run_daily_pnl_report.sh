#!/bin/bash
# 每日盤後已實現損益統計與發送排程
echo "=== 開始結算今日已實現損益 ==="
/Users/bookid/.hermes/.venv/bin/python /Users/bookid/.hermes/scripts/calculate_pnl_summary.py
echo "=== 啟動 Swift 引擎發送報表 ==="
/usr/bin/swift /Users/bookid/.hermes/scripts/send_pnl_report.swift
echo "=== 完成 ==="
