from .core import db_connect


def db_upsert_discord_member(discord_user_id: int, joined_at_iso: str):
    """
    Insert member if missing; do NOT overwrite joined_at if they already exist.
    Updates last_seen_at each time.
    """
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO discord_members (discord_user_id, joined_at, last_seen_at)
        VALUES (?, ?, ?)
        ON CONFLICT(discord_user_id) DO UPDATE SET
            last_seen_at=excluded.last_seen_at
        """,
        (discord_user_id, joined_at_iso, joined_at_iso),
    )
    con.commit()
    con.close()


def db_touch_last_seen(discord_user_id: int, seen_at_iso: str):
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        """
        UPDATE discord_members
        SET last_seen_at = ?
        WHERE discord_user_id = ?
        """,
        (seen_at_iso, discord_user_id),
    )
    con.commit()
    con.close()


def db_delete_discord_member(discord_user_id: int):
    con = db_connect()
    cur = con.cursor()
    cur.execute("DELETE FROM discord_members WHERE discord_user_id = ?", (discord_user_id,))
    con.commit()
    con.close()
