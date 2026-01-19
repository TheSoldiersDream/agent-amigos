import json
import os
from typing import Dict, Any

TRAINER_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "trainer")
TRAINER_DATA_DIR = os.path.abspath(TRAINER_DATA_DIR)


def _safe_name(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in ("-", "_", ".")) or "default"


def _profile_path(game_id: str) -> str:
    safe = _safe_name(game_id)
    return os.path.join(TRAINER_DATA_DIR, f"{safe}.json")


def _cheat_table_path(game_id: str) -> str:
    safe = _safe_name(game_id)
    return os.path.join(TRAINER_DATA_DIR, f"{safe}.ct")


def save_profile(game_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    os.makedirs(TRAINER_DATA_DIR, exist_ok=True)
    path = _profile_path(game_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return {"success": True, "game_id": game_id, "path": path}


def update_profile(game_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    os.makedirs(TRAINER_DATA_DIR, exist_ok=True)
    existing = load_profile(game_id)
    data: Dict[str, Any] = {}
    if existing.get("success") and isinstance(existing.get("data"), dict):
        data = existing["data"]
    data.update(updates or {})
    return save_profile(game_id, data)


def load_profile(game_id: str) -> Dict[str, Any]:
    path = _profile_path(game_id)
    if not os.path.exists(path):
        return {"success": False, "error": "profile_not_found", "game_id": game_id}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {"success": True, "game_id": game_id, "data": data}


def list_profiles() -> Dict[str, Any]:
    if not os.path.exists(TRAINER_DATA_DIR):
        return {"success": True, "profiles": []}
    files = [f for f in os.listdir(TRAINER_DATA_DIR) if f.endswith(".json")]
    profiles = [os.path.splitext(f)[0] for f in files]
    return {"success": True, "profiles": profiles}


def export_cheat_engine_table(game_id: str, address_map: Dict[str, int]) -> Dict[str, Any]:
    """Generate a minimal Cheat Engine .CT file from an address map.

    Each key in address_map becomes a CheatEntry with 4-byte value type.
    """

    if not address_map:
        return {"success": False, "error": "empty_address_map", "game_id": game_id}

    lines = [
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>",
        "<CheatTable>",
        "  <CheatEntries>",
    ]

    for label, addr in address_map.items():
        try:
            addr_int = int(addr)
        except (TypeError, ValueError):
            continue
        addr_hex = f"{addr_int:X}"
        lines.extend(
            [
                "    <CheatEntry>",
                f"      <Description>\"{label}\"</Description>",
                "      <VariableType>4 Bytes</VariableType>",
                f"      <Address>{addr_hex}</Address>",
                "    </CheatEntry>",
            ]
        )

    lines.extend(["  </CheatEntries>", "</CheatTable>"])

    os.makedirs(TRAINER_DATA_DIR, exist_ok=True)
    ct_path = _cheat_table_path(game_id)
    with open(ct_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return {"success": True, "game_id": game_id, "path": ct_path}
