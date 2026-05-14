#!/bin/bash
set -e
nohup hermes --profile star-platinum gateway start > /Users/bookid/.hermes/logs/gateway_cron.log 2>&1 &
