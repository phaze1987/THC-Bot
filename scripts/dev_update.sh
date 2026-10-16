#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/apps/thc-bot
git checkout main
if [ -n "$(git status --porcelain)" ]; then
echo "ERROR: Working tree is dirty. Commit/stash changes before updating."
git status --porcelain
exit 1
fi
git pull
docker compose build bot-dev
docker compose up -d bot-dev
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"