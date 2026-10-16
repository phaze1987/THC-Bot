import sqlite3
from ..config import DB_PATH


def db_connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    # Helps avoid "database is locked" a bit with multiple quick writes
    con.execute("PRAGMA journal_mode=WAL;")
    return con


def db_init():
    con = db_connect()
    cur = con.cursor()

    # Discord membership tracking (non-sensitive)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS discord_members (
            discord_user_id INTEGER PRIMARY KEY,
            joined_at TEXT NOT NULL,
            last_seen_at TEXT
        )
        """
    )

    # Stable Torn identity + encrypted API key (sensitive)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS torn_users (
            torn_user_id INTEGER PRIMARY KEY,
            torn_username TEXT,
            torn_api_key_encrypted BLOB NOT NULL,
            linked_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    # One-to-one mapping (takeover model)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS discord_links (
            discord_user_id INTEGER PRIMARY KEY,
            torn_user_id INTEGER NOT NULL UNIQUE,
            linked_at TEXT NOT NULL,
            FOREIGN KEY (torn_user_id) REFERENCES torn_users(torn_user_id) ON DELETE CASCADE
        )
        """
    )

    # Battlestats keyed by TornID (stable)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS battlestats_latest (
            torn_user_id INTEGER PRIMARY KEY,
            updated_at TEXT NOT NULL,
            strength INTEGER NOT NULL,
            speed INTEGER NOT NULL,
            defense INTEGER NOT NULL,
            dexterity INTEGER NOT NULL,
            total INTEGER NOT NULL,
            FOREIGN KEY (torn_user_id) REFERENCES torn_users(torn_user_id) ON DELETE CASCADE
        )
        """
    )

    con.commit()
    con.close()
