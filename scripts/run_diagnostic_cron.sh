#!/bin/bash
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:$PATH"

echo "=== Running Morning Diagnostic Gatekeeper ==="
# Run the diagnostic script in auto-heal mode
RESULT=$(/usr/bin/swift /Users/bookid/.hermes/scripts/hermes_diagnostic.swift --auto-heal)
EXIT_CODE=$?

# Fetch TELEGRAM_BOT_TOKEN and TELEGRAM_HOME_CHANNEL from .env
ENV_FILE="/Users/bookid/.hermes/.env"
if [ -f "$ENV_FILE" ]; then
    TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d '=' -f2)
    CHAT_ID=$(grep '^TELEGRAM_HOME_CHANNEL=' "$ENV_FILE" | cut -d '=' -f2)
fi

# Send message to Telegram
send_telegram() {
    local message="$1"
    if [ -n "$TOKEN" ] && [ -n "$CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
            -d "chat_id=${CHAT_ID}" \
            -d "text=${message}" \
            -d "parse_mode=Markdown" > /dev/null
    fi
}

if [ $EXIT_CODE -ne 0 ]; then
    echo "$RESULT"
    # Filter the critical failures to send to Telegram
    CRITICALS=$(echo "$RESULT" | grep "   - ")
    MESSAGE="🚨 *Hermes 開盤前診斷失敗 (自動修復無效)* 🚨%0A請立即登入系統檢查！%0A%0A*失敗項目:*%0A${CRITICALS}"
    send_telegram "$MESSAGE"
    exit 1
else
    # If successful and it performed an auto-heal, notify the user.
    if echo "$RESULT" | grep -q "\[自動修復\] 成功"; then
        HEALS=$(echo "$RESULT" | grep "\[自動修復\] 成功" | sed 's/   ✅ \[自動修復\] 成功: //g')
        MESSAGE="⚕️ *Hermes 晨間自癒完成* ⚕️%0A系統已在開盤前自動修復以下異常：%0A${HEALS}%0A%0A🌟 全鏈路完美健康，三語言協同架構運作正常！"
        send_telegram "$MESSAGE"
    else
        # Silent pass, or just a green light message
        MESSAGE="🟢 *Hermes 晨間診斷通過* 🟢%0A系統全鏈路完美健康，無須自動修復。準備迎接開盤！"
        send_telegram "$MESSAGE"
    fi
    echo "Diagnostic passed successfully."
    exit 0
fi
