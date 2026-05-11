import os
import yfinance as yf
from datetime import datetime, timedelta

SAVE_DIR = os.path.expanduser("~/Documents/StockData_History")

def fetch_stock(ticker, start_date, end_date):
    """
    Downloads historical data for a ticker and saves as CSV.
    Include your health check here.
    """
    try:
        data = yf.download(ticker, start=start_date, end=end_date, group_by='ticker')
        if data.empty:
            return False, "No data"
        
        # Health Check: Ensure sufficient rows or date coverage
        expected_days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days
        actual_rows = len(data)
        health_score = actual_rows / (expected_days * 0.7) # Approx 5 trading days/7 total days
        
        if health_score < 0.8:
             return False, f"Gap detected: health score {health_score:.2f}"

        filename = os.path.join(SAVE_DIR, f"{ticker}.csv")
        data.to_csv(filename)
        return True, filename
    except Exception as e:
        return False, str(e)
