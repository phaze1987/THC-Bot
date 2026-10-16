THC Bot — Dev & Prod Deploy / Release Runbook

Overview
-This repo runs two Discord bot services via Docker Compose.
-Policy: deployments are built only from the main branch (we do not deploy from non-main branches).

Key idea:
-Dev is rebuilt whenever you pull new code.
-Prod is updated by building a new image tagged with the current git SHA, then updating PROD_TAG.

Services
-bot-dev
--Built from the current working tree
--Uses .env.dev
--Data stored in ./data-dev (mounted to /app/data)

-bot-prod
--Runs image thcbot:prod-${PROD_TAG}
--Uses .env.prod
--Data stored in ./data-prod (mounted to /app/data)

Prerequisites
-Run everything from the repo root on the VPS
--cd /home/ubuntu/apps/thc-bot
-These files must exist on the VPS and must not be committed to git
--.env.dev
--.env.prod
--.env.compose (contains PROD_TAG=...)

##### SCRIPTED
DEV UPDATE
sudo /home/ubuntu/apps/thc-bot/scripts/dev_update.sh

PROD RELEASE
sudo /home/ubuntu/apps/thc-bot/scripts/prod_release.sh

PROD ROLLBACK

List all PROD versions
docker images "thcbot" --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}"

List current version
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

Using TAG above to rollback
sudo /home/ubuntu/apps/thc-bot/scripts/prod_rollback.sh <TAG>

View SCRIPT
sed -n '1,200p' /home/ubuntu/apps/thc-bot/scripts/<NAME>.sh


##### MANUAL
DEV — Update (pull, rebuild, restart)
-Step 1 — Ensure you are on main and pull latest
--git checkout main
--git pull
-Step 2 — Rebuild and restart only dev
--docker compose build bot-dev
--docker compose up -d bot-dev
-Step 3 — Verify status
--docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

PROD — Release (build a pinned SHA image and deploy it)
-Step 1 — Ensure you are on main, pull latest, and capture the SHA
--git checkout main
--git pull
--SHA=$(git rev-parse --short HEAD)
--echo "Releasing $SHA"
-Step 2 — Build the prod image tagged with the SHA
--docker build -t thcbot:prod-$SHA .
-Step 3 — Update .env.compose to point prod at the new SHA
--sed -i "s/^PROD_TAG=.*/PROD_TAG=$SHA/" .env.compose
--cat .env.compose
-Step 4 — Restart only prod using the pinned tag
--docker compose --env-file .env.compose up -d bot-prod
-Step 5 — Verify prod is running the expected image
--docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

PROD — Rollback
-Set PROD_TAG back to a previous known-good SHA and restart prod
--sed -i "s/^PROD_TAG=.*/PROD_TAG=<oldsha>/" .env.compose
--docker compose --env-file .env.compose up -d bot-prod
--docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

Quick checks — Confirm dev/prod data separation
-Check bind mounts (dev and prod should point to different host folders)
--docker inspect thc-bot-bot-dev-1 --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
--docker inspect thc-bot-bot-prod-1 --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
-Expected bind mounts
--Dev: /home/ubuntu/apps/thc-bot/data-dev -> /app/data
--Prod: /home/ubuntu/apps/thc-bot/data-prod -> /app/data
-Check DB_PATH inside containers
--docker exec -i thc-bot-bot-dev-1 python -c "import os; print(os.getenv('DB_PATH'))"
--docker exec -i thc-bot-bot-prod-1 python -c "import os; print(os.getenv('DB_PATH'))"

Notes / gotchas
-On Ubuntu, python may not exist; use python3 on the host if needed.
-Avoid reusing a moving prod tag like bootstrap; prefer immutable SHA tags for easy rollback.
-Data lives in bind-mounted folders (data-dev, data-prod). Deploying new images should not affect data unless you manually move or overwrite these folders.

######################################################
##### Safe Commands
######################################################

Safe anytime (updates repo files only; does NOT change running containers)
-cd /home/ubuntu/apps/thc-bot
-git checkout main
-git pull

Notes:
-This updates the code on disk in /home/ubuntu/apps/thc-bot.
-Nothing running changes until you rebuild/restart a service.

Safe for DEV only (applies the latest pulled code to the dev bot)
-cd /home/ubuntu/apps/thc-bot
-docker compose build bot-dev
-docker compose up -d bot-dev

Optional check:
-docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

PROD release only (this is what actually updates production)
-cd /home/ubuntu/apps/thc-bot
-git checkout main
-git pull
-SHA=$(git rev-parse --short HEAD)
-docker build -t thcbot:prod-$SHA .
-sed -i "s/^PROD_TAG=.*/PROD_TAG=$SHA/" .env.compose
-docker compose --env-file .env.compose up -d bot-prod

Optional check:
-docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

PROD rollback only (switch prod back to an older image)
-cd /home/ubuntu/apps/thc-bot
-sed -i "s/^PROD_TAG=.*/PROD_TAG=<oldsha>/" .env.compose
-docker compose --env-file .env.compose up -d bot-prod
-docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

One rule to keep prod safe
Do NOT run: docker compose up -d --build bot-prod
Do NOT add: build: to the bot-prod service in docker-compose.yml