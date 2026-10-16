import discord
from discord import app_commands
from ..config import ADMIN_ROLE_IDS
from ..db import db_get_user_api_key
from ..torn_api.user import fetch_battlestats
from ..services.members import touch_member


def is_admin_member(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    role_ids = {r.id for r in member.roles}
    return len(role_ids.intersection(ADMIN_ROLE_IDS)) > 0


def setup(bot: discord.Client):
    @bot.tree.command(name="view_bs", description="(Admin) View a user's current battlestats")
    @app_commands.describe(user="User to view")
    async def view_bs(interaction: discord.Interaction, user: discord.Member):
        if not isinstance(interaction.user, discord.Member) or not is_admin_member(interaction.user):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True, ephemeral=True)
        touch_member(interaction.user.id)

        api_key = db_get_user_api_key(user.id)
        if not api_key:
            await interaction.followup.send(f"{user.mention} has not registered an API key.", ephemeral=True)
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

