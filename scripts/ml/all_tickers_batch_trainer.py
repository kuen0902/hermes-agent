#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import argparse
from datetime import datetime
import duckdb
import pandas as pd

# Add current script directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rolling_ml_orchestrator import (
    prepare_daily_features,
    query_ticker_daily_db,
    train_daily_ticker_model,
    run_rolling_training_and_feedback,
    normalize_code,
    MODEL_DIR,
    DUCK_PATH
)

STATE_FILE = os.path.join(MODEL_DIR, "batch_training_state.json")

def send_ger_notification(message):
    token = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU" # Star Platinum (@taiwangupiaoBot)
    chat_id = "6326497055"
    import requests
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if not response.json().get("ok", False):
            print(f"⚠️ Telegram API response error: {response.text}")
    except Exception as e:
        print(f"⚠️ Failed to send Telegram notification: {e}")

def load_all_active_tickers():
    if not os.path.exists(DUCK_PATH):
        print(f"⚠️ DuckDB database not found at {DUCK_PATH}")
        return []
    try:
        conn = duckdb.connect(DUCK_PATH)
        latest_date_str = conn.execute("SELECT MAX(date) FROM daily_stock_data").fetchone()[0]
        if not latest_date_str:
            conn.close()
            return []
        latest_dt = pd.to_datetime(latest_date_str)
        rows = conn.execute("""
            SELECT code, MAX(date) as max_date 
            FROM daily_stock_data 
            GROUP BY code
        """).fetchall()
        conn.close()
        
        active_tickers = []
        for code, max_date_str in rows:
            if max_date_str:
                max_dt = pd.to_datetime(max_date_str)
                if (latest_dt - max_dt).days <= 7:
                    active_tickers.append(normalize_code(code))
        return sorted(list(set(active_tickers)))
    except Exception as e:
        print(f"⚠️ Error loading active tickers: {e}")
        return []

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading state file: {e}")
    return {
        "processed_tickers": [],
        "failed_tickers": {},
        "last_processed_index": -1,
        "total_tickers": 0,
        "last_run_at": None
    }

def save_state(state):
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error saving state file: {e}")

