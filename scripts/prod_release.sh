#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/apps/thc-bot
KEEP_PROD_IMAGES=10
git checkout main
if [ -n "$(git status --porcelain)" ]; then
echo "ERROR: Working tree is dirty. Commit/stash changes before releasing."
git status --porcelain
exit 1
fi
git pull
SHA=$(git rev-parse --short HEAD)
echo "Releasing $SHA"
CURRENT_TAG=$(grep '^PROD_TAG=' .env.compose | cut -d'=' -f2 || true)
if [ "$CURRENT_TAG" = "$SHA" ]; then
echo "No-op: PROD_TAG is already $SHA. Nothing to deploy."
exit 0
fi
docker build -t thcbot:prod-$SHA .
sed -i "s/^PROD_TAG=.*/PROD_TAG=$SHA/" .env.compose
cat .env.compose
docker compose --env-file .env.compose up -d bot-prod
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
echo "Pruning old prod images (keeping latest $KEEP_PROD_IMAGES, and always keeping current prod image)…"