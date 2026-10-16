import os

TORN_BASE_URL = os.getenv("TORN_BASE_URL", "https://api.torn.com/v2")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOT_ENV = os.getenv("BOT_ENV", "prod").strip().lower()

DEV_GUILD_ID = int(os.getenv("DEV_GUILD_ID", "0") or "0")
DB_PATH = os.getenv("DB_PATH", "/app/data/tornbot.sqlite3")

KEY_ENCRYPTION_SECRET = os.getenv("KEY_ENCRYPTION_SECRET", "")

WIPE_COMMANDS = os.getenv("WIPE_COMMANDS", "0") == "1"


def parse_id_set(raw: str) -> set[int]:
    if not raw:
        return set()
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        out.add(int(part))
    return out


ADMIN_ROLE_IDS = parse_id_set(os.getenv("ADMIN_ROLE_IDS", ""))
