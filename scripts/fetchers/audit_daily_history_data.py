#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-
import os
import json
import duckdb
import pandas as pd
import datetime

DATA_DIR = os.path.expanduser("~/.hermes/data")
POTENTIAL_DDB = os.path.join(DATA_DIR, "potential_analysis.ddb")
REGISTRY_PATH = os.path.join(DATA_DIR, "master_stock_registry.json")
CSV_DIR = os.path.expanduser("~/Documents/StockData_History_Final")

def get_previous_trading_day():
    """Returns the ISO string YYYY-MM-DD of the previous trading day (Mon-Fri) excluding holidays."""
    try:
        import yfinance as yf
        ticker = yf.Ticker("0050.TW")
        hist = ticker.history(period="5d")
        if not hist.empty:
            return hist.index[-1].strftime('%Y-%m-%d')
    except Exception:
        pass
        
    # Fallback to local weekday math if network check fails
    today = datetime.datetime.now()
    offset = 1
    wd = today.weekday()
    if wd == 0:    # Monday
        offset = 3
    elif wd == 6:  # Sunday
        offset = 2
    elif wd == 5:  # Saturday
        offset = 1
    prev = today - datetime.timedelta(days=offset)
    return prev.strftime('%Y-%m-%d')

def audit_daily_history():
    print("=========================================================================")
    print(f" 🔍 啟動「14年日線歷史資料」健康排查與一致性稽核 [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}]")
    print("=========================================================================")
    
    if not os.path.exists(POTENTIAL_DDB):
        print(f"❌ 找不到 DuckDB 資料庫: {POTENTIAL_DDB}")
        return
        
    prev_trading_day = get_previous_trading_day()
    print(f"📅 前一交易日目標: {prev_trading_day}")
    
    conn = duckdb.connect(POTENTIAL_DDB)
    
    # 1. 取得資料庫中所有有日線記錄的股號與最新交易日
    print("  👉 [1/5] 稽核資料庫時效性 (Recency Analysis)...")
    try:
        db_summary_df = conn.execute("""
            SELECT code, ticker, name, MAX(date) as max_date, COUNT(*) as total_rows
            FROM daily_stock_data
            GROUP BY code, ticker, name
        """).fetchdf()
    except Exception as e:
        print(f"❌ 無法讀取 daily_stock_data 資料表: {e}")
        conn.close()
        return

    total_stocks = len(db_summary_df)
    print(f"     資料庫中共存有 {total_stocks} 檔個股的日線資料。")
    
    not_recent_stocks = []
    for _, row in db_summary_df.iterrows():
        code = str(row['code'])
        max_date = str(row['max_date'])
        if max_date != prev_trading_day:
            not_recent_stocks.append({
                "code": code,
                "ticker": str(row['ticker']),
                "name": str(row['name']),
                "latest_date": max_date
            })
            
    print(f"     ✓ 時效性稽核完成。有 {len(not_recent_stocks)}/{total_stocks} 檔個股的最新日線日期未對齊前一交易日。")
    
    # 2. 欄位格式與數值合理性排查 (Data Quality Audit)
    print("\n  👉 [2/5] 欄位與數值合理性排查 (價格非正值、NaN 檢驗)...")
    anomaly_records = []
    try:
        # 篩選出任何開高低收價格為零/負數、或成交量為負值之异常行
        anomalies_df = conn.execute("""
            SELECT date, code, ticker, name, open, high, low, close, volume
            FROM daily_stock_data
            WHERE open <= 0 OR high <= 0 OR low <= 0 OR close <= 0 OR volume < 0
               OR open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL OR volume IS NULL
            ORDER BY date DESC
            LIMIT 100
        """).fetchdf()
        
        if not anomalies_df.empty:
            for _, row in anomalies_df.iterrows():
                anomaly_records.append({
                    "date": str(row['date']),
                    "code": str(row['code']),
                    "ticker": str(row['ticker']),
                    "name": str(row['name']),
                    "open": float(row['open']) if pd.notna(row['open']) else None,
                    "high": float(row['high']) if pd.notna(row['high']) else None,
                    "low": float(row['low']) if pd.notna(row['low']) else None,
                    "close": float(row['close']) if pd.notna(row['close']) else None,
                    "volume": int(row['volume']) if pd.notna(row['volume']) else None,
                    "reason": "價格非正值或包含空值(Null)"
                })
    except Exception as e:
        print(f"     ⚠️ 價格合理性查詢出錯: {e}")
        
    # 3. 價格邏輯一致性排查 (High/Low Bounds & Price Logic Check)
    print("\n  👉 [3/5] 價格邏輯一致性排查 (High >= Low 物理邏輯)...")
    try:
        logic_errors_df = conn.execute("""
            SELECT date, code, ticker, name, open, high, low, close
            FROM daily_stock_data
            WHERE high < open OR high < close OR low > open OR low > close OR high < low
            ORDER BY date DESC
            LIMIT 100
        """).fetchdf()
        
        if not logic_errors_df.empty:
            for _, row in logic_errors_df.iterrows():
                anomaly_records.append({
                    "date": str(row['date']),
                    "code": str(row['code']),
                    "ticker": str(row['ticker']),
                    "name": str(row['name']),
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "reason": "最高低價物理邏輯矛盾(例如 High < Low 或 High < Close)"
                })
    except Exception as e:
        print(f"     ⚠️ 價格邏輯查詢出錯: {e}")
        
    print(f"     ✓ 價格邏輯與數值合理性完成。共發現 {len(anomaly_records)} 筆異常日線行。")

    # 4. 籌碼數據完整性排查 (Institutional Flows Missing Check)
    print("\n  👉 [4/5] 籌碼數據完整性排查 (最近10天三大法人是否全為0)...")
    chips_missing_stocks = []
    try:
        # 篩選最近10個交易日內，三大法人合計淨買賣均為 0 的個股 (排除冷門無交易個股後)
        chips_df = conn.execute("""
            SELECT code, ticker, name, 
                   SUM(ABS(foreign_net)) as total_f, 
                   SUM(ABS(trust_net)) as total_t, 
                   SUM(ABS(dealer_net)) as total_d,
                   SUM(volume) as total_v
            FROM daily_stock_data
            WHERE date >= CURRENT_DATE - INTERVAL 15 DAY
            GROUP BY code, ticker, name
            HAVING total_f = 0 AND total_t = 0 AND total_d = 0 AND total_v > 100000
        """).fetchdf()
        
        for _, row in chips_df.iterrows():
            chips_missing_stocks.append({
                "code": str(row['code']),
                "ticker": str(row['ticker']),
                "name": str(row['name']),
                "reason": "成交量大於10萬股，但最近15天三大法人買賣超全為0 (疑似籌碼漏同步)"
            })
    except Exception as e:
        print(f"     ⚠️ 籌碼完整性查詢出錯: {e}")
    print(f"     ✓ 籌碼數據完整性完成。共篩選出 {len(chips_missing_stocks)} 檔疑似籌碼缺失個股。")

    # 5. 本地實體 CSV 檔案完整性對齊排查 (Local CSV vs Database Alignment)
    print("\n  👉 [5/5] 本地實體 CSV 檔案與資料庫對齊排查...")
    csv_missing_stocks = []
    csv_out_of_sync = []
    
    if os.path.exists(CSV_DIR):
        try:
            csv_files = {f.split('_')[0]: f for f in os.listdir(CSV_DIR) if f.endswith('.csv')}
            for _, row in db_summary_df.iterrows():
                code = str(row['code'])
                ticker = str(row['ticker'])
                name = str(row['name']).replace('/', '_')
                
                # A. 檢查實體檔案是否存在
                if code not in csv_files:
                    csv_missing_stocks.append({
                        "code": code,
                        "ticker": ticker,
                        "name": name
                    })
                else:
                    # B. 檢查 CSV 檔案最新日期是否與資料庫同步
                    csv_path = os.path.join(CSV_DIR, csv_files[code])
                    try:
                        df_csv = pd.read_csv(csv_path)
                        if not df_csv.empty and 'Date' in df_csv.columns:
                            csv_latest = str(df_csv['Date'].iloc[-1]).strip()
                            db_latest = str(row['max_date']).strip()
                            if csv_latest != db_latest:
                                csv_out_of_sync.append({
                                    "code": code,
                                    "ticker": ticker,
                                    "name": name,
                                    "csv_latest": csv_latest,
                                    "db_latest": db_latest
                                })
                    except:
                        pass
        except Exception as e:
            print(f"     ⚠️ 實體 CSV 檔案排查出錯: {e}")
            
    print(f"     ✓ CSV 與資料庫對齊排查完成。檔案缺失: {len(csv_missing_stocks)} 檔 | 時序不對齊: {len(csv_out_of_sync)} 檔。")
    conn.close()

    # 💾 6. 彙總並寫入 14年歷史資料排查報告快取
    audit_report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "prev_trading_day": prev_trading_day,
        "total_audited_stocks": total_stocks,
        "not_recent_stocks_count": len(not_recent_stocks),
        "anomalies_count": len(anomaly_records),
        "chips_missing_count": len(chips_missing_stocks),
        "csv_missing_count": len(csv_missing_stocks),
        "csv_out_of_sync_count": len(csv_out_of_sync),
        "not_recent_stocks": not_recent_stocks[:20],  # 限制寫入前 20 筆
        "anomalies": anomaly_records[:20],
        "chips_missing": chips_missing_stocks[:20],
        "csv_missing": csv_missing_stocks,
        "csv_out_of_sync": csv_out_of_sync[:20]
    }
    
    report_cache_path = os.path.join(DATA_DIR, "missing_daily_audit.json")
    with open(report_cache_path, 'w', encoding='utf-8') as f:
        json.dump(audit_report, f, indent=2, ensure_ascii=False)
        
    # 🖨️ 印出 Markdown 體檢報告
    print("\n" + "="*80)
    print(" 📋 「14年日線歷史資料」大排查健康診斷書")
    print("="*80)
    total_issues = len(not_recent_stocks) + len(anomaly_records) + len(chips_missing_stocks) + len(csv_missing_stocks) + len(csv_out_of_sync)
    status = "🔴 警告 (有局部資料缺漏或異常值)" if total_issues > 0 else "🟢 完美健康 (100% 完整與精確)"
    
    print(f"📊 總結狀態：{status}")
    print(f" - 體檢個股總數：{total_stocks} 檔")
    print(f" - 最新日線未對齊前一交易日：{len(not_recent_stocks)} 檔")
    print(f" - 數值異常/邏輯矛盾日線行：{len(anomaly_records)} 條")
    print(f" - 籌碼缺失疑似股：{len(chips_missing_stocks)} 檔")
    print(f" - 本地實體 CSV 檔案缺失：{len(csv_missing_stocks)} 檔")
    print(f" - CSV 與資料庫時間不一致：{len(csv_out_of_sync)} 檔")
    print("-"*80)
    
    if csv_missing_stocks:
        print("📁 實體 CSV 檔案缺失清單 (前 5 檔)：")
        for s in csv_missing_stocks[:5]:
            print(f"  - {s['code']} ({s['name']}) -> {s['ticker']}")
        print("-"*80)
        
    if not_recent_stocks:
        print("🕒 最新日線未對齊前一交易日個股 (前 5 檔)：")
        for s in not_recent_stocks[:5]:
            print(f"  - {s['code']} ({s['name']}) | 最新日期: {s['latest_date']} (預期: {prev_trading_day})")
        print("-"*80)
        
    print(f"💾 已將詳細的診斷報告寫入快取，可隨時讀取回補：{report_cache_path}")
    print("=========================================================================")

if __name__ == "__main__":
    audit_daily_history()
