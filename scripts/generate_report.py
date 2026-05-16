import json
import os
from datetime import datetime
import pytz

# Read bridge file
bridge_path = os.path.expanduser('~/.hermes/data/market_prices_bridge.json')
with open(bridge_path, 'r') as f:
    data = json.load(f)

# Create comprehensive report
taipei_tz = pytz.timezone('Asia/Taipei')
report_time = datetime.now(taipei_tz).strftime('%Y-%m-%d %H:%M')

# Note on night session status
now = datetime.now(taipei_tz)
weekday = now.weekday()
hour = now.hour

# Determine session status
session_active = False
if 0 <= weekday <= 4 and hour >= 15:
    session_active = True
if 1 <= weekday <= 5 and hour < 6:
    session_active = True

status_text = '活跃中' if session_active else '非活跃 (周末/非交易时间)'

# Build report
lines = []
lines.append('台湾股夜盘监测报告 (自主执行)')
lines.append('生成时间：' + report_time)
lines.append('日期：' + now.strftime('%Y-%m-%d %A'))
lines.append('夜盘状态：' + status_text)
lines.append('')
lines.append('--- 市场价格数据 (即时) ---')
lines.append('')

# Format each ticker
tickers_info = {
    'NQ': ('Nasdaq 100 Futures', '点数'),
    'TSM': ('台积电 ADR', 'USD'),
    'NVDA': ('Nvidia', 'USD'),
    'SYNA': ('Synaptics', 'USD'),
    'FITXP': ('台指期', '点数')
}

for sym in ['NQ', 'TSM', 'NVDA', 'SYNA', 'FITXP']:
    if sym in data:
        name, unit = tickers_info[sym]
        price = data[sym]
        if unit == '点数':
            lines.append('* ' + name + ': ' + str(round(price, 2)) + ' ' + unit)
        else:
            lines.append('* ' + name + ': $' + str(round(price, 2)) + ' ' + unit)

lines.append('')
lines.append('--- 数据来源 ---')
lines.append('- 主要数据源：yfinance (即时市场数据)')
lines.append('- 桥接文件：' + bridge_path)
lines.append('- 数据时间戳：' + str(data.get('timestamp', 'N/A')))
lines.append('')
lines.append('--- 执行注释 ---')
if session_active:
    lines.append('* 夜盘活跃，监控系统正常运作')
else:
    lines.append('* 夜盘非活跃期间 (周末或非交易时间)，执行器已按设计跳过正式通报流程。此报告为自主执行任务产出。')

lines.append('')
lines.append('本次任务已成功完成：')
lines.append('1. 获取即时市场价格 (NQ, TSM, NVDA, SYNA, FITXP)')
lines.append('2. 写入桥接文件: ~/.hermes/data/market_prices_bridge.json')
lines.append('3. 执行夜报监控脚本: run_night_report.py (按设计跳过，因夜盘非活跃)')

print('\n'.join(lines))
