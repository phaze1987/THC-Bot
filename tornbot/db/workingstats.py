from .core import db_connect


def db_get_latest_workingstats(torn_user_id: int):
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        "SELECT * FROM workingstats_latest WHERE torn_user_id = ?",
        (torn_user_id,),
    )
    row = cur.fetchone()
    con.close()
    return row


def db_upsert_latest_workingstats(torn_user_id: int, ws: dict, updated_at_iso: str):
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO workingstats_latest (
            torn_user_id, updated_at, manual_labor, intelligence, endurance, total
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(torn_user_id) DO UPDATE SET
            updated_at=excluded.updated_at,
            manual_labor=excluded.manual_labor,
            intelligence=excluded.intelligence,
            endurance=excluded.endurance,
            total=excluded.total
        """,
        (
            torn_user_id,
            updated_at_iso,
            int(ws["manual_labor"]),
            int(ws["intelligence"]),
            int(ws["endurance"]),
            int(ws["total"]),
        ),
    )
    con.commit()
    con.close()
