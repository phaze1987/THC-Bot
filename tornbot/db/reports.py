from .core import db_connect


def db_get_unlinked_members(limit: int = 25):
    """
    Members who exist in discord_members but have no discord_links row.
    """
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        """
        SELECT m.discord_user_id, m.joined_at
        FROM discord_members m
        LEFT JOIN discord_links l
            ON l.discord_user_id = m.discord_user_id
        WHERE l.discord_user_id IS NULL
        ORDER BY m.joined_at DESC
        LIMIT ?
        """,
        (int(limit),),
    )
    rows = cur.fetchall()
    con.close()
    return rows
