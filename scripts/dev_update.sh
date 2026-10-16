#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/apps/thc-bot
git checkout main
if ! git diff --quiet; then
  echo "ERROR: Tracked files have local modifications. Commit/stash before running."
  git --no-pager diff --name-only
  exit 1
fi
git pull
docker compose --env-file .env.compose build bot-dev
docker compose --env-file .env.compose up -d bot-dev
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
