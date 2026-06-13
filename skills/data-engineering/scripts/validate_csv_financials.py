import os
import pandas as pd
from datetime import datetime, timedelta

def validate_stock_csv(file_path, min_size_kb=1, min_rows=5, max_latency_days=7):
    """
    Robust validation for financial CSV data.
    """
    results = {"valid": True, "errors": [], "warnings": []}
    
    # 1. Existence and Size
    if not os.path.exists(file_path):
        results["valid"] = False
        results["errors"].append("File does not exist")
        return results
        
    size_kb = os.path.getsize(file_path) / 1024
    if size_kb < min_size_kb:
        results["valid"] = False
        results["errors"].append(f"File too small: {size_kb:.2f} KB (min {min_size_kb} KB)")
        
    try:
        # 2. Parse and Empty Check
        df = pd.read_csv(file_path)
        if df.empty:
            results["valid"] = False
            results["errors"].append("CSV is empty")
            return results
            
        # 3. Content validaton (dropna)
        df_clean = df.dropna()
        if len(df_clean) < min_rows:
            results["valid"] = False
            results["errors"].append(f"Insufficient data rows: {len(df_clean)} (min {min_rows})")

        # 4. Latency Check
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            last_date = df['Date'].max()
            if last_date < (datetime.now() - timedelta(days=max_latency_days)):
                results["warnings"].append(f"Data latency: Last date is {last_date.strftime('%Y-%m-%d')}")
        else:
            results["errors"].append("Missing 'Date' column")
            results["valid"] = False

    except Exception as e:
        results["valid"] = False
        results["errors"].append(f"Parse error: {str(e)}")
        
    return results
