from ..db import db_upsert_discord_member, db_touch_last_seen
from datetime import datetime, timezone

def now_iso_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC")

def touch_member(discord_user_id: int):
    ts = now_iso_utc()
    db_upsert_discord_member(discord_user_id, ts)
    db_touch_last_seen(discord_user_id, ts)
