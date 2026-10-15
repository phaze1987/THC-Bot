import os
import sqlite3
import hashlib
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from cryptography.fernet import Fernet
import base64
from datetime import datetime, timezone

# ----------------------------
# ENV / CONFIG
# ----------------------------
TOKEN = os.getenv("DISCORD_TOKEN")
DEV_GUILD_ID = int(os.getenv("DEV_GUILD_ID", "0") or "0")
DB_PATH = os.getenv("DB_PATH", "/app/data/tornbot.sqlite3")
KEY_ENCRYPTION_SECRET = os.getenv("KEY_ENCRYPTION_SECRET", "")

TORN_BASE_URL = "https://api.torn.com/v2"

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

    # Add columns if they don't exist (safe to run repeatedly)
    cur.execute("PRAGMA table_info(users)")
    cols = {row[1] for row in cur.fetchall()}

    if "torn_user_id" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN torn_user_id INTEGER")

    if "torn_username" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN torn_username TEXT")

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

def db_get_user_torn_identity(discord_user_id: int):
    con = db_connect()
    cur = con.cursor()
    cur.execute("SELECT torn_user_id, torn_username FROM users WHERE discord_user_id = ?", (discord_user_id,))
    row = cur.fetchone()
    con.close()
    return row

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
# Torn API (v2)
# Base: https://api.torn.com/v2
# ----------------------------
def torn_headers(api_key: str) -> dict:
    return {
        "Authorization": f"ApiKey {api_key}",
        "Accept": "application/json",
        "User-Agent": "THCBot/1.0",
    }

async def torn_fetch_battlestats(api_key: str) -> dict:
    url = f"{TORN_BASE_URL}/user/battlestats"

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            headers=torn_headers(api_key),
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            data = await resp.json()

    if "error" in data:
        err = data["error"]
        raise RuntimeError(f"{err.get('error')} (code {err.get('code')})")

    bs = data.get("battlestats")
    if not isinstance(bs, dict):
        raise RuntimeError("Torn response missing 'battlestats'")

    def stat_value(name: str) -> int:
        v = bs.get(name)
        if isinstance(v, dict) and "value" in v:
            return int(v["value"])
        if isinstance(v, int):
            return int(v)
        return 0

    strength = stat_value("strength")
    speed = stat_value("speed")
    defense = stat_value("defense")
    dexterity = stat_value("dexterity")
    total = int(bs.get("total", strength + speed + defense + dexterity))

    return {
        "strength": strength,
        "speed": speed,
        "defense": defense,
        "dexterity": dexterity,
        "total": total,
    }

