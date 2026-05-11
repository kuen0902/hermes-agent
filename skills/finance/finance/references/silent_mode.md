# Gateway Silent Mode Logic

## Overview
Silent mode is used to prevent an interactive AI personality (Gateway) from responding to messages during specific windows, while still allowing the system to send automated reports from the same identity.

## Lifecycle Commands (Star Platinum Example)

### 1. Enable Silent Mode (Stop interaction)
Execute this via cron before the market opens.
```bash
# Pattern 1: Force kill by process name (Robust)
pkill -f "hermes --profile star-platinum gateway run"

# Pattern 2: Graceful stop via service (If installed as service)
hermes --profile star-platinum gateway stop
```

### 2. Disable Silent Mode (Restore interaction)
Execute this via cron after market close.
```bash
# Must use background: true in terminal tool or nohup in shell
hermes --profile star-platinum gateway run
```

## Troubleshooting
If the gateway fails to start after a silent window:
1. Check the logs: `tail -n 50 ~/.hermes/profiles/star-platinum/logs/gateway.log`.
2. Check for zombie PIDs: `ps aux | grep hermes`.
3. Reset systemd failed state if applicable: `systemctl --user reset-failed hermes-gateway-star-platinum`.
