import discord


def setup(bot: discord.Client):
    @bot.tree.command(name="help", description="Show available commands (private)")
    async def help_cmd(interaction: discord.Interaction):
        lines = [
            "**Available commands**",
            "",
            "**Identity / setup**",
            "- `/register` — Link your Torn API key (encrypted) to your Discord account",
            "",
            "**Stats**",
            "- `/bs` — Battle stats: save snapshot + show gains since last snapshot",
            "- `/ws` — Working stats: save snapshot + show gains since last snapshot",
            "",
            "**Admin**",
            "- `/view_bs <user>` — View a user's current battle stats (admin only)",
            "- `/unlinked [limit]` — List members who joined but haven't registered (admin only)",
            "",
            "**Other**",
            "- `/help` — This message",
        ]

        embed = discord.Embed(
            title="THC Bot Help",
            description="\n".join(lines),
            colour=discord.Colour.blurple(),
        )
        embed.set_footer(text="Tip: run /register first, then /bs or /ws any time to track gains.")

        await interaction.response.send_message(embed=embed, ephemeral=True)
