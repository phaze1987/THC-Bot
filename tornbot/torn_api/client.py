import aiohttp
from ..config import TORN_BASE_URL


def torn_headers(api_key: str) -> dict:
    return {
        "Authorization": f"ApiKey {api_key}",
        "Accept": "application/json",
        "User-Agent": "THCBot/1.0",
    }


async def torn_get(api_key: str, path: str) -> dict:
    url = f"{TORN_BASE_URL}{path}"

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            headers=torn_headers(api_key),
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            data = await resp.json()

    if isinstance(data, dict) and "error" in data:
        err = data["error"]
        raise RuntimeError(f"{err.get('error')} (code {err.get('code')})")

    if not isinstance(data, dict):
        raise RuntimeError("Unexpected Torn response type")

    return data
