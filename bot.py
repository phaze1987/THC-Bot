import os
import sqlite3
import hashlib
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from cryptography.fernet import Fernet
import base64
from datetime import datetime

# ----------------------------
# ENV / CONFIG
# ----------------------------
TOKEN = os.getenv("DISCORD_TOKEN")
DEV_GUILD_ID = int(os.getenv("DEV_GUILD_ID", "0") or "0")
DB_PATH = os.getenv("DB_PATH", "/app/data/tornbot.sqlite3")
KEY_ENCRYPTION_SECRET = os.getenv("KEY_ENCRYPTION_SECRET", "")

TORN_BASE_URL = "https://api.torn.com/user/"
TORN_COMMENT = "TornAPI"

WIPE_COMMANDS = os.getenv("WIPE_COMMANDS", "0") == "1"

def parse_id_set(raw: str) -> set[int]:
    if not raw:
        return set()
    out = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        out.add(int(part))
    return out

ADMIN_ROLE_IDS = parse_id_set(os.getenv("ADMIN_ROLE_IDS", ""))

# ----------------------------
# Encryption (Linux-safe)
# Fernet requires a 32-byte urlsafe base64 key.
# We derive one from KEY_ENCRYPTION_SECRET.
# ----------------------------
def _fernet() -> Fernet:
    if not KEY_ENCRYPTION_SECRET or len(KEY_ENCRYPTION_SECRET) < 16:
        raise RuntimeError("KEY_ENCRYPTION_SECRET is missing/too short. Set it in .env (16+ chars, ideally 32+).")
    digest = hashlib.sha256(KEY_ENCRYPTION_SECRET.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return Fernet(fernet_key)

def encrypt_api_key(api_key: str) -> bytes:
    return _fernet().encrypt(api_key.encode("utf-8"))

def decrypt_api_key(ciphertext: bytes) -> str:
    return _fernet().decrypt(ciphertext).decode("utf-8")

# ----------------------------
# DB
# ----------------------------
def db_connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def db_init():
    con = db_connect()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        discord_user_id INTEGER PRIMARY KEY,
        torn_api_key_encrypted BLOB NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # Latest battlestats snapshot per user (for /bs deltas)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS battlestats_latest (
        discord_user_id INTEGER PRIMARY KEY,
        updated_at TEXT NOT NULL,
        strength INTEGER NOT NULL,
        speed INTEGER NOT NULL,
        defense INTEGER NOT NULL,
        dexterity INTEGER NOT NULL,
        total INTEGER NOT NULL
    )
    """)

    con.commit()
    con.close()

def db_get_user_api_key(discord_user_id: int) -> str | None:
    con = db_connect()
    cur = con.cursor()
    cur.execute("SELECT torn_api_key_encrypted FROM users WHERE discord_user_id = ?", (discord_user_id,))
    row = cur.fetchone()
    con.close()
    if not row:
        return None
    return decrypt_api_key(row["torn_api_key_encrypted"])

def db_get_latest_snapshot(discord_user_id: int):
    con = db_connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM battlestats_latest WHERE discord_user_id = ?", (discord_user_id,))
    row = cur.fetchone()
    con.close()
    return row

def db_upsert_latest_snapshot(discord_user_id: int, stats: dict, updated_at_iso: str):
    con = db_connect()
    cur = con.cursor()
    cur.execute("""
    INSERT INTO battlestats_latest (discord_user_id, updated_at, strength, speed, defense, dexterity, total)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(discord_user_id) DO UPDATE SET
        updated_at=excluded.updated_at,
        strength=excluded.strength,
        speed=excluded.speed,
        defense=excluded.defense,
        dexterity=excluded.dexterity,
        total=excluded.total
    """, (
        discord_user_id,
        updated_at_iso,
        stats["strength"],
        stats["speed"],
        stats["defense"],
        stats["dexterity"],
        stats["total"],
    ))
    con.commit()
    con.close()

# ----------------------------
# Torn API
# ----------------------------
async def torn_fetch_battlestats(api_key: str) -> dict:
    params = {
        "key": api_key,
        "comment": TORN_COMMENT,
        "selections": "battlestats"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(TORN_BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            data = await resp.json()

    if "error" in data:
        err = data["error"]
        raise RuntimeError(f"{err.get('error')} (code {err.get('code')})")

    bs = data.get("battlestats")
    if not isinstance(bs, dict):
        raise RuntimeError("Torn response missing 'battlestats'")

    # Normalise + compute total ourselves
    strength = int(bs.get("strength", 0))
    speed = int(bs.get("speed", 0))
    defense = int(bs.get("defense", 0))
    dexterity = int(bs.get("dexterity", 0))
    total = strength + speed + defense + dexterity

    return {
        "strength": strength,
        "speed": speed,
        "defense": defense,
        "dexterity": dexterity,
        "total": total,
    }

# ----------------------------
# Bot
# ----------------------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def is_admin_member(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    role_ids = {r.id for r in member.roles}
    return len(role_ids.intersection(ADMIN_ROLE_IDS)) > 0

@bot.event
async def on_ready():
    db_init()

    # Sync slash commands
    WIPE_COMMANDS = os.getenv("WIPE_COMMANDS", "0") == "1"

    if DEV_GUILD_ID:
        guild = discord.Object(id=DEV_GUILD_ID)

        if WIPE_COMMANDS:
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f"WIPED guild commands for {DEV_GUILD_ID}. Set WIPE_COMMANDS=0 and restart.")
            return

        await bot.tree.sync(guild=guild)
        cmds = await bot.tree.fetch_commands(guild=guild)
        print("Guild commands after sync:", [c.name for c in cmds])
        print(f"Synced commands to dev guild {DEV_GUILD_ID}.")
    else:
        await bot.tree.sync()
        print("Synced commands globally (may take a few minutes to appear).")

    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.tree.command(name="ping", description="Check if the bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

@bot.tree.command(name="hello", description="Say hello")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hello, {interaction.user.mention}!")

@bot.tree.command(name="register", description="Register your Torn API key (stored securely)")
async def register(interaction: discord.Interaction, api_key: str):
    await interaction.response.defer(ephemeral=True)

    api_key = (api_key or "").strip()
    if len(api_key) < 10:
        await interaction.followup.send("That doesn’t look like a valid API key. Try again.", ephemeral=True)
        return

    # Validate against Torn
    try:
        stats = await torn_fetch_battlestats(api_key)
    except Exception as e:
        await interaction.followup.send(f"Registration failed: {e}", ephemeral=True)
        return

    enc = encrypt_api_key(api_key)

    con = db_connect()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO users (discord_user_id, torn_api_key_encrypted, created_at, updated_at)
        VALUES (?, ?, datetime('now'), datetime('now'))
        ON CONFLICT(discord_user_id) DO UPDATE SET
            torn_api_key_encrypted=excluded.torn_api_key_encrypted,
            updated_at=datetime('now')
    """, (interaction.user.id, enc))
    con.commit()
    con.close()

    await interaction.followup.send(
        f"Registered successfully. Torn battlestats validated.\nCurrent total: {stats['total']:,}",
        ephemeral=True
    )

