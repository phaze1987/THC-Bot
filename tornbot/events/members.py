import discord
from datetime import datetime, timezone

from ..config import channel_id, channel_mention
from ..db import db_upsert_discord_member, db_mark_member_left


def setup(bot: discord.Client) -> None:
    @bot.event
    async def on_member_join(member: discord.Member):
        try:
            joined_at = member.joined_at or datetime.now(timezone.utc)
            joined_at_iso = joined_at.replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC")
            db_upsert_discord_member(member.id, joined_at_iso)

            cid = channel_id("sekisho-checkpoint")
            if cid <= 0:
                return

            channel = bot.get_channel(cid) or await bot.fetch_channel(cid)

            msg = (
                f"**Halt. You have reaced the Sekisho of The Hayabusa Clan.** {member.mention}. 🦅\n"
                "Beyond these gates lies the Niwa. Unmask your identity, pledge your loyalty to the shadows, and prepare your blades. Here, loyalty is paid in blood and respect is earned through iron willpower.\n\n"
                "🥷 **To pass the checkpoint:**\n\n"
                f"1. Show your seal and link your API in {channel_mention('menpo-identity-mask')} to verify your Torn profile.\n"
                f"2. Study the clan tenets and sacred code in {channel_mention('hatto-scroll-of-laws')}.\n"
                f"3. Step out of the smog and join the hidden flock in {channel_mention('kakurega-the-hideout')}.\n\n"
                "*Fly swift. Strike hard. Leave no survivors.*"
            )

            await channel.send(msg)
        except Exception as e:
            print(f"[JOIN] ERROR: {type(e).__name__}: {e}")


    @bot.event
    async def on_member_remove(member: discord.Member):
        left_at_iso = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC")
        db_mark_member_left(member.id, left_at_iso)