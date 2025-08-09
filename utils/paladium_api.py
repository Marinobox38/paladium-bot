import os
import requests

PALADIUM_API_KEY = os.getenv("PALADIUM_API_KEY")
PALADIUM_API_BASE = "https://api.paladium.games/v1"

if not PALADIUM_API_KEY:
    raise RuntimeError("Set PALADIUM_API_KEY environment variable")

def fetch_paladium(path: str, timeout=15):
    url = f"{PALADIUM_API_BASE}{path}"
    headers = {"Authorization": PALADIUM_API_KEY}
    resp = requests.get(url, headers=headers, timeout=timeout)
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    return resp.status_code, data

def verify_player_basic(pseudo: str):
    status, data = fetch_paladium(f"/player/profile/{pseudo}")
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
