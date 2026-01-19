from typing import List, Dict, Any, Optional
from datetime import datetime
import re

from fastapi import APIRouter, HTTPException
import psutil
from pydantic import BaseModel

from . import process_manager
from .memory_scanner import scan_exact_value, scan_next as scan_next_internal, scan_pattern as scan_pattern_internal
from .memory_writer import read_memory, write_memory, freeze_memory, unfreeze_memory, get_frozen_registry
from .game_state_models import GameWorldState, PlayerState
from .trainer_engine import TrainerEngine
from .ai_controller import AIController
from . import profile_store
from . import steam_library
from . import mod_workspace


router = APIRouter(prefix="/trainer", tags=["trainer"])

_engine = TrainerEngine()
_ai = AIController(_engine)
_session: Dict[str, Any] = {}


def _normalize_game_id(name: str, platform: str) -> str:
    base = f"{name.strip()}-{platform.strip()}".lower()
    base = re.sub(r"\s+", "-", base)
    base = re.sub(r"[^a-z0-9\-_.]", "", base)
    return base or "unknown-game"


def _infer_platform(platform: str) -> str:
    p = (platform or "").strip().lower()
    if not p:
        return "PC"
    if "pc" in p:
        return "PC"
    if "xbox" in p:
        return "Console (Xbox)"
    if "playstation" in p or "ps" in p:
        return "Console (PlayStation)"
    if "switch" in p:
        return "Console (Switch)"
    if "emulator" in p:
        return "Emulator"
    return platform.strip()


def _infer_engine(game_name: str) -> str:
    name = (game_name or "").lower()
    engine_map = {
        "fortnite": "Unreal Engine",
        "valorant": "Unreal Engine 4",
        "apex": "Source",
        "counter-strike": "Source 2",
        "cs2": "Source 2",
        "cs:go": "Source",
        "gta": "RAGE",
        "rocket league": "Unreal Engine 3",
        "minecraft": "Java/Bedrock Engine",
        "overwatch": "Iris Engine",
        "elden ring": "PhyreEngine",
    }
    for key, engine in engine_map.items():
        if key in name:
            return engine
    return "Unknown"


def _infer_genre(game_name: str) -> str:
    name = (game_name or "").lower()
    if any(k in name for k in ["fps", "shooter", "call of duty", "battlefield", "counter-strike", "valorant", "apex"]):
        return "FPS"
    if any(k in name for k in ["rpg", "elden", "skyrim", "witcher", "baldur", "ff", "final fantasy"]):
        return "RPG"
    if any(k in name for k in ["strategy", "rts", "civ", "civilization", "age of empires", "starcraft"]):
        return "RTS"
    if any(k in name for k in ["sim", "simulator", "flight", "farm", "city", "truck"]):
        return "Sim"
    if any(k in name for k in ["sports", "fifa", "nba", "madden", "nhl"]):
        return "Sports"
    if any(k in name for k in ["mmo", "online", "guild", "raid", "wow", "warcraft"]):
        return "MMO"
    return "Unknown"


def _infer_online(game_name: str) -> str:
    name = (game_name or "").lower()
    if any(k in name for k in ["online", "multiplayer", "mmo", "co-op", "coop", "battle royale"]):
        return "Online"
    return "Unknown"


def _build_knowledge_graph(game_name: str, platform: str, engine: str, genre: str, online: str) -> Dict[str, Any]:
    return {
        "game_title": game_name,
        "platform": platform,
        "engine": engine,
        "genre": genre,
        "online_mode": online,
        "core_mechanics": ["Awaiting live telemetry", "Movement basics", "Objective-driven play"],
        "progression_systems": ["Profile-based progression", "Unlockable upgrades"],
        "difficulty_scaling": ["Adaptive difficulty (if supported)", "Skill-based matchmaking (if online)"]
        if online == "Online"
        else ["Static difficulty presets"],
        "ai_behavior_patterns": ["Pattern recognition pending", "State-driven AI loops"],
        "common_failure_points": ["Positioning errors", "Resource mismanagement", "Timing mistakes"],
        "meta_strategies": ["Safe objective routing", "Risk vs reward pathing"],
        "speedrun_techniques": ["Route optimization (legal)", "Consistency improvements"],
        "known_bugs_or_loopholes": ["None detected locally"],
        "resource_bottlenecks": ["Ammo/energy scarcity", "Cooldown windows"],
    }


