import json
import os
from typing import Any

TORN_BASE_URL = os.getenv("TORN_BASE_URL", "https://api.torn.com/v2")

# Secrets (env only)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
KEY_ENCRYPTION_SECRET = os.getenv("KEY_ENCRYPTION_SECRET", "")

# Environment selector (env only)
BOT_ENV = os.getenv("BOT_ENV", "prod").strip().lower()
if BOT_ENV not in ("dev", "prod"):
    BOT_ENV = "prod"


def _load_runtime_config() -> dict[str, Any]:
    path = f"config.runtime.{BOT_ENV}.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {path}: {e}") from e


_RUNTIME = _load_runtime_config()


def _env_present(key: str) -> bool:
    return os.getenv(key) is not None


def _get_runtime_str(key: str, default: str = "") -> str:
    # Env overrides JSON; JSON overrides default
    v = os.getenv(key)
    if v is not None:
        return v
    v2 = _RUNTIME.get(key, default)
    return str(v2) if v2 is not None else default


def _get_runtime_int(key: str, default: int = 0) -> int:
    raw = _get_runtime_str(key, str(default)).strip()
    if raw == "":
        return default
    return int(raw)


def _get_runtime_bool(key: str, default: bool = False) -> bool:
    raw = _get_runtime_str(key, "1" if default else "0").strip().lower()
    if raw in ("1", "true", "yes", "y", "on"):
        return True
    if raw in ("0", "false", "no", "n", "off", ""):
        return False
    raise ValueError(f"{key} must be boolean-like, got: {raw!r}")


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


def _parse_id_list(value: Any) -> list[int]:
    """
    Accepts:
      - JSON list: [1,2,3]
      - JSON string: "1,2,3"
      - None / missing -> []
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [int(x) for x in value]
    if isinstance(value, str):
        return sorted(parse_id_set(value))
    raise TypeError(f"Expected list[int] or comma-string, got {type(value).__name__}")


# Non-secret runtime config (JSON, with env override)
DEV_GUILD_ID = _get_runtime_int("DEV_GUILD_ID", 0)
DB_PATH = _get_runtime_str("DB_PATH", "/app/data/tornbot.sqlite3")
WIPE_COMMANDS = _get_runtime_bool("WIPE_COMMANDS", False)

# Admin roles: prefer env override if present, else JSON list
if _env_present("ADMIN_ROLE_IDS"):
    ADMIN_ROLE_IDS = parse_id_set(os.getenv("ADMIN_ROLE_IDS", ""))
else:
    ADMIN_ROLE_IDS = set(_parse_id_list(_RUNTIME.get("ADMIN_ROLE_IDS")))

# Channels: JSON dict (optional). Keys are your Discord channel names (without #).
raw_channels = _RUNTIME.get("CHANNEL_IDS", {})
if raw_channels is None:
    raw_channels = {}
if not isinstance(raw_channels, dict):
    raise TypeError("CHANNEL_IDS must be an object/dict in runtime JSON")

CHANNEL_IDS: dict[str, int] = {str(k): int(v) for k, v in raw_channels.items()}


def channel_id(name: str) -> int:
    """
    Convenience helper: returns channel id for a given name, or 0 if not configured.
    Example: channel_id("welcome")
    """
    return int(CHANNEL_IDS.get(name, 0))


def channel_mention(name: str) -> str:
    cid = channel_id(name)
    return f"<#{cid}>" if cid > 0 else f"#{name}"
