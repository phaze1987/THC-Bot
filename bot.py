import os
import sqlite3
import hashlib
import aiohttp
import discord
from discord.ext import commands
from cryptography.fernet import Fernet
import base64

# ----------------------------
# ENV / CONFIG
# ----------------------------
TOKEN = os.getenv("DISCORD_TOKEN")
DEV_GUILD_ID = int(os.getenv("DEV_GUILD_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "/app/data/tornbot.sqlite3")
KEY_ENCRYPTION_SECRET = os.getenv("KEY_ENCRYPTION_SECRET", "")

TORN_BASE_URL = "https://api.torn.com/user/"
TORN_COMMENT = "TornAPI"

WIPE_COMMANDS = os.getenv("WIPE_COMMANDS", "0") == "1"

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
    con.commit()
    con.close()


# ----------------------------
# Torn API
# ----------------------------
async def torn_validate_battlestats(api_key: str) -> dict:
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

    # Basic sanity check
    for k in ("strength", "defense", "speed", "dexterity", "total"):
        if k not in data:
            raise RuntimeError(f"Torn response missing '{k}'")
    return data


# ----------------------------
# Bot
# ----------------------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    db_init()

    # Sync slash commands
    WIPE_COMMANDS = os.getenv("WIPE_COMMANDS", "0") == "1"

    if DEV_GUILD_ID:
        guild = discord.Object(id=DEV_GUILD_ID)

        if WIPE_COMMANDS:
            # Wipe guild commands in Discord for this app, then stop (one-time reset)
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f"WIPED guild commands for {DEV_GUILD_ID}. Set WIPE_COMMANDS=0 and restart.")
            return

        # Normal dev sync
        await bot.tree.sync(guild=guild)

        # Optional: prove what Discord has registered right now
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
    # Ephemeral because it's sensitive
    await interaction.response.defer(ephemeral=True)

    api_key = (api_key or "").strip()
    if len(api_key) < 10:
        await interaction.followup.send("That doesn’t look like a valid API key. Try again.", ephemeral=True)
        return

    # Strict validation against Torn
    try:
        data = await torn_validate_battlestats(api_key)
    except Exception as e:
        await interaction.followup.send(f"Registration failed: {e}", ephemeral=True)
        return

    # Store encrypted
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

    total = int(data["total"])
    await interaction.followup.send(
        f"Registered successfully. Torn battlestats validated.\nCurrent total: {total:,}",
        ephemeral=True
    )


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set in .env")

bot.run(TOKEN)
