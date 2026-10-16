import discord
from datetime import datetime, timezone
from ..db import (
    db_get_user_api_key,
    db_get_latest_snapshot,
    db_upsert_latest_snapshot,
    db_get_user_torn_identity,
)
from ..torn_api.user import fetch_battlestats
from ..services.members import touch_member



def fmt_int(n: int) -> str:
    return f"{n:,}"


def pad_right(s: str, width: int) -> str:
    return s + (" " * max(0, width - len(s)))


def setup(bot: discord.Client):
    @bot.tree.command(name="bs", description="Update and show your battle stat gains since last update")
    async def bs(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        touch_member(interaction.user.id)

        api_key = db_get_user_api_key(interaction.user.id)
        if not api_key:
            await interaction.followup.send("No API key registered. Use /register first.", ephemeral=True)
            return

        try:
            current = await fetch_battlestats(api_key)
        except Exception as e:
            await interaction.followup.send(f"Failed to fetch battlestats: {e}", ephemeral=True)
            return

        prev = db_get_latest_snapshot(interaction.user.id)
        now_iso = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC")

        ident_row = db_get_user_torn_identity(interaction.user.id)
        if ident_row and ident_row["torn_username"] and ident_row["torn_user_id"]:
            who = f"{ident_row['torn_username']} [{ident_row['torn_user_id']}]"
        else:
            who = f"{interaction.user.display_name} [{interaction.user.id}]"

        torn_id = None
        if ident_row and ident_row["torn_user_id"] is not None:
            torn_id = int(ident_row["torn_user_id"])
        torn_profile_url = f"https://www.torn.com/profiles.php?XID={torn_id}" if torn_id else None

        if prev is None:
            db_upsert_latest_snapshot(interaction.user.id, current, now_iso)

            embed = discord.Embed(
                title=f"Changes to Stats for {who}",
                url=torn_profile_url,
                description=(
                    f"Total {current['total']:,}\n"
                    f"First snapshot saved.\n"
                    f"Run **/bs** again to see changes."
                ),
                colour=discord.Colour.blurple(),
            )
            embed.set_footer(text=f"Saved at: {now_iso}")
            await interaction.followup.send(embed=embed)
            return

        prev_stats = {
            "strength": int(prev["strength"]),
            "defense": int(prev["defense"]),
            "speed": int(prev["speed"]),
            "dexterity": int(prev["dexterity"]),
            "total": int(prev["total"]),
        }

        deltas = {
            "strength": current["strength"] - prev_stats["strength"],
            "defense": current["defense"] - prev_stats["defense"],
            "speed": current["speed"] - prev_stats["speed"],
            "dexterity": current["dexterity"] - prev_stats["dexterity"],
            "total": current["total"] - prev_stats["total"],
        }

        def pct_change(delta: int, base: int) -> float:
            if base <= 0:
                return 0.0
            return (delta / base) * 100.0

        last_at = prev["updated_at"]
        if "UTC" not in str(last_at):
            last_at = f"{last_at} UTC"

        db_upsert_latest_snapshot(interaction.user.id, current, now_iso)

        rows = [
            ("Str:", "strength"),
            ("Spd:", "speed"),
            ("Dex:", "dexterity"),
            ("Def:", "defense"),
            ("", None),
            ("Tot:", "total"),
        ]

        formatted = []
        for label, key in rows:
            if key is None:
                formatted.append((label, "", "", ""))
                continue
            before = prev_stats[key]
            after = current[key]
            delta = deltas[key]
            pct = pct_change(delta, before)
            formatted.append((label, fmt_int(before), fmt_int(after), f"({pct:.2f}%)"))

        label_w = max(len(r[0]) for r in formatted)
        before_w = max(len(r[1]) for r in formatted)
        after_w = max(len(r[2]) for r in formatted)

        lines = []
        lines.append("Old Battle Stats ---> New Battle Stats")
        lines.append("")
        for (label, before_s, after_s, pct_s) in formatted:
            if before_s == "" and after_s == "":
                lines.append("")
                continue
            lines.append(
                f"{pad_right(label, label_w)}  "
                f"{pad_right(before_s, before_w)}  --->  "
                f"{pad_right(after_s, after_w)} {pct_s}"
            )

        block = "```" + "\n" + "\n".join(lines) + "\n```"

        embed = discord.Embed(
            title=f"Changes to Stats for {who}",
            url=torn_profile_url,
            description=block,
            colour=discord.Colour.green() if deltas["total"] >= 0 else discord.Colour.red(),
        )
        embed.set_footer(text=f"Changes since: {last_at} • Stats updated: {now_iso}")

        await interaction.followup.send(embed=embed)
