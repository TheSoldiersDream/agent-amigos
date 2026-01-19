import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent / "data" / "game_mods"


def _safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value.strip())
    return cleaned.strip("_") or "game"


def _workspace_path(game_id: str, name: str) -> Path:
    safe_id = _safe_name(game_id or "unknown")
    safe_name = _safe_name(name or "game")
    return WORKSPACE_ROOT / f"{safe_name}_{safe_id}"


def list_workspaces() -> Dict[str, object]:
    if not WORKSPACE_ROOT.exists():
        return {"success": True, "workspaces": []}

    workspaces: List[Dict[str, object]] = []
    for entry in WORKSPACE_ROOT.iterdir():
        if not entry.is_dir():
            continue
        meta_path = entry / "metadata.json"
        metadata = {}
        if meta_path.exists():
            try:
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                metadata = {}
        workspaces.append(
            {
                "name": entry.name,
                "path": str(entry),
                "metadata": metadata,
            }
        )
    return {"success": True, "workspaces": workspaces}


def create_workspace(game_id: str, game_name: str, steam_app_id: Optional[str] = None) -> Dict[str, object]:
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    ws_path = _workspace_path(game_id or steam_app_id or game_name, game_name)
    ws_path.mkdir(parents=True, exist_ok=True)

    metadata = {
        "game_id": game_id,
        "game_name": game_name,
        "steam_app_id": steam_app_id,
        "created_at": datetime.utcnow().isoformat(),
        "notes": "Single-player only. Do not use in online multiplayer.",
    }

    meta_path = ws_path / "metadata.json"
    if not meta_path.exists():
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    cheats_path = ws_path / "cheats.json"
    if not cheats_path.exists():
        cheats_path.write_text(json.dumps({"cheats": []}, indent=2), encoding="utf-8")

    readme_path = ws_path / "README.md"
    if not readme_path.exists():
        readme_path.write_text(
            "# Game Trainer Mod Workspace\n\n"
            "This workspace stores cheat tables and notes for a single-player game.\n\n"
            "- Use the Trainer Console to scan for values.\n"
            "- Save addresses into `cheats.json`.\n"
            "- Keep usage offline and respect game terms.\n",
            encoding="utf-8",
        )

    notes_path = ws_path / "notes.md"
    if not notes_path.exists():
        notes_path.write_text("# Notes\n\n", encoding="utf-8")

    return {
        "success": True,
        "path": str(ws_path),
        "metadata": metadata,
    }
