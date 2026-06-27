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
    return str(code_str).replace(".TWO", "").replace(".TW", "").strip()

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

def prune_stale_models(active_tickers, archive=True, auto_confirm=False):
    """根據使用者政策，已全面停用自動封存與刪除模型的功能"""
    print("\n=========================================================")
    print(" 🛡️ 自動封存與清理功能已根據政策全面停用 ")
    print("=========================================================")
    print("為確保所有股票皆能參與全市場潛力股海選，系統不再執行任何封存或刪除動作。")
    print("所有的模型皆被永久保留在 models/ 資料夾中。")
    print("=========================================================")

if __name__ == "__main__":
    mode = "--audit"
    auto_confirm = False
    
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg == "--confirm":
                auto_confirm = True
            elif arg in ["--audit", "--prune", "--archive"]:
                mode = arg
        
    active_list = load_current_active_tickers()
    
    if mode == "--audit":
        audit_active_models(active_list)
    elif mode == "--prune":
        prune_stale_models(active_list, archive=False, auto_confirm=auto_confirm)
    elif mode == "--archive":
        prune_stale_models(active_list, archive=True, auto_confirm=auto_confirm)
    else:
        print("使用說明：")
        print("  python manage_models.py --audit   : 稽核線上有效模型收斂度 (預設)")
        print("  python manage_models.py --archive : 歸檔失效的過期模型 (移至 archive/)")
        print("  python manage_models.py --prune   : 刪除失效的過期模型 (釋放硬碟空間)")
        print("  附加參數:")
        print("  --confirm                         : 跳過互動式 y/n 詢問，直接執行 (適合自動排程使用)")
