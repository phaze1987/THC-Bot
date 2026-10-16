import discord
from discord.ext import commands

from .config import DISCORD_TOKEN, DEV_GUILD_ID, WIPE_COMMANDS, BOT_ENV
from .db import db_init, db_upsert_discord_member
from .commands import register, bs, admin, misc, unlinked

from datetime import datetime, timezone




def build_bot() -> commands.Bot:
    
    intents = discord.Intents.default()
    intents.members = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    # Register slash commands
    register.setup(bot)
    bs.setup(bot)
    admin.setup(bot)
    misc.setup(bot)
    unlinked.setup(bot)

    @bot.event
    async def on_member_join(member: discord.Member):
        now_iso = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC")
        db_upsert_discord_member(member.id, now_iso)

    @bot.event
    async def on_ready():
        db_init()

        if DEV_GUILD_ID > 0:
            guild = discord.Object(id=DEV_GUILD_ID)

            if WIPE_COMMANDS:
                bot.tree.clear_commands(guild=guild)
                await bot.tree.sync(guild=guild)
                print(f"WIPED guild commands for {DEV_GUILD_ID}. Set WIPE_COMMANDS=0 and restart.")
                return

            print("Local tree commands pre-sync:", [c.name for c in bot.tree.get_commands()])

            await bot.tree.sync(guild=guild)
            cmds = await bot.tree.fetch_commands(guild=guild)
            print("Guild commands after sync:", [c.name for c in cmds])
            print(f"Synced commands to dev guild {DEV_GUILD_ID}.")
        else:
            if BOT_ENV == "dev":
                print("BOT_ENV=dev but DEV_GUILD_ID is not set. Refusing to global sync commands.")
                return

            await bot.tree.sync()
            print("Synced commands globally (may take a few minutes to appear).")

        print(f"BOT_ENV={BOT_ENV} • DEV_GUILD_ID={DEV_GUILD_ID}")

        print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    return bot


def main():
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set in .env")

    bot = build_bot()
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
