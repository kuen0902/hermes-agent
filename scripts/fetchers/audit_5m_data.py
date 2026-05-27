#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-
import os
import json
import duckdb
import pandas as pd
from datetime import datetime

DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")
CENTRAL_JSON = os.path.join(DATA_DIR, "central_stock_data.json")

def get_monitoring_codes():
    if not os.path.exists(CENTRAL_JSON):
        return []
    try:
        with open(CENTRAL_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
            personal = list(data.get('personal_data', {}).keys())
            group = data.get('group_codes', [])
            william = data.get('william_codes', [])
            all_codes = sorted(list(set(personal + group + william)))
            return [c for c in all_codes if not c.startswith('^')]
    except Exception as e:
        print(f"Error loading central json: {e}")
        return []

def audit_5m_gaps():
    codes = get_monitoring_codes()
    if not codes:
        print("❌ 沒有發現監控個股代碼。")
        return
        
    print(f"🔍 啟動 {len(codes)} 檔在線個股之 5m 高頻資料健康體檢...")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ 找不到 DuckDB 資料庫: {DB_PATH}")
        return
        
    conn = duckdb.connect(DB_PATH)
    
    # 獲取最近 60 天內的所有交易日
    try:
        trading_days_df = conn.execute("""
            SELECT DISTINCT date 
            FROM daily_stock_data 
            WHERE date >= CURRENT_DATE - INTERVAL 60 DAY
            ORDER BY date DESC
        """).fetchdf()
        trading_days = [pd.to_datetime(d).date() for d in trading_days_df['date'].values]
    except Exception as e:
        print(f"❌ 無法獲取交易日列表: {e}")
        conn.close()
        return
        
    print(f"📅 最近 60 天內的交易日總數: {len(trading_days)} 天")
    
    report_data = []
    gap_registry = {}
    
    for idx, code in enumerate(codes, 1):
        # 查詢該股在 daily_stock_data 中的實際交易日
        try:
            stock_days_df = conn.execute("""
                SELECT DISTINCT date 
                FROM daily_stock_data 
                WHERE code = ? AND date >= CURRENT_DATE - INTERVAL 60 DAY
            """, (code,)).fetchdf()
            stock_days = set(pd.to_datetime(d).date() for d in stock_days_df['date'].values)
        except Exception as e:
            print(f"⚠️ 讀取 {code} 歷史交易日失敗: {e}")
            stock_days = set()
            
        # 查詢該股在 kbars_5m 中已有的 5m 資料日期與每日期數
        try:
            kbars_df = conn.execute("""
                SELECT CAST(timestamp AS DATE) as date, count(*) as bar_count
                FROM kbars_5m
                WHERE code = ? AND timestamp >= CURRENT_DATE - INTERVAL 60 DAY
                GROUP BY date
            """, (code,)).fetchdf()
            
            kbars_by_date = {pd.to_datetime(row['date']).date(): int(row['bar_count']) for _, row in kbars_df.iterrows()}
        except Exception as e:
            print(f"⚠️ 讀取 {code} 5m K線失敗: {e}")
            kbars_by_date = {}
            
        missing_days = []
        incomplete_days = [] # bars < 30 (台股一天應有 54 根 5m bar)
        
        for d in sorted(list(stock_days)):
            if d not in kbars_by_date:
                missing_days.append(d.strftime('%Y-%m-%d'))
            elif kbars_by_date[d] < 30:
                incomplete_days.append((d.strftime('%Y-%m-%d'), kbars_by_date[d]))
                
        has_issue = len(missing_days) > 0 or len(incomplete_days) > 0
        if has_issue:
            gap_registry[code] = {
                "missing": missing_days,
                "incomplete": [d for d, _ in incomplete_days]
            }
            
        report_data.append({
            "code": code,
            "total_trading_days": len(stock_days),
            "missing_count": len(missing_days),
            "incomplete_count": len(incomplete_days),
            "missing_days": missing_days,
            "incomplete_days": incomplete_days
        })
        
    conn.close()
    
    # 輸出 Markdown 體檢報告
    print("\n" + "="*80)
    print(" 📋 「在線個股」5m 高頻資料健康體檢報告 (最近 60 天)")
    print("="*80)
    
    total_gaps = sum(r['missing_count'] + r['incomplete_count'] for r in report_data)
    affected_stocks = sum(1 for r in report_data if r['missing_count'] + r['incomplete_count'] > 0)
    
    print(f"📊 總結：共體檢 {len(codes)} 檔個股，其中 {affected_stocks} 檔個股存在資料缺漏，共計缺漏 {total_gaps} 個交易日。")
    print("-"*80)
    
    print(f"{'股號':<6} | {'總交易日':<8} | {'完全缺漏(天)':<12} | {'資料不足(天)':<12} | {'體檢狀態'}")
    print("-"*80)
    for r in report_data:
        status = "🔴 異常" if (r['missing_count'] + r['incomplete_count'] > 0) else "🟢 完美健康"
        print(f"{r['code']:<8} | {r['total_trading_days']:<12} | {r['missing_count']:<14} | {r['incomplete_count']:<14} | {status}")
        
    print("-"*80)
    
    # 若有缺漏，寫入待回補清單
    registry_path = os.path.join(DATA_DIR, "missing_5m_audit.json")
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(gap_registry, f, indent=2, ensure_ascii=False)
    print(f"💾 已將缺漏日期清單寫入快取: {registry_path}")
    print("="*80)

if __name__ == "__main__":
    audit_5m_gaps()
