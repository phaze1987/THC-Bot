from ..crypto import encrypt_api_key
from ..torn_api.user import fetch_identity
from ..db import db_upsert_torn_user, db_link_discord_to_torn_takeover


def validate_api_key_format(api_key: str) -> str:
    api_key = (api_key or "").strip()
    if len(api_key) != 16:
        raise ValueError("Invalid key format. Torn API keys are 16 characters.")
    return api_key


async def register_user(discord_user_id: int, api_key: str) -> tuple[dict, str]:
    api_key = validate_api_key_format(api_key)
    ident = await fetch_identity(api_key)

    enc = encrypt_api_key(api_key)
    torn_user_id = int(ident["torn_user_id"])
    torn_username = str(ident["torn_username"])

    db_upsert_torn_user(torn_user_id, torn_username, enc)
    db_link_discord_to_torn_takeover(discord_user_id, torn_user_id)

    return ident, api_key
