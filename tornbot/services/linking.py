from ..crypto import encrypt_api_key
from ..db import db_connect
from ..torn_api.user import fetch_identity

def validate_api_key_format(api_key: str) -> str:
    api_key = (api_key or "").strip()
    if len(api_key) != 16:
        raise ValueError("Invalid key format. Torn API keys are 16 characters.")
    return api_key

def upsert_linked_user(discord_user_id: int, api_key: str, ident: dict):
    enc = encrypt_api_key(api_key)

    con = db_connect()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO users (
            discord_user_id,
            torn_api_key_encrypted,
            torn_user_id,
            torn_username,
            linked_at,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
        ON CONFLICT(discord_user_id) DO UPDATE SET
            torn_api_key_encrypted=excluded.torn_api_key_encrypted,
            torn_user_id=excluded.torn_user_id,
            torn_username=excluded.torn_username,
            linked_at=datetime('now'),
            updated_at=datetime('now')
        """,
        (discord_user_id, enc, ident["torn_user_id"], ident["torn_username"]),
    )
    con.commit()
    con.close()

async def register_user(discord_user_id: int, api_key: str) -> tuple[dict, str]:
    api_key = validate_api_key_format(api_key)
    ident = await fetch_identity(api_key)
    upsert_linked_user(discord_user_id, api_key, ident)
    return ident, api_key

