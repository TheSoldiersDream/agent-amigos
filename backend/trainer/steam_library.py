import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


_CACHE = {
    "timestamp": 0.0,
    "data": None,
}


def _get_steam_root() -> Optional[str]:
    env_root = os.environ.get("STEAM_ROOT")
    if env_root and os.path.exists(env_root):
        return env_root

    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    program_files = os.environ.get("ProgramFiles")

    candidates = []
    if program_files_x86:
        candidates.append(os.path.join(program_files_x86, "Steam"))
    if program_files:
        candidates.append(os.path.join(program_files, "Steam"))

    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _parse_library_paths(vdf_text: str) -> List[str]:
    # Look for "path" "X:\\SteamLibrary" entries
    paths = []
    for match in re.finditer(r'"path"\s+"([^"]+)"', vdf_text):
        raw = match.group(1)
        # Steam stores backslashes escaped in some cases
        cleaned = raw.replace("\\\\", "\\")
        if cleaned and cleaned not in paths:
            paths.append(cleaned)
    return paths


def _parse_app_manifest(manifest_text: str) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for key in ["appid", "name", "installdir"]:
        m = re.search(rf'"{key}"\s+"([^"]+)"', manifest_text)
        if m:
            data[key] = m.group(1)
    return data


def _discover_library_folders(steam_root: str) -> List[str]:
    steamapps = Path(steam_root) / "steamapps"
    library_vdf = steamapps / "libraryfolders.vdf"
    if not library_vdf.exists():
        return [steam_root]

    text = _read_text(library_vdf)
    paths = _parse_library_paths(text)

    # Ensure the root library is included
    if steam_root not in paths:
        paths.insert(0, steam_root)

    # Filter to existing paths
    return [p for p in paths if os.path.exists(p)]


def list_installed_games(max_games: int = 250, ttl_seconds: int = 30) -> Dict[str, object]:
    now = time.monotonic()
    cached = _CACHE.get("data")
    if cached and (now - _CACHE.get("timestamp", 0.0)) < ttl_seconds:
        return cached

    steam_root = _get_steam_root()
    if not steam_root:
        result = {
            "success": False,
            "steam_root": None,
            "libraries": [],
            "games": [],
            "detail": "Steam installation not found. Set STEAM_ROOT env var if Steam is installed elsewhere.",
        }
        _CACHE["data"] = result
        _CACHE["timestamp"] = now
        return result

    libraries = _discover_library_folders(steam_root)
    games: List[Dict[str, object]] = []

    for lib in libraries:
        steamapps = Path(lib) / "steamapps"
        if not steamapps.exists():
            continue
        manifests = list(steamapps.glob("appmanifest_*.acf"))
        for manifest in manifests:
            if len(games) >= max_games:
                break
            text = _read_text(manifest)
            data = _parse_app_manifest(text)
            app_id = data.get("appid")
            name = data.get("name")
            installdir = data.get("installdir")
            if not app_id or not installdir:
                continue
            install_path = Path(lib) / "steamapps" / "common" / installdir
            games.append(
                {
                    "app_id": app_id,
                    "name": name or installdir,
                    "installdir": installdir,
                    "library_path": str(lib),
                    "install_path": str(install_path),
                    "installed": install_path.exists(),
                }
            )
        if len(games) >= max_games:
            break

    result = {
        "success": True,
        "steam_root": steam_root,
        "libraries": libraries,
        "games": games,
        "count": len(games),
    }
    _CACHE["data"] = result
    _CACHE["timestamp"] = now
    return result
