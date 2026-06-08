#!/bin/bash
unset _HERMES_GATEWAY
/Users/bookid/.local/bin/hermes --profile star-platinum gateway start > /Users/bookid/.hermes/logs/gateway_cron.log 2>&1
