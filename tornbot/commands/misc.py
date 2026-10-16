import discord

def setup(bot: discord.Client):
    @bot.tree.command(name="ping", description="Check if the bot is alive")
    async def ping(interaction: discord.Interaction):
        await interaction.response.send_message("Pong!")

    @bot.tree.command(name="hello", description="Say hello")
    async def hello(interaction: discord.Interaction):
        await interaction.response.send_message(f"Hello, {interaction.user.mention}!")
