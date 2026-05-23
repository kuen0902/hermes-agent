#!/Users/bookid/.hermes/.venv/bin/python
import os
import json
import time
import glob
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import requests
import urllib3
from bs4 import BeautifulSoup
import concurrent.futures

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
SAVE_DIR = os.path.expanduser("~/Documents/StockData_History_5Y")
DATA_DIR = os.path.expanduser("~/.hermes/data")
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

ELIGIBLE_JSON_PATH = os.path.join(DATA_DIR, "eligible_5y_stocks.json")

def get_tw_stock_list():
    """Fetches all TWSE/TPEx stock symbols from ISIN page."""
    print("Fetching active stock list from TWSE/TPEx ISIN...")
    stocks = {}
    # Mode 2: Listed, Mode 4: OTC
    for mode in [2, 4]:
        url = f"https://isin.twse.com.tw/isin/C_public.jsp?strMode={mode}"
        try:
            response = requests.get(url, timeout=15, verify=False)
            response.encoding = 'big5'
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'class': 'h4'})
            if not table:
                continue
            for row in table.find_all('tr')[1:]:
                tds = row.find_all('td')
                if len(tds) < 1: 
                    continue
                text = tds[0].text.strip()
                # Pattern: "Code Name" e.g., "2330 台積電"
                parts = text.split('\u3000') # Wide space
                if len(parts) == 2:
                    code, name = parts
                    if len(code) == 4 and code.isdigit():
                        suffix = ".TW" if mode == 2 else ".TWO"
                        stocks[code + suffix] = name
        except Exception as e:
            print(f"Error fetching list for mode {mode}: {e}")
    return stocks

def download_and_filter():
    symbols_map = get_tw_stock_list()
    all_symbols = list(symbols_map.keys())
    print(f"Total symbols found in TWSE/TPEx: {len(all_symbols)}")

    # Time range: past 5 years (approx 1826 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365 + 10)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    print(f"Downloading historical range from {start_str} to {end_str}")

    # Process in chunks of 50 to avoid request overhead
    chunk_size = 50
    total_downloaded = 0
    
    # We will accumulate eligible stock stats
    # Criteria: 
    # 1. Start date must be <= 2021-05-28
    # 2. End date must be >= 2026-05-15 (active recently)
    # 3. Minimum trading days >= 800 (to filter out highly inactive or suspended stocks)
    cutoff_5yrs = datetime.strptime('2021-05-28', '%Y-%m-%d')
    cutoff_active = datetime.strptime('2026-05-15', '%Y-%m-%d')
    
    eligible_list = []
    
    for i in range(0, len(all_symbols), chunk_size):
        chunk = all_symbols[i:i+chunk_size]
        print(f"Downloading chunk {i//chunk_size + 1}/{len(all_symbols)//chunk_size + 1}: {chunk[0]} - {chunk[-1]}")
        
        try:
            # Download price data
            data = yf.download(chunk, start=start_str, end=end_str, group_by='ticker', threads=True, progress=False)
            
            for ticker in chunk:
                try:
                    # yfinance returns a single ticker dataframe directly if chunk size is 1,
                    # but since chunk size > 1, it returns multi-index
                    if len(chunk) > 1:
                        t_data = data[ticker].dropna(subset=['Close'])
                    else:
                        t_data = data.dropna(subset=['Close'])
                        
                    if t_data.empty or len(t_data) < 10:
                        continue
                    
                    t_data = t_data.reset_index()
                    t_data['Date'] = pd.to_datetime(t_data['Date'])
                    
                    start_t = t_data['Date'].min()
                    end_t = t_data['Date'].max()
                    num_days = len(t_data)
                    
                    # 5-Year Survivor Filter
                    if start_t <= cutoff_5yrs and end_t >= cutoff_active and num_days >= 800:
                        name = symbols_map.get(ticker, "").replace("/", "_")
                        file_path = os.path.join(SAVE_DIR, f"{ticker}_{name}.csv")
                        
                        # Save the historical CSV file
                        t_data.to_csv(file_path, index=False)
                        total_downloaded += 1
                        
                        # Compute liquidity: average daily trading value (Volume * Close) over the last 20 days
                        last_20_days = t_data.tail(20)
                        avg_volume_20 = last_20_days['Volume'].mean()
                        avg_price_20 = last_20_days['Close'].mean()
                        # Trading value in NTD (approximate)
                        avg_value_20 = avg_volume_20 * avg_price_20
                        
                        eligible_list.append({
                            "ticker": ticker,
                            "code": ticker.split('.')[0],
                            "name": name,
                            "market": "TWSE" if ticker.endswith(".TW") else "TPEx",
                            "start_date": start_t.strftime('%Y-%m-%d'),
                            "end_date": end_t.strftime('%Y-%m-%d'),
                            "trading_days": num_days,
                            "avg_price_20": float(avg_price_20),
                            "avg_volume_20": float(avg_volume_20),
                            "avg_value_20": float(avg_value_20)
                        })
                except Exception as e:
                    # Ignore individual ticker errors
                    pass
            
            # Brief sleep to avoid Yahoo rate limits
            time.sleep(1.5)
            
        except Exception as e:
            print(f"Error downloading chunk: {e}")
            time.sleep(5)

    print(f"\nPrice download completed. Total survivor stocks saved: {total_downloaded}")
    
    # Sort eligible list by daily trading value (liquidity) descending
    eligible_df = pd.DataFrame(eligible_list)
    if not eligible_df.empty:
        eligible_df = eligible_df.sort_values(by="avg_value_20", ascending=False).reset_index(drop=True)
        
        # Add rank and subset mark (Top 500)
        sorted_list = []
        for idx, row in eligible_df.iterrows():
            item = row.to_dict()
            item["liquidity_rank"] = idx + 1
            item["is_top_500"] = (idx < 500)
            sorted_list.append(item)
            
        with open(ELIGIBLE_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(sorted_list, f, indent=2, ensure_ascii=False)
            
        print(f"Eligible stock registry saved to {ELIGIBLE_JSON_PATH}")
        print(f"Total eligible stocks: {len(sorted_list)}")
        print(f"High-liquidity Top 500 stocks marked.")
    else:
        print("Error: No stocks met the 5-year survivor criteria.")

if __name__ == "__main__":
    download_and_filter()
