import discord
from discord import app_commands
from .admin import is_admin_member
from ..db import db_get_unlinked_members


def setup(bot: discord.Client):
    @bot.tree.command(name="unlinked", description="(Admin) List members who joined but haven't registered")
    @app_commands.describe(limit="Max results to show (default 25)")
    async def unlinked(interaction: discord.Interaction, limit: int = 25):
        if not isinstance(interaction.user, discord.Member) or not is_admin_member(interaction.user):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        limit = max(1, min(int(limit), 100))
        rows = db_get_unlinked_members(limit=limit)

        if not rows:
            await interaction.followup.send("Everyone is linked — nice.", ephemeral=True)
            return

        lines = []
        for r in rows:
            lines.append(f"- <@{r['discord_user_id']}> • joined_at: {r['joined_at']}")

        await interaction.followup.send(
            "**Unlinked members:**\n" + "\n".join(lines),
            ephemeral=True
        )
