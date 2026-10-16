from .core import db_connect


def db_get_latest_snapshot(torn_user_id: int):
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        "SELECT * FROM battlestats_latest WHERE torn_user_id = ?",
        (torn_user_id,),
    )
    row = cur.fetchone()
    con.close()
    return row


def db_upsert_latest_snapshot(torn_user_id: int, stats: dict, updated_at_iso: str):
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO battlestats_latest (torn_user_id, updated_at, strength, speed, defense, dexterity, total)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(torn_user_id) DO UPDATE SET
            updated_at=excluded.updated_at,
            strength=excluded.strength,
            speed=excluded.speed,
            defense=excluded.defense,
            dexterity=excluded.dexterity,
            total=excluded.total
        """,
        (
            torn_user_id,
            updated_at_iso,
            stats["strength"],
            stats["speed"],
            stats["defense"],
            stats["dexterity"],
            stats["total"],
        ),
    )
    con.commit()
    con.close()


def db_delete_battlestats(torn_user_id: int):
    con = db_connect()
    cur = con.cursor()
    cur.execute("DELETE FROM battlestats_latest WHERE torn_user_id = ?", (torn_user_id,))
    con.commit()
    con.close()
