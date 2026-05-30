#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-
"""
個股預測模型管理與自動稽核系統
- 提供對多重個股模型 (Multi-Model) 的集中生命週期管理
- 可稽核目前線上有效個股的模型狀態 (資料樣本數、偏差收斂度、最新預測誤差)
- 可自動清理 (Prune) 或歸檔 (Archive) 已失效、下市或不在目前訂閱清單中的過期個股模型，釋放系統空間
"""
import os
import sys
import json
import shutil
import sqlite3
import pandas as pd
from datetime import datetime

DATA_DIR = os.path.expanduser("~/.hermes/data")
MODEL_DIR = os.path.expanduser("~/.hermes/models")
PORTFOLIO_DB = os.path.join(DATA_DIR, "portfolio.db")
DUCK_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")

GLOBAL_PROTECTED_FILES = {
    "intraday_model.pkl",
    "intraday_model_reg.pkl",
    "sell_signal_v1.pkl"
}

def normalize_code(code_str):
    return str(code_str).replace(".TW", "").replace(".TWO", "").strip()

def load_current_active_tickers():
    """載入當前真實持股與 Telegram 訂閱/監控名單中的所有個股代號"""
    active = set()
    # 1. 載入當前 SQLite 持股
    if os.path.exists(PORTFOLIO_DB):
        try:
            conn = sqlite3.connect(PORTFOLIO_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM current_holdings")
            for row in cursor.fetchall():
                active.add(normalize_code(row[0]))
            conn.close()
        except Exception as e:
            print(f"⚠️ 無法讀取 SQLite 持股資訊: {e}")

    # 2. 載入監控清單
    central_path = os.path.join(DATA_DIR, "central_stock_data.json")
    if os.path.exists(central_path):
        try:
            with open(central_path, 'r', encoding='utf-8') as f:
                c_data = json.load(f)
                group_codes = c_data.get("group_codes", [])
                william_codes = c_data.get("william_codes", [])
                active.update(normalize_code(c) for c in group_codes)
                active.update(normalize_code(c) for c in william_codes)
        except Exception as e:
            print(f"⚠️ 無法讀取監控清單 JSON: {e}")
            
    return sorted(list(active))

def audit_active_models(active_tickers):
    """稽核當前有效線上個股的模型收斂與收尾狀態"""
    print("\n=========================================================")
    print(" 🔍 線上有效個股獨立模型稽核報告 (Active Tickers Audit) ")
    print("=========================================================")
    print(f"【線上有效商品總數】：{len(active_tickers)} 檔")
    
    report_data = []
    missing_models = []
    
    for code in active_tickers:
        daily_model_exists = os.path.exists(os.path.join(MODEL_DIR, f"daily_model_{code}.pkl"))
        intra_clf_exists = os.path.exists(os.path.join(MODEL_DIR, f"intraday_model_{code}.pkl"))
        intra_reg_exists = os.path.exists(os.path.join(MODEL_DIR, f"intraday_model_reg_{code}.pkl"))
        state_path = os.path.join(MODEL_DIR, f"rolling_state_{code}.json")
        
        has_state = os.path.exists(state_path)
        bias = 0.0
        last_err = 0.0
        samples = 0
        updated_at = "無紀錄"
        
        if has_state:
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    bias = meta.get("optimized_bias", 0.0)
                    last_err = meta.get("last_error", 0.0)
                    samples = meta.get("samples", 0)
                    updated_at = meta.get("updated_at", "無日期").split("T")[0]
            except:
                pass
                
        # 標記缺失模型
        if not (daily_model_exists and intra_clf_exists and intra_reg_exists):
            missing_models.append(code)
            
        report_data.append({
            "代號": code,
            "日線模型": "✓" if daily_model_exists else "✗",
            "高頻分類": "✓" if intra_clf_exists else "✗",
            "高頻迴歸": "✓" if intra_reg_exists else "✗",
            "訓練樣本": f"{samples} 天" if samples > 0 else "無",
            "偏差控制 (Bias)": f"{bias:+.4f}" if has_state else "無",
            "最新預測誤差": f"{last_err:+.2f}" if has_state else "無",
            "更新日期": updated_at
        })
        
    df = pd.DataFrame(report_data)
    print(df.to_string(index=False))
    
    if missing_models:
        print("\n⚠️ 【注意】以下線上有效個股模型不完整（可能尚未執行滾動優化訓練）：")
        print(f"  👉 {', '.join(missing_models)}")
        print("  💡 提示：可執行 `rolling_ml_orchestrator.py` 來自動生成並訓練這些缺失的模型。")
        
    print("=========================================================")

def prune_stale_models(active_tickers, archive=True):
    """清理或歸檔不再訂閱或失效個股的過期模型與狀態檔"""
    print("\n=========================================================")
    print(" 🧹 啟動過期/失效模型自動清理與歸檔程序 (Pruning Engine) ")
    print("=========================================================")
    
    active_set = set(active_tickers)
    archive_dir = os.path.join(MODEL_DIR, "archive")
    if archive:
        os.makedirs(archive_dir, exist_ok=True)
        
    stale_count = 0
    bytes_freed = 0
    
    # 掃描模型資料夾
    for file_name in os.listdir(MODEL_DIR):
        if file_name in GLOBAL_PROTECTED_FILES:
            continue
        if file_name == "archive":
            continue
            
        # 提取代號
        code = None
        file_type = None
        
        if file_name.startswith("daily_model_") and file_name.endswith(".pkl"):
            code = file_name.replace("daily_model_", "").replace(".pkl", "")
            file_type = "日線模型"
        elif file_name.startswith("intraday_model_reg_") and file_name.endswith(".pkl"):
            code = file_name.replace("intraday_model_reg_", "").replace(".pkl", "")
            file_type = "高頻迴歸"
        elif file_name.startswith("intraday_model_") and file_name.endswith(".pkl"):
            code = file_name.replace("intraday_model_", "").replace(".pkl", "")
            file_type = "高頻分類"
        elif file_name.startswith("rolling_state_") and file_name.endswith(".json"):
            code = file_name.replace("rolling_state_", "").replace(".json", "")
            file_type = "滾動狀態"
            
        if code and code not in active_set:
            file_path = os.path.join(MODEL_DIR, file_name)
            file_size = os.path.getsize(file_path)
            bytes_freed += file_size
            stale_count += 1
            
            if archive:
                dest_path = os.path.join(archive_dir, file_name)
                shutil.move(file_path, dest_path)
                print(f" 📂 [歸檔] 過期 {file_type} ({code}) -> archive/")
            else:
                os.remove(file_path)
                print(f" ❌ [刪除] 過期 {file_type} ({code})")
                
    mb_freed = bytes_freed / (1024 * 1024)
    action_str = "移動歸檔" if archive else "永久刪除"
    print(f"\n🎉 清理完成！共計 {action_str} {stale_count} 個失效的過期檔案，釋放空間：{mb_freed:.2f} MB")
    print("=========================================================")

if __name__ == "__main__":
    mode = "--audit"
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        
    active_list = load_current_active_tickers()
    
    if mode == "--audit":
        audit_active_models(active_list)
    elif mode == "--prune":
        prune_stale_models(active_list, archive=False)
    elif mode == "--archive":
        prune_stale_models(active_list, archive=True)
    else:
        print("使用說明：")
        print("  python manage_models.py --audit   : 稽核線上有效模型收斂度 (預設)")
        print("  python manage_models.py --archive : 歸檔失效的過期模型 (移至 archive/)")
        print("  python manage_models.py --prune   : 刪除失效的過期模型 (釋放硬碟空間)")
