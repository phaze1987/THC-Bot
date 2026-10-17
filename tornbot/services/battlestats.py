from datetime import datetime, timezone

from ..db import db_get_latest_snapshot, db_upsert_latest_snapshot
from ..torn_api.user import fetch_battlestats
from .stats_common import fmt_int, pad_right, pct_change



async def update_and_format_battlestats(torn_user_id: int, api_key: str) -> tuple[str, str, int]:
    """
    Fetch current battlestats; compare to previous snapshot; upsert snapshot.

    Returns: (block_text, footer_text, delta_total)
    - block_text: code-block-ready text WITHOUT triple backticks
    - footer_text: 'Saved at...' or 'Changes since...'
    - delta_total: current_total - prev_total (0 if first snapshot)
    """
    current = await fetch_battlestats(api_key)
    prev = db_get_latest_snapshot(torn_user_id)
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC")

    if prev is None:
        db_upsert_latest_snapshot(torn_user_id, current, now_iso)
        lines = [
            "Old Battle Stats ---> New Battle Stats",
            "",
            f"Total {current['total']:,}",
            "First snapshot saved.",
            "Run /bs again to see changes.",
        ]
        return ("\n".join(lines), f"Saved at: {now_iso}", 0)

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

    last_at = prev["updated_at"]
    if "UTC" not in str(last_at):
        last_at = f"{last_at} UTC"

    db_upsert_latest_snapshot(torn_user_id, current, now_iso)

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

    footer = f"Changes since: {last_at} • Stats updated: {now_iso}"
    return ("\n".join(lines), footer, int(deltas["total"]))
