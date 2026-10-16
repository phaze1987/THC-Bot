import discord
from ..services.members import touch_member
from ..services.linking import register_user
from ..services.battlestats import fetch_and_snapshot

def setup(bot: discord.Client):
    @bot.tree.command(name="register", description="Register your Torn API key (stored securely)")
    async def register(interaction: discord.Interaction, api_key: str):
        await interaction.response.defer(ephemeral=True)
        touch_member(interaction.user.id)

        try:
            ident, cleaned_key = await register_user(interaction.user.id, api_key)
            stats, _, _ = await fetch_and_snapshot(interaction.user.id, cleaned_key)
        except ValueError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"Registration failed: {e}", ephemeral=True)
            return

        await interaction.followup.send(
            f"Registered successfully for **{ident['torn_username']} [{ident['torn_user_id']}]**.\n"
            f"Current total: {stats['total']:,}",
            ephemeral=True,
        )