async def torn_fetch_identity(api_key: str) -> dict:
    url = f"{TORN_BASE_URL}/user/basic"

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            headers=torn_headers(api_key),
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            data = await resp.json()

    if "error" in data:
        err = data["error"]
        raise RuntimeError(f"{err.get('error')} (code {err.get('code')})")

    profile = data.get("profile") or {}
    torn_name = profile.get("name")
    torn_id = profile.get("id")

    if not torn_name or not torn_id:
        raise RuntimeError("Could not read Torn username/ID from /v2/user/basic response")

    return {"torn_username": str(torn_name), "torn_user_id": int(torn_id)}


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

    # Validate against Torn + capture identity
    try:
        stats = await torn_fetch_battlestats(api_key)
        ident = await torn_fetch_identity(api_key)
    except Exception as e:
        await interaction.followup.send(f"Registration failed: {e}", ephemeral=True)
        return

    enc = encrypt_api_key(api_key)

    con = db_connect()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO users (discord_user_id, torn_api_key_encrypted, torn_user_id, torn_username, created_at, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        ON CONFLICT(discord_user_id) DO UPDATE SET
            torn_api_key_encrypted=excluded.torn_api_key_encrypted,
            torn_user_id=excluded.torn_user_id,
            torn_username=excluded.torn_username,
            updated_at=datetime('now')
    """, (interaction.user.id, enc, ident["torn_user_id"], ident["torn_username"]))
    con.commit()
    con.close()

    await interaction.followup.send(
        f"Registered successfully for **{ident['torn_username']} [{ident['torn_user_id']}]**.\n"
        f"Current total: {stats['total']:,}",
        ephemeral=True
    )

@bot.tree.command(name="bs", description="Update and show your battle stat gains since last update")
async def bs(interaction: discord.Interaction):
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
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Determine display identity (Torn name + ID if present)
    ident_row = db_get_user_torn_identity(interaction.user.id)
    if ident_row and ident_row["torn_username"] and ident_row["torn_user_id"]:
        who = f"{ident_row['torn_username']} [{ident_row['torn_user_id']}]"
    else:
        who = f"{interaction.user.display_name} [{interaction.user.id}]"

    # First run: store snapshot and show current only
    if prev is None:
        db_upsert_latest_snapshot(interaction.user.id, current, now_iso)

        torn_profile_url = "https://www.torn.com/profiles.php?XID=4414988"

        if ident_row and ident_row["torn_user_id"]:
            torn_profile_url = f"https://www.torn.com/profiles.php?XID={int(ident_row['torn_user_id'])}"
            embed = discord.Embed(
            title=f"Changes to Stats for {who}",
            url=torn_profile_url,
            description=(
            f"Total {prev_stats['total']:,} → {current['total']:,} ({total_pct:+.2f}%)\n"
            f"Biggest gain: {biggest_label} ({biggest_pct:+.2f}%)\n"
            f"**Since last /bs**"
        ),
    colour=discord.Colour.green() if deltas["total"] >= 0 else discord.Colour.red(),
)

        embed.set_footer(text=f"Saved at: {now_iso}")
        await interaction.followup.send(embed=embed)
        return

    prev_stats = {
        "strength": int(prev["strength"]),
        "defense": int(prev["defense"]),
        "speed": int(prev["speed"]),
        "dexterity": int(prev["dexterity"]),
        "total": int(prev["total"]),
    }

    deltas = {
        "strength": current["strength"] - prev_stats["strength"],
        "defense": current["defense"] - prev_stats["defense"],
        "speed": current["speed"] - prev_stats["speed"],
        "dexterity": current["dexterity"] - prev_stats["dexterity"],
        "total": current["total"] - prev_stats["total"],
    }

    def pct_change(delta: int, base: int) -> float:
        if base <= 0:
            return 0.0
        return (delta / base) * 100.0

    total_pct = pct_change(deltas["total"], prev_stats["total"])

    stat_names = ["strength", "defense", "speed", "dexterity"]
    stat_pct = {k: pct_change(deltas[k], prev_stats[k]) for k in stat_names}
    biggest = max(stat_names, key=lambda k: stat_pct[k])
    biggest_label = biggest.capitalize()
    biggest_pct = stat_pct[biggest]

    last_at = prev["updated_at"]
    if "UTC" not in str(last_at):
        last_at = f"{last_at} UTC"

    # Save the new snapshot
    db_upsert_latest_snapshot(interaction.user.id, current, now_iso)

    embed = discord.Embed(
        title=f"Changes to Stats for {who}",
        description=(
            f"Total {prev_stats['total']:,} → {current['total']:,} ({total_pct:+.2f}%)\n"
            f"Biggest gain: {biggest_label} ({biggest_pct:+.2f}%)\n"
            f"**Since last /bs**"
        ),
        colour=discord.Colour.green() if deltas["total"] >= 0 else discord.Colour.red(),
    )

    def stat_block(key: str) -> str:
        before = prev_stats[key]
        after = current[key]
        delta = deltas[key]
        pct = pct_change(delta, before)
        return f"{before:,} → {after:,}\n{delta:+,} ({pct:+.2f}%)"

    embed.add_field(name="Strength", value=stat_block("strength"), inline=False)
    embed.add_field(name="Defense", value=stat_block("defense"), inline=False)
    embed.add_field(name="Speed", value=stat_block("speed"), inline=False)
    embed.add_field(name="Dexterity", value=stat_block("dexterity"), inline=False)
    embed.add_field(name="Total", value=stat_block("total"), inline=False)

    embed.set_footer(text=f"Compared to last /bs • {last_at}")

    print("DEBUG embed.url =", embed.url)

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="view_bs", description="(Admin) View a user's current battlestats")
@app_commands.describe(user="User to view")
async def view_bs(interaction: discord.Interaction, user: discord.Member):
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
        f"STR {current['strength']:,}; SPD {current['speed']:,}; DEF {current['defense']:,}; "
        f"DEX {current['dexterity']:,}; TOTAL {current['total']:,}"
    )
    await interaction.followup.send(msg, ephemeral=True)

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set in .env")

bot.run(TOKEN)
