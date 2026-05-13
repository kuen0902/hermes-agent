# Night Session Network Stability: Root Causes & Fixes

Detected and resolved during May 13, 2026 session.

## 1. The "Hanging Script" Syndrome
**Failure**: Monitoring scripts (e.g., `stock_monitor.py`) stop sending updates despite the process still being alive.
**Root Cause**: `urllib.request.urlopen` without an explicit `timeout` parameter. In cases of network jitter or ISP connection resets (common in late-night maintenance windows), the socket enters a "half-open" state, and the Python thread waits indefinitely.

**The Fix (urllib)**:
```python
# Force a 10s timeout to allow the script to exit/retry
with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
    return response.status == 200
```

## 2. DNS Jitter induction
**Failure**: Intermittent "Address not found" or slow connection initiation (Jitter > 4ms).
**Root Cause**: ISP default DNS servers undergoing maintenance or being under-resourced during graveyard shifts.
**The Fix**: Use high-availability DNS.
```bash
networksetup -setdnsservers Wi-Fi 8.8.8.8 1.1.1.1
```

## 3. macOS Sleep/Nap Interference
**Failure**: Network hardware enters low-power state.
**The Fix**: Use `caffeinate` wrapper for all night-session monitoring.
```bash
caffeinate -ism python3 script_name.py
```
