# utils/paladium_api.py
import os
import aiohttp

PALADIUM_API_KEY = os.getenv("PALADIUM_API_KEY")
PALADIUM_API_BASE = "https://api.paladium.games/v1"

if not PALADIUM_API_KEY:
    raise RuntimeError("Set PALADIUM_API_KEY environment variable")

async def fetch_paladium(path: str, session: aiohttp.ClientSession = None, timeout=15):
    url = f"{PALADIUM_API_BASE}{path}"
    headers = {"Authorization": PALADIUM_API_KEY}
    own_session = False
    if session is None:
        session = aiohttp.ClientSession()
        own_session = True
    try:
        async with session.get(url, headers=headers, timeout=timeout) as resp:
            status = resp.status
            try:
                data = await resp.json()
            except Exception:
                data = await resp.text()
            return status, data
    finally:
        if own_session:
            await session.close()

async def verify_player_basic(pseudo: str):
    status, data = await fetch_paladium(f"/player/profile/{pseudo}")
    if status != 200:
        return {"ok": False, "reason": f"Paladium API returned {status}", "data": data}
    is_crack = False
    faction = None
    if isinstance(data, dict):
        is_crack = data.get("is_crack", False) or data.get("crack", False)
        faction = data.get("faction") or data.get("faction_name") or data.get("factionId")
    if is_crack:
        return {"ok": False, "reason": "Compte marqué comme crack selon Paladium.", "data": data}
    return {"ok": True, "reason": None, "data": {"faction": faction, **(data or {})}}
