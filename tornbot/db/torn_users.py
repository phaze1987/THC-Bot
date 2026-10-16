from .core import db_connect
from ..crypto import decrypt_api_key


def db_upsert_torn_user(torn_user_id: int, torn_username: str, api_key_encrypted: bytes):
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO torn_users (
            torn_user_id, torn_username, torn_api_key_encrypted,
            linked_at, created_at, updated_at
        )
        VALUES (?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
        ON CONFLICT(torn_user_id) DO UPDATE SET
            torn_username=excluded.torn_username,
            torn_api_key_encrypted=excluded.torn_api_key_encrypted,
            linked_at=datetime('now'),
            updated_at=datetime('now')
        """,
        (torn_user_id, torn_username, api_key_encrypted),
    )
    con.commit()
    con.close()


def db_get_api_key_by_torn_id(torn_user_id: int) -> str | None:
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        "SELECT torn_api_key_encrypted FROM torn_users WHERE torn_user_id = ?",
        (torn_user_id,),
    )
    row = cur.fetchone()
    con.close()
    if not row:
        return None
    return decrypt_api_key(row["torn_api_key_encrypted"])


def db_delete_torn_user(torn_user_id: int):
    """
    Deletes the Torn user row (and cascades battlestats + link via FK if enabled).
    """
    con = db_connect()
    cur = con.cursor()
    cur.execute("DELETE FROM torn_users WHERE torn_user_id = ?", (torn_user_id,))
    con.commit()
    con.close()
