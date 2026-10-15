import sqlite3
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
