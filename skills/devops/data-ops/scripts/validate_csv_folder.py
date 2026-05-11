import os
import pandas as pd
import glob
import sys

def validate_folder(path, expected_count=None):
    files = glob.glob(os.path.join(path, "*.csv"))
    if not files:
        return False, "No CSV files found"
    
    if expected_count and len(files) < expected_count * 0.9:
        return False, f"File count too low: {len(files)} < {expected_count}"

    corrupt = []
    total_rows = 0
    
    for f in files:
        try:
            if os.path.getsize(f) < 100: # Min 100 bytes
                corrupt.append(f"{os.path.basename(f)} (Too small)")
                continue
            
            # Fast check
            df = pd.read_csv(f, nrows=5)
            if df.empty:
                 corrupt.append(f"{os.path.basename(f)} (Empty)")
        except Exception as e:
            corrupt.append(f"{os.path.basename(f)} (Load error: {str(e)})")

    health_rate = (len(files) - len(corrupt)) / len(files)
    status = health_rate >= 0.95
    
    report = {
        "path": path,
        "total": len(files),
        "healthy": len(files) - len(corrupt),
        "health_rate": f"{health_rate:.1%}",
        "corrupt_samples": corrupt[:5]
    }
    
    return status, report

if __name__ == "__main__":
    # Example usage
    if len(sys.argv) > 1:
        ok, res = validate_folder(sys.argv[1])
        print(res)
        sys.exit(0 if ok else 1)
