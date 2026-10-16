from .core import db_connect


def db_link_discord_to_torn_takeover(discord_user_id: int, torn_user_id: int):
    """
    Enforces 1:1 mapping with takeover:
    - If this discord_user_id was linked to another torn_user_id, replace it.
    - If this torn_user_id was linked to another discord_user_id, replace it.
    """
    con = db_connect()
    cur = con.cursor()

    # Remove any existing mapping for either side
    cur.execute("DELETE FROM discord_links WHERE discord_user_id = ?", (discord_user_id,))
    cur.execute("DELETE FROM discord_links WHERE torn_user_id = ?", (torn_user_id,))

    # Insert new mapping
    cur.execute(
        """
        INSERT INTO discord_links (discord_user_id, torn_user_id, linked_at)
        VALUES (?, ?, datetime('now'))
        """,
        (discord_user_id, torn_user_id),
    )

    con.commit()
    con.close()


def db_get_torn_id_for_discord(discord_user_id: int) -> int | None:
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        "SELECT torn_user_id FROM discord_links WHERE discord_user_id = ?",
        (discord_user_id,),
    )
    row = cur.fetchone()
    con.close()
    if not row:
        return None
    return int(row["torn_user_id"])


def db_delete_link_for_discord(discord_user_id: int) -> int | None:
    """
    Deletes the link row for a discord user; returns torn_user_id if one existed.
    """
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        "SELECT torn_user_id FROM discord_links WHERE discord_user_id = ?",
        (discord_user_id,),
    )
    row = cur.fetchone()

    cur.execute("DELETE FROM discord_links WHERE discord_user_id = ?", (discord_user_id,))
    con.commit()
    con.close()

    if not row:
        return None
    return int(row["torn_user_id"])
