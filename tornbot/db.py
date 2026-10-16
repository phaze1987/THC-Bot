import sqlite3
from datetime import datetime, timezone
from .config import DB_PATH
from .crypto import decrypt_api_key


def db_connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def db_init():
    con = db_connect()
    cur = con.cursor()


    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS discord_members (
        discord_user_id INTEGER PRIMARY KEY,
        joined_at TEXT NOT NULL,
        last_seen_at TEXT,
        left_at TEXT
    )
    """
    )


    cur.execute("PRAGMA table_info(discord_members)")
    dm_cols = {row[1] for row in cur.fetchall()}
    if "left_at" not in dm_cols:
        cur.execute("ALTER TABLE discord_members ADD COLUMN left_at TEXT")


    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        discord_user_id INTEGER PRIMARY KEY,
        torn_api_key_encrypted BLOB NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """
    )

    # Add columns if they don't exist (safe to run repeatedly)
    cur.execute("PRAGMA table_info(users)")
    cols = {row[1] for row in cur.fetchall()}

    if "torn_user_id" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN torn_user_id INTEGER")

    if "torn_username" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN torn_username TEXT")

    if "access_type" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN access_type TEXT")

    if "ff_api_key_encrypted" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN ff_api_key_encrypted BLOB")

    if "linked_at" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN linked_at TEXT")

    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS battlestats_latest (
        discord_user_id INTEGER PRIMARY KEY,
        updated_at TEXT NOT NULL,
        strength INTEGER NOT NULL,
        speed INTEGER NOT NULL,
        defense INTEGER NOT NULL,
        dexterity INTEGER NOT NULL,
        total INTEGER NOT NULL
    )
    """
    )

    con.commit()
    con.close()
    


def db_upsert_discord_member(discord_user_id: int, joined_at_iso: str):
    """
    Insert member if missing; do NOT overwrite joined_at if they already exist.
    Also clears left_at on join/rejoin.
    """
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO discord_members (discord_user_id, joined_at, last_seen_at, left_at)
        VALUES (?, ?, ?, NULL)
        ON CONFLICT(discord_user_id) DO UPDATE SET
            last_seen_at=excluded.last_seen_at,
            left_at=NULL
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


def db_get_unlinked_members(limit: int = 50):
    """
    Members who joined (discord_members) but do not have a linked Torn user (users).
    """
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        """
        SELECT dm.discord_user_id, dm.joined_at, dm.last_seen_at
        FROM discord_members dm
        LEFT JOIN users u ON u.discord_user_id = dm.discord_user_id
        WHERE u.discord_user_id IS NULL
        ORDER BY dm.joined_at ASC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    con.close()
    return rows


def db_get_user_api_key(discord_user_id: int) -> str | None:
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        "SELECT torn_api_key_encrypted FROM users WHERE discord_user_id = ?",
        (discord_user_id,),
    )
    row = cur.fetchone()
    con.close()
    if not row:
        return None
    return decrypt_api_key(row["torn_api_key_encrypted"])


def db_get_user_torn_identity(discord_user_id: int):
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        "SELECT torn_user_id, torn_username FROM users WHERE discord_user_id = ?",
        (discord_user_id,),
    )
    row = cur.fetchone()
    con.close()
    return row


def db_get_latest_snapshot(discord_user_id: int):
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        "SELECT * FROM battlestats_latest WHERE discord_user_id = ?",
        (discord_user_id,),
    )
    row = cur.fetchone()
    con.close()
    return row


def db_get_user(discord_user_id: int):
    con = db_connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE discord_user_id = ?", (discord_user_id,))
    row = cur.fetchone()
    con.close()
    return row


def db_unlink_user(discord_user_id: int) -> bool:
    con = db_connect()
    cur = con.cursor()

    cur.execute("DELETE FROM users WHERE discord_user_id = ?", (discord_user_id,))
    removed = cur.rowcount > 0

    cur.execute("DELETE FROM battlestats_latest WHERE discord_user_id = ?", (discord_user_id,))

    con.commit()
    con.close()
    return removed


def db_upsert_latest_snapshot(discord_user_id: int, stats: dict, updated_at_iso: str):
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        """
    INSERT INTO battlestats_latest (discord_user_id, updated_at, strength, speed, defense, dexterity, total)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(discord_user_id) DO UPDATE SET
        updated_at=excluded.updated_at,
        strength=excluded.strength,
        speed=excluded.speed,
        defense=excluded.defense,
        dexterity=excluded.dexterity,
        total=excluded.total
    """,
        (
            discord_user_id,
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


def db_mark_member_left(discord_user_id: int, left_at_iso: str):
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        """
        UPDATE discord_members
        SET left_at = ?, last_seen_at = ?
        WHERE discord_user_id = ?
        """,
        (left_at_iso, left_at_iso, discord_user_id),
    )
    con.commit()
    con.close()
