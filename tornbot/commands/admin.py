import functools

import discord
from discord import app_commands

from ..config import ADMIN_ROLE_IDS
from ..db import db_get_torn_id_for_discord, db_get_api_key_by_torn_id
from ..torn_api.user import fetch_battlestats
from ..services.members import touch_member


def is_admin_member(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    role_ids = {r.id for r in member.roles}
    return len(role_ids.intersection(ADMIN_ROLE_IDS)) > 0


def admin_command(bot: discord.Client, name: str, description: str):
    """
    Decorator that registers an admin-only slash command with consistent permission errors.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        async def predicate(interaction: discord.Interaction) -> bool:
            return isinstance(interaction.user, discord.Member) and is_admin_member(interaction.user)

        cmd = bot.tree.command(name=name, description=description)(wrapper)
        cmd = app_commands.check(predicate)(cmd)

        @cmd.error
        async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            if isinstance(error, app_commands.CheckFailure):
                msg = "You don't have permission to use this command."
                if interaction.response.is_done():
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.response.send_message(msg, ephemeral=True)
                return
            raise error

        return cmd

    return decorator


def setup(bot: discord.Client):
    @admin_command(bot, "view_bs", "(Admin) View a user's current battlestats")
    @app_commands.describe(user="User to view")
    async def view_bs(interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(thinking=True, ephemeral=True)
        touch_member(interaction.user.id)

        torn_user_id = db_get_torn_id_for_discord(user.id)
        if torn_user_id is None:
            await interaction.followup.send(f"{user.mention} has not registered an API key.", ephemeral=True)
            return

        api_key = db_get_api_key_by_torn_id(torn_user_id)
        if not api_key:
            await interaction.followup.send(
                f"{user.mention} is linked but no API key was found. Ask them to run /register again.",
                ephemeral=True,
            )
            return

        try:
            current = await fetch_battlestats(api_key)
        except Exception as e:
            await interaction.followup.send(
                f"Failed to fetch battlestats for {user.mention}: {e}", ephemeral=True
            )
            return

        msg = (
            f"**Battle Stats (Admin View)**\n"
            f"User: {user.mention}\n"
            f"STR {current['strength']:,}; SPD {current['speed']:,}; DEF {current['defense']:,}; "
            f"DEX {current['dexterity']:,}; TOTAL {current['total']:,}"
        )
        await interaction.followup.send(msg, ephemeral=True)

    @admin_command(bot, "adminhelp", "Show available admin commands (private)")
    async def adminhelp_cmd(interaction: discord.Interaction):
        lines = [
            "**Available admin commands**",
            "",
            "- `/view_bs <user>` — View a user's current battle stats",
            "- `/unlinked [limit]` — List members who joined but haven't registered",
        ]

        embed = discord.Embed(
            title="THC Bot Admin Help",
            description="\n".join(lines),
            colour=discord.Colour.blurple(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
