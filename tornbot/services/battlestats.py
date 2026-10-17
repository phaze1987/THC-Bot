from datetime import datetime, timezone
import sqlite3
from typing import Any

from ..db import db_get_latest_snapshot, db_upsert_latest_snapshot
from ..torn_api.user import fetch_battlestats


def now_iso_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC")


async def fetch_and_snapshot(torn_user_id: int, api_key: str) -> tuple[dict[str, Any], sqlite3.Row | None, str]:
    current = await fetch_battlestats(api_key)
    prev = db_get_latest_snapshot(torn_user_id)
    ts = now_iso_utc()
    db_upsert_latest_snapshot(torn_user_id, current, ts)
    return current, prev, ts
