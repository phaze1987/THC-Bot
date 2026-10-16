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
docker build -t thcbot:prod-$SHA .
sed -i "s/^PROD_TAG=.*/PROD_TAG=$SHA/" .env.compose
cat .env.compose
docker compose --env-file .env.compose up -d bot-prod
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
echo "Pruning old prod images (keeping latest $KEEP_PROD_IMAGES)…"
docker images --format "{{.Repository}}:{{.Tag}} {{.CreatedAt}}" \
| grep '^thcbot:prod-' \
| sort -r \
| awk -v keep="$KEEP_PROD_IMAGES" 'NR>keep {print $1}' \
| xargs -r docker rmi