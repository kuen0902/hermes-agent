import json
import os

def generate_categorized_report(categories, market_data, mapping):
    """
    Template for generating categorized messages.
    categories: {"Category Name": ["ticker1", "ticker2"]}
    market_data: {"ticker": {"price": 100, "pct": 1.5, ...}}
    """
    category_lines = {cat: [] for cat in categories}
    
    for cat, tickers in categories.items():
        for ticker in tickers:
            data = market_data.get(ticker)
            if data:
                name = mapping.get(ticker, ticker)
                trend = "🔴" if data['pct'] > 0 else "🟢" if data['pct'] < 0 else "⚪"
                line = f"{trend} **{name}** (`{ticker}`)\n   ▸ **{data['price']}** ({data['pct']:+.2f}%)\n"
                category_lines[cat].append(line)
    
    body = ""
    for cat, lines in category_lines.items():
        if lines:
            body += f"📌 **{cat}**\n" + "".join(lines) + "\n"
    return body
