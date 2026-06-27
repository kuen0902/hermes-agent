def format_stock_summary(chinese_name, symbol, price, prev_close, last_price=None):
    """
    Implements Compact Layout 2.0 (System Architect Style)
    """
    diff = price - prev_close
    pct = (diff / prev_close * 100) if prev_close > 0 else 0
    trend = "🔴" if diff > 0 else "🟢" if diff < 0 else "⚪"
    
    # Pricing Rules: Integer for >= 1000, 2 decimals for < 1000
    price_str = f"{price:,.0f}" if price >= 1000 else f"{price:,.2f}"
    pct_str = f"{pct:+.2f}%"
    
    # 10M Metric
    m10_part = ""
    if last_price is not None:
        d10 = price - last_price
        p10 = (d10 / last_price * 100) if last_price > 0 else 0
        t10_emoji = "▲" if d10 > 0 else "▼" if d10 < 0 else "•"
        m10_part = f" | 10M: {trend}{t10_emoji}{p10:+.2f}%"
    
    return f"{trend} **{chinese_name}** (`{symbol}`)\n   ▸ **{price_str}** ({pct_str}){m10_part}"
