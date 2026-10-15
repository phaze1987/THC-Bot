import discord
from discord.ext import commands

from .config import DISCORD_TOKEN, DEV_GUILD_ID, WIPE_COMMANDS
from .db import db_init
from .commands import register, bs, admin, misc




def build_bot() -> commands.Bot:
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    # Register slash commands
    register.setup(bot)
    bs.setup(bot)
    admin.setup(bot)

    @bot.event
    async def on_ready():
        db_init()

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

    return bot


def main():
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set in .env")

    bot = build_bot()
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