def _build_recommendations(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    genre = session.get("genre", "Unknown")
    mode = session.get("trainer_mode", "training")
    base = [
        {
            "title": "Tighten movement discipline",
            "why": "Reduces exposure time and improves positional advantage.",
            "risk": "Low",
            "expected_improvement_pct": 6,
            "alternatives": ["Slower, safer rotation", "Hold power positions"],
            "comparison": "If you strafe-cut earlier instead of full-sprinting, you reduce exposure windows.",
        },
        {
            "title": "Optimize objective timing",
            "why": "Earlier objective control yields resource and tempo advantage.",
            "risk": "Medium",
            "expected_improvement_pct": 8,
            "alternatives": ["Delay for resource stack", "Split-push to bait rotations"],
            "comparison": "If you secure the objective before clearing side-loot, you gain tempo at the cost of economy.",
        },
    ]

    if genre == "FPS":
        base.append(
            {
                "title": "Pre-aim common angles",
                "why": "Cuts reaction time and increases first-shot accuracy.",
                "risk": "Low",
                "expected_improvement_pct": 5,
                "alternatives": ["Shoulder peek for info", "Utility clear before entry"],
                "comparison": "If you pre-aim instead of wide-swinging, you reduce peek time and exposure.",
            }
        )
    if mode == "performance":
        base.append(
            {
                "title": "Min-max loadout cooldowns",
                "why": "Higher uptime on peak damage windows.",
                "risk": "Medium",
                "expected_improvement_pct": 10,
                "alternatives": ["Balanced sustain build", "Team-support focused build"],
                "comparison": "If you favor cooldown reduction over defense, you gain burst windows but lose survivability.",
            }
        )
    if mode == "meta":
        base.append(
            {
                "title": "Counter dominant tactics",
                "why": "Shifts matchups in your favor against common strategies.",
                "risk": "Medium",
                "expected_improvement_pct": 9,
                "alternatives": ["Mirror strategy", "Hard disengage tempo"],
                "comparison": "If you counter-pick instead of mirror, you gain matchup leverage but require execution.",
            }
        )
    return base


def _build_dashboard(session: Dict[str, Any]) -> Dict[str, Any]:
    recommendations = _build_recommendations(session)
    expected = max(5, min(18, int(sum(r.get("expected_improvement_pct", 0) for r in recommendations) / max(1, len(recommendations)))))
    return {
        "analysis_summary": "Continuous training baseline active. Awaiting deeper telemetry for higher-precision coaching.",
        "observations": [
            "Initial session running in autonomous coaching mode",
            "No invasive tools enabled by default",
        ],
        "recommendations": recommendations,
        "risk_level": "Low",
        "expected_improvement_pct": expected,
        "trainer_mode": session.get("trainer_mode", "training"),
        "alternatives": ["Safer route optimization", "Focus on consistency before speed"],
        "timestamp": datetime.utcnow().isoformat(),
    }


class AttachRequest(BaseModel):
    process_name: str


class AttachPidRequest(BaseModel):
    pid: int


class ScanValueRequest(BaseModel):
    value: int
    type: str = "int"


class PatternScanRequest(BaseModel):
    pattern: str


class NextScanRequest(BaseModel):
    mode: str = "exact"
    value: Optional[float] = None
    type: str = "int"


class WriteRequest(BaseModel):
    address: int
    type: str = "int"
    value: int


class ReadRequest(BaseModel):
    address: int
    type: str = "int"


class FreezeRequest(BaseModel):
    address: int
    type: str = "int"
    value: int
    interval_ms: int = 100


class UnfreezeRequest(BaseModel):
    address: int


class AIRunRequest(BaseModel):
    state: GameWorldState


class SaveProfileRequest(BaseModel):
    game_id: str
    address_map: Dict[str, int]


class LoadProfileRequest(BaseModel):
    game_id: str


class ExportCheatTableRequest(BaseModel):
    game_id: str


class ModWorkspaceRequest(BaseModel):
    game_id: str
    game_name: str
    steam_app_id: Optional[str] = None


class GameSessionStartRequest(BaseModel):
    game_name: str
    platform: str
    notes: Optional[str] = None
    allow_memory_tools: bool = False


class TrainerModeRequest(BaseModel):
    mode: str


class SessionMemoryUpdateRequest(BaseModel):
    updates: Dict[str, Any]


class MemoryToolsRequest(BaseModel):
    enabled: bool


@router.get("/processes")
async def get_processes() -> List[Dict[str, Any]]:
    return process_manager.list_processes()


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    proc = process_manager.get_attached_process()
    frozen = get_frozen_registry()
    frozen_list = [
        {"address": f"0x{addr:X}", **meta} for addr, meta in frozen.items()
    ]
    proc_details = None
    if proc is not None:
        try:
            p = psutil.Process(proc.pid)
            exe_path = p.exe()
            mem_mb = round(p.memory_info().rss / (1024 * 1024), 1)
            proc_details = {
                "pid": proc.pid,
                "name": proc.name,
                "exe": exe_path,
                "memory_mb": mem_mb,
                "is_steam_game": "steamapps" in (exe_path or "").lower(),
            }
        except Exception:
            proc_details = {"pid": proc.pid, "name": proc.name}
    return {
        "attached_process": proc_details,
        "frozen": frozen_list,
        "frozen_count": len(frozen_list),
    }


@router.post("/session/start")
async def start_session(req: GameSessionStartRequest) -> Dict[str, Any]:
    game_name = (req.game_name or "").strip()
    platform = _infer_platform(req.platform)
    if not game_name:
        raise HTTPException(status_code=400, detail="game_name is required")

    game_id = _normalize_game_id(game_name, platform)
    engine = _infer_engine(game_name)
    genre = _infer_genre(game_name)
    online = _infer_online(game_name)

    knowledge_graph = _build_knowledge_graph(game_name, platform, engine, genre, online)
    previous = profile_store.load_profile(game_id)
    memory = {}
    if previous.get("success") and isinstance(previous.get("data"), dict):
        memory = previous["data"].get("memory", {}) or {}

    session = {
        "game_id": game_id,
        "game_name": game_name,
        "platform": platform,
        "engine": engine,
        "genre": genre,
        "online": online,
        "knowledge_graph": knowledge_graph,
        "trainer_mode": "training",
        "allow_memory_tools": bool(req.allow_memory_tools),
        "notes": req.notes or "",
        "memory": memory,
        "started_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    _session.clear()
    _session.update(session)
    profile_store.update_profile(game_id, {"memory": memory, "last_session": session})
    return session


@router.get("/session/status")
async def session_status() -> Dict[str, Any]:
    if not _session:
        return {"active": False}
    return {"active": True, **_session}


@router.post("/session/mode")
async def set_trainer_mode(req: TrainerModeRequest) -> Dict[str, Any]:
    if not _session:
        raise HTTPException(status_code=400, detail="no_active_session")
    mode = (req.mode or "").strip().lower()
    if mode not in {"training", "performance", "meta"}:
        raise HTTPException(status_code=400, detail="invalid_mode")
    _session["trainer_mode"] = mode
    _session["updated_at"] = datetime.utcnow().isoformat()
    return {"success": True, "trainer_mode": mode}


@router.post("/session/analysis")
async def session_analysis() -> Dict[str, Any]:
    if not _session:
        raise HTTPException(status_code=400, detail="no_active_session")
    dashboard = _build_dashboard(_session)
    _session["last_analysis"] = dashboard
    _session["updated_at"] = datetime.utcnow().isoformat()
    return dashboard


@router.post("/session/memory")
async def update_memory(req: SessionMemoryUpdateRequest) -> Dict[str, Any]:
    if not _session:
        raise HTTPException(status_code=400, detail="no_active_session")
    memory = _session.get("memory", {})
    memory.update(req.updates or {})
    _session["memory"] = memory
    _session["updated_at"] = datetime.utcnow().isoformat()
    profile_store.update_profile(_session["game_id"], {"memory": memory})
    return {"success": True, "memory": memory}


@router.post("/session/memory-tools")
async def set_memory_tools(req: MemoryToolsRequest) -> Dict[str, Any]:
    if not _session:
        raise HTTPException(status_code=400, detail="no_active_session")
    _session["allow_memory_tools"] = bool(req.enabled)
    _session["updated_at"] = datetime.utcnow().isoformat()
    profile_store.update_profile(_session["game_id"], {"allow_memory_tools": bool(req.enabled)})
    return {"success": True, "allow_memory_tools": bool(req.enabled)}


@router.post("/attach")
async def attach(req: AttachRequest) -> Dict[str, Any]:
    proc = process_manager.attach_to_process(req.process_name)
    if proc is None:
        raise HTTPException(status_code=404, detail="Process not found")
    return {"pid": proc.pid, "name": proc.name}


@router.post("/attach/pid")
async def attach_pid(req: AttachPidRequest) -> Dict[str, Any]:
    proc = process_manager.attach_to_pid(req.pid)
    if proc is None:
        raise HTTPException(status_code=404, detail="Process not found")
    return {"pid": proc.pid, "name": proc.name}


@router.post("/detach")
async def detach() -> Dict[str, Any]:
    removed = process_manager.detach_process()
    return {"detached": removed}


@router.post("/scan/value")
async def scan_value(req: ScanValueRequest) -> Dict[str, Any]:
    try:
        matches = scan_exact_value(req.value, req.type)
        return {"count": len(matches), "addresses": matches}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/scan/next")
async def scan_next(req: NextScanRequest) -> Dict[str, Any]:
    try:
        matches = scan_next_internal(req.mode, req.value, req.type)
        return {"count": len(matches), "addresses": matches}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/scan/pattern")
async def scan_pattern(req: PatternScanRequest) -> Dict[str, Any]:
    # For now this delegates to a generic scan and returns previous matches.
    try:
        matches = scan_pattern_internal(req.pattern)
        return {"count": len(matches), "addresses": matches}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/write")
async def write(req: WriteRequest) -> Dict[str, Any]:
    try:
        result = write_memory(req.address, req.type, req.value)
        return result
    except (RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/read")
async def read(req: ReadRequest) -> Dict[str, Any]:
    try:
        result = read_memory(req.address, req.type)
        return result
    except (RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/freeze")
async def freeze(req: FreezeRequest) -> Dict[str, Any]:
    try:
        result = freeze_memory(req.address, req.type, req.value, req.interval_ms)
        return result
    except (RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/unfreeze")
async def unfreeze(req: UnfreezeRequest) -> Dict[str, Any]:
    try:
        result = unfreeze_memory(req.address)
        return result
    except (RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/state")
async def get_state() -> GameWorldState:
    # This demo implementation reads from configured addresses if available.
    player = PlayerState()
    if "player_health" in _engine.address_map:
        player.health = int(read_memory(_engine.address_map["player_health"], "int")["value"])
    if "player_ammo" in _engine.address_map:
        player.ammo = int(read_memory(_engine.address_map["player_ammo"], "int")["value"])
    if "player_xp" in _engine.address_map:
        player.xp = int(read_memory(_engine.address_map["player_xp"], "int")["value"])

    state = GameWorldState(player=player, enemies=[], enemy_count=0)
    return state


@router.post("/ai/run")
async def ai_run(req: AIRunRequest) -> Dict[str, Any]:
    plan = _ai.run_step(req.state)
    return plan


@router.post("/profile/save")
async def save_profile(req: SaveProfileRequest) -> Dict[str, Any]:
    # Store any engine configuration plus caller-provided address map
    data = {
        "address_map": req.address_map,
    }
    result = profile_store.save_profile(req.game_id, data)
    # Also hydrate engine with this map for immediate reuse
    _engine.address_map.update(req.address_map)
    return result


@router.post("/profile/load")
async def load_profile(req: LoadProfileRequest) -> Dict[str, Any]:
    result = profile_store.load_profile(req.game_id)
    if result.get("success") and isinstance(result.get("data"), dict):
        addr_map = result["data"].get("address_map", {})
        if isinstance(addr_map, dict):
            # Apply to in-memory engine so trainer is immediately ready
            safe_map = {}
            for key, value in addr_map.items():
                if value is None:
                    continue
                try:
                    safe_map[key] = int(value)
                except (TypeError, ValueError):
                    continue
            _engine.address_map.update(safe_map)
    return result


@router.get("/profile/list")
async def list_profiles() -> Dict[str, Any]:
    return profile_store.list_profiles()


@router.post("/profile/export-cheat-engine")
async def export_cheat_engine(req: ExportCheatTableRequest) -> Dict[str, Any]:
    loaded = profile_store.load_profile(req.game_id)
    if not loaded.get("success"):
        return loaded
    data = loaded.get("data") or {}
    addr_map = data.get("address_map", {})
    result = profile_store.export_cheat_engine_table(req.game_id, addr_map)
    return result


@router.get("/steam/library")
async def steam_library_list() -> Dict[str, Any]:
    return steam_library.list_installed_games()


@router.get("/mods/list")
async def mods_list() -> Dict[str, Any]:
    return mod_workspace.list_workspaces()


@router.post("/mods/workspace")
async def mods_workspace(req: ModWorkspaceRequest) -> Dict[str, Any]:
    return mod_workspace.create_workspace(req.game_id, req.game_name, req.steam_app_id)
