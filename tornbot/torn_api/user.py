from .client import torn_get


async def fetch_battlestats(api_key: str) -> dict:
    data = await torn_get(api_key, "/user/battlestats")

    bs = data.get("battlestats")
    if not isinstance(bs, dict):
        raise RuntimeError("Torn response missing 'battlestats'")

    def stat_value(name: str) -> int:
        v = bs.get(name)
        if isinstance(v, dict) and "value" in v:
            return int(v["value"])
        if isinstance(v, int):
            return int(v)
        return 0

    strength = stat_value("strength")
    speed = stat_value("speed")
    defense = stat_value("defense")
    dexterity = stat_value("dexterity")
    total = int(bs.get("total", strength + speed + defense + dexterity))

    return {
        "strength": strength,
        "speed": speed,
        "defense": defense,
        "dexterity": dexterity,
        "total": total,
    }


async def fetch_identity(api_key: str) -> dict:
    data = await torn_get(api_key, "/user/basic")

    profile = data.get("profile") or {}
    torn_name = profile.get("name")
    torn_id = profile.get("id")

    if not torn_name or not torn_id:
        raise RuntimeError("Could not read Torn username/ID from /v2/user/basic response")

    return {"torn_username": str(torn_name), "torn_user_id": int(torn_id)}