@bot.tree.command(name="bs", description="Update and show your battle stat gains since last update")
async def bs(interaction: discord.Interaction):
    # Public response (as requested)
    await interaction.response.defer(thinking=True)

    api_key = db_get_user_api_key(interaction.user.id)
    if not api_key:
        await interaction.followup.send("No API key registered. Use /register first.", ephemeral=True)
        return

    try:
        current = await torn_fetch_battlestats(api_key)
    except Exception as e:
        await interaction.followup.send(f"Failed to fetch battlestats: {e}", ephemeral=True)
        return

    prev = db_get_latest_snapshot(interaction.user.id)
    now_iso = datetime.now().isoformat(timespec="seconds")

    if prev is None:
        db_upsert_latest_snapshot(interaction.user.id, current, now_iso)
        msg = (
            f"**Battle Stats Update** ({interaction.user.mention})\n"
            f"First snapshot saved.\n"
            f"STR {current['strength']:,}; SPD {current['speed']:,}; DEF {current['defense']:,}; DEX {current['dexterity']:,}; "
            f"TOTAL {current['total']:,}\n"
            f"Last updated: *none* → {now_iso}"
        )
        await interaction.followup.send(msg)
        return

    d_str = current["strength"] - int(prev["strength"])
    d_spd = current["speed"] - int(prev["speed"])
    d_def = current["defense"] - int(prev["defense"])
    d_dex = current["dexterity"] - int(prev["dexterity"])
    d_total = current["total"] - int(prev["total"])

    last_at = prev["updated_at"]

    db_upsert_latest_snapshot(interaction.user.id, current, now_iso)

    msg = (
        f"**Battle Stats Update** ({interaction.user.mention})\n"
        f"Last updated: {last_at}\n"
        f"Now: STR {current['strength']:,}; SPD {current['speed']:,}; DEF {current['defense']:,}; DEX {current['dexterity']:,}; TOTAL {current['total']:,}\n"
        f"Change: STR {d_str:+,}; SPD {d_spd:+,}; DEF {d_def:+,}; DEX {d_dex:+,}; TOTAL {d_total:+,}\n"
        f"Updated at: {now_iso}"
    )
    await interaction.followup.send(msg)

@bot.tree.command(name="view_bs", description="(Admin) View a user's current battlestats")
@app_commands.describe(user="User to view")
async def view_bs(interaction: discord.Interaction, user: discord.Member):
    # Admin-only; keep response private to avoid drama/leaks
    if not isinstance(interaction.user, discord.Member) or not is_admin_member(interaction.user):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)

    api_key = db_get_user_api_key(user.id)
    if not api_key:
        await interaction.followup.send(f"{user.mention} has not registered an API key.", ephemeral=True)
        return

    try:
        current = await torn_fetch_battlestats(api_key)
    except Exception as e:
        await interaction.followup.send(f"Failed to fetch battlestats for {user.mention}: {e}", ephemeral=True)
        return

    msg = (
        f"**Battle Stats (Admin View)**\n"
        f"User: {user.mention}\n"
        f"STR {current['strength']:,}; SPD {current['speed']:,}; DEF {current['defense']:,}; DEX {current['dexterity']:,}; TOTAL {current['total']:,}"
    )
    await interaction.followup.send(msg, ephemeral=True)

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set in .env")

bot.run(TOKEN)
