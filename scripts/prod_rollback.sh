#!/usr/bin/env bash
set -euo pipefail
if [ $# -ne 1 ]; then
echo "Usage: $0 <oldsha>"
exit 1
fi
OLD_SHA="$1"
cd /home/ubuntu/apps/thc-bot
CURRENT_TAG=$(grep '^PROD_TAG=' .env.compose | cut -d'=' -f2 || true)
if [ "$CURRENT_TAG" = "$OLD_SHA" ]; then
echo "No-op: PROD_TAG is already $OLD_SHA. Nothing to roll back."
exit 0
fi