import discord
from discord.ext import commands

from .config import DISCORD_TOKEN, DEV_GUILD_ID, WIPE_COMMANDS, BOT_ENV, channel_id

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
    try:
        print(f"[JOIN] member={member} id={member.id} guild={member.guild} guild_id={member.guild.id}")

        now_iso = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC")
        db_upsert_discord_member(member.id, now_iso)

        cid = channel_id("sekisho-checkpoint")
        print(f"[JOIN] sekisho-checkpoint channel id from config: {cid}")

        if cid <= 0:
            print("[JOIN] No channel id configured; skipping welcome message.")
            return

        channel = bot.get_channel(cid)
        print(f"[JOIN] bot.get_channel({cid}) -> {channel}")

        if channel is None:
            channel = await bot.fetch_channel(cid)
            print(f"[JOIN] bot.fetch_channel({cid}) -> {channel}")

        msg = (
            "Oh look, a new soul has crossed over into Purgatory...\n"
            f"Welcome {member.mention}, to The No Pants Purgatory Ranch server 💜\n\n"
            "👉 Your first stop is to go to the #ocker channel and register with the bot.\n\n"
            "Once you’re in, introduce yourself, don’t be a dick, and make yourself at home 💜"
        )

        await channel.send(msg)
        print("[JOIN] Welcome message sent.")
    except Exception as e:
        print(f"[JOIN] ERROR: {type(e).__name__}: {e}")


    @bot.event
    async def on_ready():
        db_init()

        print("Local tree commands pre-sync:", [c.name for c in bot.tree.get_commands()])
        print("bot.user.id:", bot.user.id)
        print("bot.application_id:", bot.application_id)

        # If a dev guild is configured, try guild sync first (fast iteration)
        if DEV_GUILD_ID > 0:
            guild = discord.Object(id=DEV_GUILD_ID)

            if WIPE_COMMANDS:
                bot.tree.clear_commands(guild=guild)
                await bot.tree.sync(guild=guild)
                print(f"WIPED guild commands for {DEV_GUILD_ID}. Set WIPE_COMMANDS=0 and restart.")
                return

            # 1) Try guild sync
            await bot.tree.sync(guild=guild)
            guild_cmds = await bot.tree.fetch_commands(guild=guild)
            guild_names = [c.name for c in guild_cmds]
            print("Guild commands after sync:", guild_names)

            # 2) If Discord returns none, fall back to global sync
            if not guild_names:
                print(
                    f"WARNING: Guild sync returned 0 commands for {DEV_GUILD_ID}. "
                    "Falling back to global sync (may take a few minutes)."
                )
                await bot.tree.sync()
                global_cmds = await bot.tree.fetch_commands()
                print("Global commands after sync:", [c.name for c in global_cmds])
            else:
                print(f"Synced commands to dev guild {DEV_GUILD_ID}.")
        else:
            # No dev guild configured: global sync
            await bot.tree.sync()
            global_cmds = await bot.tree.fetch_commands()
            print("Global commands after sync:", [c.name for c in global_cmds])
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
