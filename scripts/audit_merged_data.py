import os
import pandas as pd
from datetime import datetime

DATA_DIR = os.path.expanduser("~/Documents/StockData_History_Final")
REPORT_PATH = os.path.expanduser("~/Documents/StockData_Health_Report.csv")

def audit_data():
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    report_data = []
    anomalies = []

    print(f"Auditing {len(files)} files...")

    for i, filename in enumerate(files):
        path = os.path.join(DATA_DIR, filename)
        try:
            df = pd.read_csv(path)
            if df.empty:
                anomalies.append({"file": filename, "issue": "Empty File"})
                continue
            
            # Ensure Date is datetime
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
            
            start_date = df['Date'].min()
            end_date = df['Date'].max()
            row_count = len(df)
            
            # Check for missing values in core columns
            missing = df.isnull().sum().sum()
            
            # Check for date gaps (> 10 days to be conservative for long holidays)
            df['diff'] = df['Date'].diff().dt.days
            max_gap = df['diff'].max()
            
            report_data.append({
                "Symbol_Name": filename,
                "Start": start_date.strftime('%Y-%m-%d'),
                "End": end_date.strftime('%Y-%m-%d'),
                "Rows": row_count,
                "Missing_Values": missing,
                "Max_Gap_Days": max_gap
            })
            
            if missing > 0 or max_gap > 15:
                anomalies.append({
                    "file": filename, 
                    "issue": f"MissingVals: {missing}, MaxGap: {max_gap} days"
                })

        except Exception as e:
            anomalies.append({"file": filename, "issue": f"Error: {str(e)}"})

        if (i + 1) % 500 == 0:
            print(f"Processed {i + 1}/{len(files)}...")

    # Save full report
    report_df = pd.DataFrame(report_data)
    report_df.to_csv(REPORT_PATH, index=False)
    
    print("\n--- Audit Summary ---")
    print(f"Total Files Audited: {len(files)}")
    print(f"Healthy Files (No metadata errors): {len(report_data)}")
    print(f"Total Anomalies Detected: {len(anomalies)}")
    
    if anomalies:
        print("\n--- Top 5 Anomalies ---")
        for a in anomalies[:5]:
            print(f"  - {a['file']}: {a['issue']}")
    
    print(f"\nFull report saved to: {REPORT_PATH}")

if __name__ == "__main__":
    audit_data()
