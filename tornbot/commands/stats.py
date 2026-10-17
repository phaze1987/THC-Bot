import discord

from ..db import db_get_torn_id_for_discord, db_get_api_key_by_torn_id
from ..services.stats_registry import get_default_providers
from ..services.members import touch_member


def setup(bot: discord.Client):
    @bot.tree.command(name="stats", description="Update and show your tracked stats since last update")
    async def stats(interaction: discord.Interaction):
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

        who = f"{interaction.user.display_name} [{torn_user_id}]"
        torn_profile_url = f"https://www.torn.com/profiles.php?XID={torn_user_id}"

        providers = get_default_providers()

        sections: list[str] = []
        footers: list[str] = []
        delta_sum = 0

        for p in providers:
            try:
                block_text, footer_text, delta_total = await p.fn(torn_user_id, api_key)
            except Exception as e:
                await interaction.followup.send(f"Failed to fetch {p.title.lower()}: {e}", ephemeral=True)
                return

            sections.append(
                f"**{p.title}**\n"
                "```" + "\n" + block_text + "\n```"
            )
            footers.append(footer_text)
            delta_sum += int(delta_total)

        embed = discord.Embed(
            title=f"Stats update for {who}",
            url=torn_profile_url,
            description="\n".join(sections),
            colour=discord.Colour.green() if delta_sum >= 0 else discord.Colour.red(),
        )
        embed.set_footer(text=" • ".join(footers))

        await interaction.followup.send(embed=embed)
