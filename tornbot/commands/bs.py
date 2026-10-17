import discord

from ..db import db_get_torn_id_for_discord, db_get_api_key_by_torn_id
from ..services.battlestats import update_and_format_battlestats
from ..services.members import touch_member


def setup(bot: discord.Client):
    @bot.tree.command(name="bs", description="Update and show your battle stat gains since last update")
    async def bs(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        touch_member(interaction.user.id)

        torn_user_id = db_get_torn_id_for_discord(interaction.user.id)
        if torn_user_id is None:
            await interaction.followup.send("No API key registered. Use /register first.", ephemeral=True)
            return

        api_key = db_get_api_key_by_torn_id(torn_user_id)
        if not api_key:
            await interaction.followup.send(
                "Your link exists but no API key was found. Please run /register again.",
                ephemeral=True,
            )
            return

        try:
            block_text, footer_text, delta_total = await update_and_format_battlestats(torn_user_id, api_key)
        except Exception as e:
            await interaction.followup.send(f"Failed to fetch battlestats: {e}", ephemeral=True)
            return

        who = f"{interaction.user.display_name} [{torn_user_id}]"
        torn_profile_url = f"https://www.torn.com/profiles.php?XID={torn_user_id}"

        embed = discord.Embed(
            title=f"Changes to Stats for {who}",
            url=torn_profile_url,
            description="```" + "\n" + block_text + "\n```",
            colour=discord.Colour.green() if delta_total >= 0 else discord.Colour.red(),
        )
        embed.set_footer(text=footer_text)

        await interaction.followup.send(embed=embed)
