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
    # 改為自 DuckDB 讀取全市場所有 active 在線個股，以支援全局 5m 同步
    db_path = DB_PATH
    if not os.path.exists(db_path):
        return []
    try:
        conn = duckdb.connect(db_path, read_only=True)
        df = conn.execute("SELECT DISTINCT code FROM daily_stock_data").fetchdf()
        conn.close()
        codes = sorted(df['code'].tolist())
        return [str(c) for c in codes if not str(c).startswith('^')]
    except Exception as e:
        print(f"⚠️ 無法自 DuckDB 載入全市場個股代碼: {e}")
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
    
    # 獲取最近 150 天內的所有交易日
    try:
        trading_days_df = conn.execute("""
            SELECT DISTINCT date 
            FROM daily_stock_data 
            WHERE date >= CURRENT_DATE - INTERVAL 150 DAY
            ORDER BY date DESC
        """).fetchdf()
        trading_days = [pd.to_datetime(d).date() for d in trading_days_df['date'].values]
    except Exception as e:
        print(f"❌ 無法獲取交易日列表: {e}")
        conn.close()
        return
        
    print(f"📅 最近 150 天內的交易日總數: {len(trading_days)} 天")
    
    # 1. 取得所有在線個股及其總交易日數
    try:
        trading_days_summary_df = conn.execute("""
            SELECT code, COUNT(DISTINCT date) as total_trading_days
            FROM daily_stock_data
            WHERE date >= CURRENT_DATE - INTERVAL 150 DAY
              AND NOT STARTS_WITH(code, '^')
            GROUP BY code
        """).fetchdf()
        stock_trading_days = {str(row['code']): int(row['total_trading_days']) for _, row in trading_days_summary_df.iterrows()}
    except Exception as e:
        print(f"❌ 獲取個股總交易日數失敗: {e}")
        conn.close()
        return

    # 2. 執行高效批量 JOIN 查詢，一次性篩選出所有缺失與不足的 5m 交易日
    try:
        gaps_query = """
        WITH stock_days AS (
            SELECT DISTINCT code, date
            FROM daily_stock_data
            WHERE date >= CURRENT_DATE - INTERVAL 150 DAY
              AND NOT STARTS_WITH(code, '^')
        ),
        kbar_counts AS (
            SELECT code, CAST(timestamp AS DATE) as date, count(*) as bar_count
            FROM kbars_5m
            WHERE timestamp >= CURRENT_DATE - INTERVAL 150 DAY
            GROUP BY code, date
        )
        SELECT 
            s.code, 
            s.date,
            COALESCE(k.bar_count, 0) as bar_count
        FROM stock_days s
        LEFT JOIN kbar_counts k ON s.code = k.code AND s.date = k.date
        WHERE k.bar_count IS NULL OR k.bar_count < 30
        ORDER BY s.code, s.date DESC
        """
        gaps_df = conn.execute(gaps_query).fetchdf()
    except Exception as e:
        print(f"❌ 批量體檢高頻 Gap 失敗: {e}")
        conn.close()
        return

    gaps_by_code = {}
    for _, row in gaps_df.iterrows():
        code = str(row['code'])
        date_str = pd.to_datetime(row['date']).strftime('%Y-%m-%d')
        bar_count = int(row['bar_count'])
        
        if code not in gaps_by_code:
            gaps_by_code[code] = {"missing": [], "incomplete": []}
            
        if bar_count == 0:
            gaps_by_code[code]["missing"].append(date_str)
        else:
            gaps_by_code[code]["incomplete"].append((date_str, bar_count))

    # 3. 建立 gap_registry 與 report_data
    report_data = []
    gap_registry = {}
    
    for code in codes:
        code_str = str(code)
        total_days = stock_trading_days.get(code_str, 0)
        
        gaps = gaps_by_code.get(code_str, {"missing": [], "incomplete": []})
        missing_days = sorted(gaps["missing"])
        incomplete_days = sorted(gaps["incomplete"], key=lambda x: x[0])
        
        if missing_days or incomplete_days:
            gap_registry[code_str] = {
                "missing": missing_days,
                "incomplete": [d for d, _ in incomplete_days]
            }
            
        report_data.append({
            "code": code_str,
            "total_trading_days": total_days,
            "missing_count": len(missing_days),
            "incomplete_count": len(incomplete_days),
            "missing_days": missing_days,
            "incomplete_days": incomplete_days
        })
        
    conn.close()
    
    # 輸出 Markdown 體檢報告
    print("\n" + "="*80)
    print(" 📋 「在線個股」5m 高頻資料健康體檢報告 (最近 150 天)")
    print("="*80)
    
    total_gaps = sum(r['missing_count'] + r['incomplete_count'] for r in report_data)
    affected_stocks = sum(1 for r in report_data if r['missing_count'] + r['incomplete_count'] > 0)
    
    print(f"📊 總結：共體檢 {len(codes)} 檔個股，其中 {affected_stocks} 檔個股存在資料缺漏，共計缺漏 {total_gaps} 個交易日。")
    print("-"*80)
    
    print(f"{'股號':<8} | {'總交易日':<12} | {'完全缺漏(天)':<14} | {'資料不足(天)':<14} | {'體檢狀態'}")
    print("-"*80)
    printed_count = 0
    for r in report_data:
        has_gap = (r['missing_count'] + r['incomplete_count'] > 0)
        if has_gap:
            if printed_count < 50:
                print(f"{r['code']:<8} | {r['total_trading_days']:<12} | {r['missing_count']:<14} | {r['incomplete_count']:<14} | 🔴 異常")
                printed_count += 1
            else:
                pass
    if affected_stocks > 50:
        print(f"... 還有 {affected_stocks - 50} 檔異常個股未列出 ...")
    print("-"*80)
    
    # 若有缺漏，寫入待回補清單
    registry_path = os.path.join(DATA_DIR, "missing_5m_audit.json")
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(gap_registry, f, indent=2, ensure_ascii=False)
    print(f"💾 已將缺漏日期清單寫入快取: {registry_path}")
    print("="*80)

if __name__ == "__main__":
    audit_5m_gaps()
