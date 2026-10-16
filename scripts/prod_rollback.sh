#!/usr/bin/env bash
set -euo pipefail
if [ $# -ne 1 ]; then
echo "Usage: $0 <oldsha>"
exit 1
fi
OLD_SHA="$1"
cd /home/ubuntu/apps/thc-bot
sed -i "s/^PROD_TAG=.*/PROD_TAG=$OLD_SHA/" .env.compose
cat .env.compose
docker compose --env-file .env.compose up -d bot-prod
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"