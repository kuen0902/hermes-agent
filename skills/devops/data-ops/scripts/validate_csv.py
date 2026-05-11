import os
import pandas as pd

def validate_csv_health(file_path, required_columns=None, min_size_kb=1.0):
    """
    Validates CSV health for stock data.
    - Checks file existence and size.
    - Checks schema/columns.
    - Checks for empty data or missing values.
    """
    if not os.path.exists(file_path):
        return False, "File does not exist"
    
    if os.path.getsize(file_path) / 1024 < min_size_kb:
        return False, f"File too small ({os.path.getsize(file_path)/1024:.2f} KB)"

    try:
        df = pd.read_csv(file_path)
        if df.empty:
            return False, "CSV is empty"
        
        if required_columns:
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                return False, f"Missing columns: {missing}"
        
        # Check for catastrophic missing data (e.g., all prices NaN)
        if df.isnull().all().any():
             return False, "Contains completely empty columns"
             
        return True, "Healthy"
    except Exception as e:
        return False, f"Not a valid CSV: {str(e)}"
