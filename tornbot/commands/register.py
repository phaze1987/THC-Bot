import discord
from ..crypto import encrypt_api_key
from ..db import db_connect
from ..torn_api.user import fetch_battlestats, fetch_identity


def setup(bot: discord.Client):
    @bot.tree.command(name="register", description="Register your Torn API key (stored securely)")
    async def register(interaction: discord.Interaction, api_key: str):
        await interaction.response.defer(ephemeral=True)

        api_key = (api_key or "").strip()
        if len(api_key) != 16:
            await interaction.followup.send(
                "Invalid key format. Torn API keys are 16 characters.",
                ephemeral=True,
            )
            return

        try:
            stats = await fetch_battlestats(api_key)
            ident = await fetch_identity(api_key)
        except Exception as e:
            await interaction.followup.send(f"Registration failed: {e}", ephemeral=True)
            return

        enc = encrypt_api_key(api_key)

        con = db_connect()
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO users (
                discord_user_id,
                torn_api_key_encrypted,
                torn_user_id,
                torn_username,
                linked_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
            ON CONFLICT(discord_user_id) DO UPDATE SET
                torn_api_key_encrypted=excluded.torn_api_key_encrypted,
                torn_user_id=excluded.torn_user_id,
                torn_username=excluded.torn_username,
                linked_at=datetime('now'),
                updated_at=datetime('now')
            """,
            (interaction.user.id, enc, ident["torn_user_id"], ident["torn_username"]),
        )

        con.commit()
        con.close()

        await interaction.followup.send(
            f"Registered successfully for **{ident['torn_username']} [{ident['torn_user_id']}]**.\n"
            f"Current total: {stats['total']:,}",
            ephemeral=True,
        )