def main():
    parser = argparse.ArgumentParser(description="全市場在線個股自適應 ML 滾動批量訓練器")
    parser.add_argument("--batch-size", type=int, default=100, help="單次執行的個股數量")
    parser.add_argument("--resume", action="store_true", help="是否接續上次的進度進行訓練")
    parser.add_argument("--start-index", type=int, default=None, help="手動指定起始的索引值(0-indexed)")
    args = parser.parse_args()
    
    print("=========================================================")
    print(" 🤖 啟動全市場在線個股自適應 ML 滾動分批訓練器 (Batch Mode) ")
    print("=========================================================")
    
    # 1. 載入全市場在線商品
    all_active = load_all_active_tickers()
    total_active_count = len(all_active)
    print(f"資料庫中有效在線個股總計: {total_active_count} 檔")
    if total_active_count == 0:
        print("❌ 查無任何有效在線個股，結束訓練。")
        return
        
    # 2. 載入進度狀態
    state = load_state()
    state["total_tickers"] = total_active_count
    
    # 處理進度續傳或重設
    processed_set = set(state["processed_tickers"])
    
    if args.resume:
        print("🔄 [Resume 模式] 載入歷史進度中...")
        print(f"  - 已成功處理：{len(processed_set)} / {total_active_count} 檔")
        print(f"  - 失敗紀錄數：{len(state['failed_tickers'])} 檔")
    else:
        print("🆕 [Fresh 模式] 重置所有訓練進度狀態...")
        state["processed_tickers"] = []
        state["failed_tickers"] = {}
        state["last_processed_index"] = -1
        processed_set = set()
        save_state(state)
        
    # 確定起始索引
    start_idx = 0
    if args.start_index is not None:
        start_idx = args.start_index
        print(f"📍 手動指定起始索引：{start_idx}")
    elif args.resume:
        start_idx = state["last_processed_index"] + 1
        
    print(f"預計從商品索引 #{start_idx} 開始掃描 ...")
    
    # 篩選出本次需要處理的清單
    pending_tickers = []
    for idx in range(start_idx, total_active_count):
        code = all_active[idx]
        if code not in processed_set:
            pending_tickers.append((idx, code))
        if len(pending_tickers) >= args.batch_size:
            break
            
    if not pending_tickers:
        print("🎉 所有在線商品已全部訓練完成！無需進行任何處理。")
        return
        
    print(f"本次批次預計訓練商品數量: {len(pending_tickers)} 檔")
    print(f"清單：{[item[1] for item in pending_tickers]}")
    print("---------------------------------------------------------")
    
    # 發送跑前 Telegram 通知
    completed_count = len(state["processed_tickers"])
    percentage = (completed_count / total_active_count) * 100
    
    start_msg = f"""🌅 **「黃金體驗-鎮魂曲」：全市場批量訓練啟動** 🌅

🔔 系統已啟動全新一輪批次訓練！
- **下一批次預計訓練個股數量**：`{len(pending_tickers)}` 檔
- **預計處理商品清單**：{', '.join([item[1] for item in pending_tickers])}
- **當前已成功處理進度**：`{completed_count}` / `{total_active_count}` (`{percentage:.2f}%`)
- **剩餘待完成商品數**：`{total_active_count - completed_count}` 檔"""
    
    send_ger_notification(start_msg)
    
    success_count = 0
    fail_count = 0
    start_time = time.time()
    
    for count_idx, (global_idx, code) in enumerate(pending_tickers, 1):
        print(f"\n[{count_idx}/{len(pending_tickers)}] 正在處理商品 #{global_idx} - {code} ...")
        
        try:
            # 1. 讀取並處理 14 年歷史日線
            daily_df = query_ticker_daily_db(code)
            if daily_df.empty or len(daily_df) < 80:
                reason = f"資料庫歷史日線資料量不足 (僅 {len(daily_df)} 筆)"
                print(f"  ⚠️ [{code}] {reason}，跳過。")
                state["failed_tickers"][code] = reason
                state["last_processed_index"] = global_idx
                save_state(state)
                fail_count += 1
                continue
                
            processed_daily = prepare_daily_features(daily_df)
            if processed_daily is None or processed_daily.empty:
                reason = "特徵工程產生無效結果"
                print(f"  ⚠️ [{code}] {reason}，跳過。")
                state["failed_tickers"][code] = reason
                state["last_processed_index"] = global_idx
                save_state(state)
                fail_count += 1
                continue
                
            # 2. 訓練個股 14 年日線 XGBoost 模型
            daily_model = train_daily_ticker_model(code, processed_daily)
            if daily_model is None:
                reason = "訓練個股日線模型失敗"
                print(f"  ⚠️ [{code}] {reason}，跳過。")
                state["failed_tickers"][code] = reason
                state["last_processed_index"] = global_idx
                save_state(state)
                fail_count += 1
                continue
            print(f"  ✓ [{code}] 個股 14年日線 XGBoost 模型訓練成功！")
            
            # 3. 高頻 150-90日預訓練 & 89日-1日自適應滾動偏差更新
            success = run_rolling_training_and_feedback(code, daily_df, daily_model)
            if success:
                print(f"  ✓ [{code}] 高頻滾動與卡爾曼偏置自適應校準成功！")
                state["processed_tickers"].append(code)
                # 從失敗列表中移除(如果之前失敗過的話)
                state["failed_tickers"].pop(code, None)
                success_count += 1
            else:
                reason = "高頻滾動偏置校準失敗"
                print(f"  ⚠️ [{code}] {reason}。")
                state["failed_tickers"][code] = reason
                fail_count += 1
                
        except Exception as ex:
            reason = f"運行期異常：{str(ex)}"
            print(f"  ❌ [{code}] {reason}")
            state["failed_tickers"][code] = reason
            fail_count += 1
            
        # 更新最後處理的總索引
        state["last_processed_index"] = global_idx
        state["last_run_at"] = datetime.now().isoformat()
        save_state(state)
        
    elapsed = time.time() - start_time
    print("\n=========================================================")
    print(" 🎉 本批次在線商品滾動自適應 ML 模型優化執行完畢！")
    print(f"  - 本次成功處理/優化商品數：{success_count} 檔")
    print(f"  - 本次失敗/跳過商品數：{fail_count} 檔")
    print(f"  - 累計已成功處理總數：{len(state['processed_tickers'])} / {total_active_count} 檔")
    print(f"  - 本批次總計花費時間：{elapsed:.2f} 秒")
    print(f"  - 進度狀態檔路徑：{STATE_FILE}")
    print("=========================================================")
    
    # 發送跑後 Telegram 通知
    final_completed_count = len(state["processed_tickers"])
    final_remaining_count = total_active_count - final_completed_count
    final_percentage = (final_completed_count / total_active_count) * 100
    
    end_msg = f"""🌅 **「黃金體驗-鎮魂曲」：本批次訓練完成** 🌅

✅ 本批次個股訓練已成功完成！
- **本批次處理結果**：成功 `{success_count}` 檔，失敗/跳過 `{fail_count}` 檔
- **累計已成功處理總數**：`{final_completed_count}` / `{total_active_count}` (`{final_percentage:.2f}%`)
- **剩餘待完成商品數**：`{final_remaining_count}` 檔
- **本批次訓練耗時**：`{elapsed:.2f}` 秒"""

    send_ger_notification(end_msg)

if __name__ == "__main__":
    main()
