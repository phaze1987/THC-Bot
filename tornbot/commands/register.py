import discord

from ..services.members import touch_member
from ..services.linking import register_user


def setup(bot: discord.Client):
    @bot.tree.command(name="register", description="Register your Torn API key (stored securely)")
    async def register(interaction: discord.Interaction, api_key: str):
        await interaction.response.defer(ephemeral=True)
        touch_member(interaction.user.id)

        try:
            ident, _cleaned_key = await register_user(interaction.user.id, api_key)
        except ValueError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"Registration failed: {e}", ephemeral=True)
            return

        await interaction.followup.send(
            f"Registered successfully for **{ident['torn_username']} [{ident['torn_user_id']}]**.\n"
            "Now run **/bs** for battle stats, **/ws** for working stats, or **/stats** for both.",
            ephemeral=True,
        )
