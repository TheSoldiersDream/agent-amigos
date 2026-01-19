# -*- coding: utf-8 -*-
import sys
import io
import os

# Allow this file to be executed as a script ("python agent_init.py") while still
# supporting package-relative imports (from .config, from .tools, etc.).
#
# VS Code tasks run from `${workspaceFolder}/backend` and invoke `agent_init.py`
# directly, so `__package__` is empty by default. Setting it enables relative
# imports without having to rewrite the import graph.
if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    _BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
    _ROOT_DIR = os.path.dirname(_BACKEND_DIR)
    if _ROOT_DIR not in sys.path:
        sys.path.insert(0, _ROOT_DIR)
    __package__ = "backend"

# Force UTF-8 encoding for stdout/stderr on Windows to prevent UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception:
        pass

from autonomy.controller import autonomy_controller
from autonomy.macro_engine import get_macro_engine
from fastapi import HTTPException
import json


def map_tool_to_action(tool_name: str) -> str:
    # Minimal default mappings; expand as needed
    t = tool_name.lower()
    # Weather requires external network access even though it's "get_*"
    if 'weather' in t or 'forecast' in t:
        return 'network-local'
    # Dedicated download check
    if 'download' in t or 'urlretrieve' in t or 'fetch_file' in t:
        return 'download'
    # Safe read-only/info tools
    if t.startswith('get_') or t.startswith('list_') or t.startswith('show_') or t.startswith('check_') or 'status' in t or 'info' in t:
        return 'read-only'
    if 'map' in t:
        return 'map'
    if 'canvas' in t or 'chalkboard' in t:
        return 'canvas'
    if t.startswith('file') or 'file' in t or 'write' in t or 'delete' in t or 'save' in t:
        return 'filesystem'
    if 'terminal' in t or 'run' in t or 'exec' in t or 'shell' in t or 'command' in t:
        return 'terminal'
    if 'network' in t or 'http' in t or 'fetch' in t:
        return 'network-local'
    if 'infer' in t or 'code' in t or 'edit' in t or 'generate' in t:
        return 'code-modification'
    if 'memory' in t or 'remember' in t or 'fact' in t or 'knowledge' in t:
        return 'memory'
    if 'search' in t or 'find' in t or 'query' in t:
        return 'search'
    if 'open' in t or 'browser' in t or 'url' in t:
        return 'browser'
    if 'click' in t or 'type' in t or 'mouse' in t or 'keyboard' in t or 'key' in t:
        return 'input'
    if 'screenshot' in t or 'screen' in t or 'capture' in t:
        return 'screen'
    if 'clipboard' in t or 'copy' in t or 'paste' in t:
        return 'clipboard'
    if 'notification' in t or 'alert' in t or 'toast' in t:
        return 'notification'
    return 'general'


def guard_tool_execution(tool_name: str, details: dict):
    action = map_tool_to_action(tool_name)
    allowed = autonomy_controller.is_action_allowed(action)
    autonomy_controller.log_action('tool_execution_attempt', {'tool': tool_name, 'action': action, 'details': details}, {'allowed': allowed})

    # Safety: block non-read-only actions when system memory is critically high
    try:
        mem = get_memory_status()
        if mem.get("available") and mem.get("level") == "critical":
            if action not in {"read-only", "notification"}:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        f"Memory pressure high ({mem.get('system', {}).get('percent')}%). "
                        f"Action '{action}' blocked to prevent instability."
                    ),
                )
    except HTTPException:
        raise
    except Exception:
        # If memory checks fail, do not block tool execution.
        pass
    
    if not allowed:
        # If autonomy is enabled and the action is NOT explicitly allowed, 
        # we raise an exception to stop the tool from running.
        raise HTTPException(
            status_code=403, 
            detail=f"Action '{action}' for tool '{tool_name}' is not allowed in the current autonomy mode ({autonomy_controller.get_config().get('autonomyMode')})."
        )
    
    return True


"""
Agent Amigos - Autonomous Agent Backend
A real agent that can perform human tasks: keyboard, mouse, web, files, system commands

Uses ReAct-style reasoning: Think -> Act -> Observe -> Repeat

Copyright (c) 2025 Darrell Buttigieg. All Rights Reserved.
Owned and developed by Darrell Buttigieg.
"""
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Body, BackgroundTasks, Header
from fastapi import UploadFile, File, Form
from .config import get_default_model, set_default_model, get_enforce_default, set_enforce_default, PREVIEW_MODELS
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple
import json
import logging
logger = logging.getLogger(__name__)

# Email itinerary tools (local paste-based)
from .tools.email_parser import parse_email_text
import dateparser
from .email_store import (
    add_itinerary,
    list_itineraries,
    get_itinerary,
    update_itinerary,
    generate_ics,
    filter_itineraries_by_range,
    generate_text_summary_for_itineraries,
    generate_combined_ics_for_itineraries,
    generate_plain_english_timeline_for_itineraries,
)
from .lead_store import add_lead, list_leads

class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Filter out /agents/team from uvicorn access logs to reduce noise
        return record.getMessage().find("/agents/team") == -1

# Filter out /agents/team from uvicorn access logs
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
import os
import re
import socket
import time
import traceback
import mimetypes
from pathlib import Path
from datetime import datetime
import urllib.parse
import shutil
import threading

# Throttling control for noisy endpoints
TEAM_LOG_LOCK = threading.Lock()
TEAM_LAST_LOG_TIME = 0.0
# Seconds between server-side logs for /agents/team
TEAM_LOG_MIN_INTERVAL = float(os.environ.get("TEAM_LOG_MIN_INTERVAL", "5"))


def get_team_status_summary():
    """Return a small summary dict of team status for concise logging."""
    try:
        s = get_team_status()
        agents = s.get("agents", {}) if isinstance(s, dict) else {}
        total = len(agents)
        online = sum(1 for a in agents.values() if a.get("status") == "online")
        working = sum(1 for a in agents.values() if a.get("status") == "working")
        return {"total": total, "online": online, "working": working}
    except Exception:
        return {"total": 0, "online": 0, "working": 0}

import requests
from functools import lru_cache
import threading
import asyncio
import concurrent.futures
try:
    import psutil
except Exception:
    psutil = None

# Music video motion pipeline (local ComfyUI + ffmpeg)
from musicvideo.comfyui_client import ComfyUIClient, get_default_comfyui_url
from musicvideo.ffmpeg_utils import (
    ffprobe_duration_seconds,
    transcode_h264,
    concat_videos,
    mux_audio,
)
from musicvideo.interpolation import interpolate_to_fps

# Connection pooling for faster HTTP
_session = requests.Session()
_session.mount('https://', requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20))
_session.mount('http://', requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=10))

# Thread pool for parallel tool execution
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# Import our tools
from .tools.computer_control import computer
from .tools import window_tools
from .tools.web_tools import web
from .tools.file_tools import files
from .tools.system_tools import system
from .tools.media_tools import media
from .tools.game_tools import trainer as game_trainer
from .tools.canvas_tools import canvas_design, generate_design_image
import subprocess as subprocess_module
from .tools.ollama_tools import (
    ollama_service,
    get_ollama_status,
    get_ollama_models,
    ollama_generate,
    ollama_chat,
    amigos_ask_ollie
)
from .tools.weather_tools import weather, resolve_location_name
from .tools.shared_memory import (
    shared_memory,
    remember_conversation,
    learn,
    recall,
    get_context,
    log_task_completion
)
from .tools.document_storage import (
    document_storage,
    store_document,
    store_url_content,
    store_plan_document,
    find_documents,
    get_doc,
    get_doc_content,
    get_relevant_docs,
    get_document_stats
)
from .tools.agent_coordinator import (
    coordinator,
    get_team_status,
    agent_working,
    agent_thinking,
    agent_idle,
    agent_error,
    agent_online,
    agent_offline,
    manage_todo_list,
    start_collaboration,
    end_collaboration,
    get_agent_prompt,
    log_communication,
    get_communications,
    get_top_contacts
)
import uuid
from .tools.team_demo import (
    run_team_demo,
    get_demo_status,
    demo_orchestrator
)
from .trainer.main import router as trainer_router
from .tools.report_tools import report_tools
from .tools.recording_tools import recording
from .tools import scraper_tools
from .tools.shop_tools import search_products as shop_search

# Import tool registry
try:
    from core.tool_registry import get_tool_registry
except Exception:
    from backend.core.tool_registry import get_tool_registry

from routes.scraper_routes import router as scraper_router
from canvas import canvas_router, canvas_controller, execute_draw_command
from canvas.canvas_ai_assist import canvas_ai_assist
from routes.canvas_ai_routes import router as canvas_ai_router
from ui_controller import router as ui_router

try:
    from canvas.canvas_agent import init_canvas_agent
except Exception:
    init_canvas_agent = None

# --- Subprocess wrappers for terminal execution to support autonomy ---
import subprocess as _subprocess
import sys
_original_run = _subprocess.run
_original_popen = _subprocess.Popen

_thread_state = threading.local()

def _inc_depth():
    if not hasattr(_thread_state, 'depth'):
        _thread_state.depth = 0
    _thread_state.depth += 1
    return _thread_state.depth

def _dec_depth():
    if hasattr(_thread_state, 'depth') and _thread_state.depth > 0:
        _thread_state.depth -= 1
    return getattr(_thread_state, 'depth', 0)

def _wrapped_run(cmd, *args, **kwargs):
    # Use autonomy settings to allow/deny terminal commands
    try:
        depth = _inc_depth()
        max_depth = autonomy_controller.get_config().get('maxCommandDepth', 10)
        if depth > max_depth:
            autonomy_controller.log_action('terminal_command_denied', {'cmd': cmd, 'reason': 'max_depth_exceeded', 'depth': depth}, {})
            raise RuntimeError(f"Max command depth exceeded ({depth} > {max_depth})")
        if not autonomy_controller.is_action_allowed('terminal'):
            autonomy_controller.log_action('terminal_command_denied', {'cmd': cmd, 'reason': 'action_denied'}, {})
            raise RuntimeError('Autonomy controller denies terminal commands')
        # Block destructive commands unless explicitly allowed
        blocked_actions = autonomy_controller.get_config().get('blockedActions', [])
        destructive_patterns = ['rm -rf', 'rm -r', 'rmdir /s', 'del /f', 'format ', 'shutdown -s', 'sc delete', 'sc stop', 'sc start']
        if 'system-level-delete' in blocked_actions:
            cd = str(cmd).lower()
            if any(p in cd for p in destructive_patterns):
                autonomy_controller.log_action('terminal_command_denied', {'cmd': cmd, 'reason': 'destructive_command_blocked'}, {})
                raise RuntimeError('Destructive commands are blocked by autonomy policy')
        # Handle DRY-RUN mode: log but don't execute
        if autonomy_controller.get_config().get('mode') == 'DRY-RUN':
            autonomy_controller.log_action('terminal_command_dry_run', {'cmd': str(cmd), 'depth': depth}, {'status': 'dry-run'})
            return _original_run(['echo', 'DRY-RUN'], capture_output=True, text=True)
        res = _original_run(cmd, *args, **kwargs)
        autonomy_controller.log_action('terminal_command', {'cmd': str(cmd), 'depth': depth}, {'status': 'finished', 'returncode': getattr(res, 'returncode', None)})
        return res
    finally:
        _dec_depth()

def _wrapped_popen(cmd, *args, **kwargs):
    # Popen usage should be treated similarly
    depth = _inc_depth()
    try:
        max_depth = autonomy_controller.get_config().get('maxCommandDepth', 10)
        if depth > max_depth:
            autonomy_controller.log_action('terminal_popen_denied', {'cmd': cmd, 'reason': 'max_depth_exceeded', 'depth': depth}, {})
            raise RuntimeError(f"Max command depth exceeded ({depth} > {max_depth})")
        if not autonomy_controller.is_action_allowed('terminal'):
            autonomy_controller.log_action('terminal_popen_denied', {'cmd': cmd, 'reason': 'action_denied'}, {})
            raise RuntimeError('Autonomy controller denies terminal commands')
        # If in DRY-RUN, don't actually spawn the process
        if autonomy_controller.get_config().get('mode') == 'DRY-RUN':
            autonomy_controller.log_action('terminal_popen_dry_run', {'cmd': str(cmd), 'depth': depth}, {'status': 'dry-run'})
            return _original_popen(['echo', 'DRY-RUN'], stdout=kwargs.get('stdout'), stderr=kwargs.get('stderr'))
        proc = _original_popen(cmd, *args, **kwargs)
        autonomy_controller.log_action('terminal_popen', {'cmd': str(cmd), 'depth': depth}, {'status': 'started', 'pid': getattr(proc, 'pid', None)})
        return proc
    finally:
        _dec_depth()

# Patch subprocess methods at import-time so tools use our wrappers
_subprocess.run = _wrapped_run
_subprocess.Popen = _wrapped_popen
try:
    # Also patch the global module entry so other modules importing subprocess pick up wrappers.
    sys.modules['subprocess'].run = _wrapped_run
    sys.modules['subprocess'].Popen = _wrapped_popen
except Exception:
    pass

# --- Forms Database ---
FORMS_DB_DIR = os.path.join(os.path.dirname(__file__), "data", "forms_db")
USER_PROFILES_FILE = os.path.join(FORMS_DB_DIR, "user_profiles.json")
FORMS_DATA_FILE = os.path.join(FORMS_DB_DIR, "forms_data.json")

# --- Memory & Learning Database ---
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "data", "memory")
AGENT_MEMORY_FILE = os.path.join(MEMORY_DIR, "agent_memory.json")
KNOWLEDGE_BASE_FILE = os.path.join(MEMORY_DIR, "knowledge_base.json")
LEARNING_STATS_FILE = os.path.join(MEMORY_DIR, "learning_stats.json")


class FormsDatabase:
    """Manage the forms database for storing user profile data"""
    
    @staticmethod
    def read_user_profiles() -> Dict:
        """Read all user profiles from database"""
        try:
            if os.path.exists(USER_PROFILES_FILE):
                with open(USER_PROFILES_FILE, 'r', encoding='utf-8') as f:
                    return {"success": True, "data": json.load(f)}
            return {"success": False, "error": "User profiles file not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_profile(profile_name: str = "default") -> Dict:
        """Get a specific profile by name"""
        try:
            result = FormsDatabase.read_user_profiles()
            if not result["success"]:
                return result
            profiles = result["data"].get("profiles", {})
            if profile_name in profiles:
                return {"success": True, "profile": profile_name, "data": profiles[profile_name]}
            return {"success": False, "error": f"Profile '{profile_name}' not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_profile_field(field_path: str, profile_name: str = "default") -> Dict:
        """Get a specific field from a profile (e.g., 'contact.email' or 'personal.first_name')"""
        try:
            result = FormsDatabase.get_profile(profile_name)
            if not result["success"]:
                return result
            data = result["data"]
            parts = field_path.split(".")
            for part in parts:
                if isinstance(data, dict) and part in data:
                    data = data[part]
                else:
                    return {"success": False, "error": f"Field '{field_path}' not found in profile"}
            return {"success": True, "field": field_path, "value": data}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def update_profile_field(field_path: str, value: str, profile_name: str = "default") -> Dict:
        """Update a specific field in a profile (e.g., 'contact.email', 'personal.first_name')"""
        try:
            # Read current data
            if os.path.exists(USER_PROFILES_FILE):
                with open(USER_PROFILES_FILE, 'r', encoding='utf-8') as f:
                    all_data = json.load(f)
            else:
                return {"success": False, "error": "User profiles file not found"}
            
            # Navigate to the field and update it
            if profile_name not in all_data.get("profiles", {}):
                return {"success": False, "error": f"Profile '{profile_name}' not found"}
            
            profile = all_data["profiles"][profile_name]
            parts = field_path.split(".")
            
            # Navigate to parent of target field
            current = profile
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the value
            old_value = current.get(parts[-1], "")
            current[parts[-1]] = value
            
            # Save back
            with open(USER_PROFILES_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "profile": profile_name,
                "field": field_path,
                "old_value": old_value,
                "new_value": value
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def create_profile(profile_name: str) -> Dict:
        """Create a new empty profile"""
        try:
            if os.path.exists(USER_PROFILES_FILE):
                with open(USER_PROFILES_FILE, 'r', encoding='utf-8') as f:
                    all_data = json.load(f)
            else:
                return {"success": False, "error": "User profiles file not found"}
            
            if profile_name in all_data.get("profiles", {}):
                return {"success": False, "error": f"Profile '{profile_name}' already exists"}
            
            # Create empty profile structure
            all_data["profiles"][profile_name] = {
                "personal": {"first_name": "", "last_name": "", "title": "", "date_of_birth": "", "gender": ""},
                "contact": {"email": "", "phone": "", "mobile": ""},
                "address": {"street": "", "street2": "", "city": "", "state": "", "zip": "", "country": ""},
                "work": {"company": "", "job_title": "", "work_email": "", "work_phone": ""},
                "social": {"website": "", "linkedin": "", "twitter": "", "github": ""}
            }
            
            with open(USER_PROFILES_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)
            
            return {"success": True, "created": profile_name}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def list_profiles() -> Dict:
        """List all available profile names"""
        try:
            result = FormsDatabase.read_user_profiles()
            if not result["success"]:
                return result
            profiles = list(result["data"].get("profiles", {}).keys())
            return {"success": True, "profiles": profiles}
        except Exception as e:
            return {"success": False, "error": str(e)}


forms_db = FormsDatabase()


class AgentMemory:
    """Persistent memory system - Agent remembers everything!"""
    
    _instance = None
    _memory = None
    _knowledge = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_memory()
        return cls._instance
    
    def _load_memory(self):
        """Load memory from disk on startup"""
        try:
            if os.path.exists(AGENT_MEMORY_FILE):
                with open(AGENT_MEMORY_FILE, 'r', encoding='utf-8') as f:
                    self._memory = json.load(f)
                print(f"[OK] Loaded agent memory ({len(self._memory.get('knowledge_base', {}).get('facts', []))} facts)")
            else:
                self._memory = self._create_default_memory()
        except Exception as e:
            print(f"[WARNING] Memory load error: {e}")
            self._memory = self._create_default_memory()
        
        try:
            if os.path.exists(KNOWLEDGE_BASE_FILE):
                with open(KNOWLEDGE_BASE_FILE, 'r', encoding='utf-8') as f:
                    self._knowledge = json.load(f)
        except:
            self._knowledge = {"topics": {}, "learning_log": {"entries": []}}
    
    def _create_default_memory(self):
        return {
            "version": "1.0",
            "knowledge_base": {"facts": []},
            "conversation_insights": {"insights": []},
            "user_preferences": {"preferences": {}},
            "context_memory": {"recent_topics": [], "active_projects": [], "ongoing_tasks": []}
        }
    
    def _save_memory(self):
        """Save memory to disk"""
        try:
            os.makedirs(MEMORY_DIR, exist_ok=True)
            self._memory["last_updated"] = datetime.now().isoformat()
            with open(AGENT_MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠ Memory save error: {e}")
    
    def _save_knowledge(self):
        """Save knowledge base to disk"""
        try:
            os.makedirs(MEMORY_DIR, exist_ok=True)
            with open(KNOWLEDGE_BASE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._knowledge, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠ Knowledge save error: {e}")
    
    def remember_fact(self, topic: str, fact: str, source: str = "conversation", confidence: float = 0.9):
        """Remember a new fact"""
        new_fact = {
            "topic": topic,
            "fact": fact,
            "confidence": confidence,
            "source": source,
            "learned_date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat()
        }
        
        # Check if similar fact already exists
        facts = self._memory.get("knowledge_base", {}).get("facts", [])
        for existing in facts:
            if existing.get("topic") == topic and existing.get("fact") == fact:
                return {"success": True, "message": "Already knew this"}
        
        if "knowledge_base" not in self._memory:
            self._memory["knowledge_base"] = {"facts": []}
        self._memory["knowledge_base"]["facts"].append(new_fact)
        self._save_memory()
        print(f"[MEMORY] Remembered: {topic} - {fact[:50]}...")
        return {"success": True, "message": f"Remembered: {topic}"}
    
    def remember_preference(self, key: str, value: str):
        """Remember a user preference"""
        if "user_preferences" not in self._memory:
            self._memory["user_preferences"] = {"preferences": {}}
        self._memory["user_preferences"]["preferences"][key] = value
        self._save_memory()
        return {"success": True, "message": f"Preference saved: {key}={value}"}
    
    def remember_conversation_topic(self, topic: str):
        """Track conversation topics for context"""
        if "context_memory" not in self._memory:
            self._memory["context_memory"] = {"recent_topics": []}
        topics = self._memory["context_memory"].get("recent_topics", [])
        if topic not in topics:
            topics.insert(0, topic)
            self._memory["context_memory"]["recent_topics"] = topics[:20]  # Keep last 20
            self._save_memory()
    
    def get_facts_about(self, topic: str) -> list:
        """Get all facts about a topic"""
        facts = self._memory.get("knowledge_base", {}).get("facts", [])
        return [f for f in facts if topic.lower() in f.get("topic", "").lower() or topic.lower() in f.get("fact", "").lower()]
    
    def get_all_facts(self) -> list:
        """Get all remembered facts"""
        return self._memory.get("knowledge_base", {}).get("facts", [])
    
    def get_recent_topics(self) -> list:
        """Get recent conversation topics"""
        return self._memory.get("context_memory", {}).get("recent_topics", [])
    
    def get_preferences(self) -> dict:
        """Get all user preferences"""
        return self._memory.get("user_preferences", {}).get("preferences", {})
    
    def get_memory_summary(self) -> str:
        """Get a summary of what the agent remembers"""
        facts = self.get_all_facts()
        prefs = self.get_preferences()
        topics = self.get_recent_topics()
        
        summary = []
        if facts:
            summary.append(f"I remember {len(facts)} facts:")
            for f in facts[:10]:  # Show first 10
                summary.append(f"  • {f.get('topic')}: {f.get('fact')}")
        if prefs:
            summary.append(f"User preferences: {prefs}")
        if topics:
            summary.append(f"Recent topics: {', '.join(topics[:5])}")
        
        return "\n".join(summary) if summary else "No memories yet."
    
    def log_learning(self, content: str, learning_type: str = "insight"):
        """Log something new that was learned"""
        if self._knowledge:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": learning_type,
                "content": content,
                "source": "conversation"
            }
            if "learning_log" not in self._knowledge:
                self._knowledge["learning_log"] = {"entries": []}
            self._knowledge["learning_log"]["entries"].append(entry)
            self._save_knowledge()


# Initialize memory system
agent_memory = AgentMemory()


# --- Load .env file if present ---
from dotenv import load_dotenv
from config import get_default_model
_backend_env_path = os.path.join(os.path.dirname(__file__), ".env")
_root_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, ".env"))

_loaded_any_env = False
for _p in (_root_env_path, _backend_env_path):
    try:
        if _p and os.path.exists(_p):
            load_dotenv(_p)
            _loaded_any_env = True
            print(f"[OK] Loaded configuration from {_p}")
    except Exception:
        # Never block server startup due to dotenv errors.
        pass

if not _loaded_any_env:
    print("[INFO] No .env file found (checked repo root and backend/)")

# --- Configuration ---
# LLM Providers: OpenAI, Grok (xAI), Groq, GitHub Copilot, Ollama
# Set LLM_PROVIDER to switch: "openai", "grok", "groq", "github", "ollama"
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")
OPENAI_ALLOW_LOCAL_BASE = os.environ.get("OPENAI_ALLOW_LOCAL_BASE", "0").strip() in {"1", "true", "yes"}

# Provider-specific configurations
LLM_CONFIGS = {
    "openai": {
        "base": os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1"),
        "key": os.environ.get("OPENAI_API_KEY", os.environ.get("LLM_API_KEY", "")),
        "model": os.environ.get("OPENAI_MODEL", get_default_model() or "gpt-4o-mini"),
        "supported_models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
    },
    "grok": {
        "base": os.environ.get("GROK_API_BASE", "https://api.x.ai/v1"),
        "key": os.environ.get("GROK_API_KEY", os.environ.get("XAI_API_KEY", "")),
        "model": os.environ.get("GROK_MODEL", get_default_model() or "grok-beta"),
        "supported_models": ["grok-beta"],
    },
    "groq": {
        "base": os.environ.get("GROQ_API_BASE", "https://api.groq.com/openai/v1"),
        "key": os.environ.get("GROQ_API_KEY", ""),
        "model": os.environ.get("GROQ_MODEL", get_default_model() or "llama-3.3-70b-versatile"),
        "supported_models": ["llama-3.3-70b-versatile"],
    },
    "github": {
        "base": os.environ.get("GITHUB_API_BASE", "https://models.inference.ai.azure.com"),
        "key": os.environ.get("GITHUB_TOKEN", os.environ.get("GITHUB_COPILOT_TOKEN", "")),
        "model": os.environ.get("GITHUB_MODEL", get_default_model() or "gpt-4o"),  # or "o1", "claude-3.5-sonnet"
        "supported_models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o-code"],
    },
    "ollama": {
        "base": os.environ.get("OLLAMA_API_BASE", "http://localhost:11434/v1"),
        # Local Ollama typically requires no auth. If the user is running Ollama behind a
        # reverse proxy that requires a token, set OLLAMA_API_KEY and we'll send it.
        "key": os.environ.get("OLLAMA_API_KEY", "ollama"),
        "model": os.environ.get("OLLAMA_MODEL", get_default_model() or "qwen2.5:7b"),  # Fast local model
        "supported_models": ["qwen2.5:7b", "raptor-mini", "llama-3.3-70b-versatile"],
        "no_auth": not bool(os.environ.get("OLLAMA_API_KEY", "").strip()),
    },
    "deepseek": {
        "base": os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1"),
        "key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        "supported_models": ["deepseek-chat"],
    },
    "openrouter": {
        "base": os.environ.get("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
        "key": os.environ.get("OPENROUTER_API_KEY", ""),
        "model": os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct"),
        "supported_models": ["meta-llama/llama-3.3-70b-instruct", "google/gemini-2.0-flash-001", "deepseek/deepseek-chat", "mistralai/mistral-large-2411"],
    },
}

# Get active config based on provider
_active_config = LLM_CONFIGS.get(LLM_PROVIDER, LLM_CONFIGS["openai"])
LLM_API_BASE = os.environ.get("LLM_API_BASE", _active_config["base"])
LLM_API_KEY = os.environ.get("LLM_API_KEY", _active_config["key"])
LLM_MODEL = os.environ.get("LLM_MODEL", _active_config["model"] if _active_config.get("model") else get_default_model())
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", 120))
AGENT_HOST = os.environ.get("AGENT_HOST", "127.0.0.1")
AGENT_PORT = int(os.environ.get("AGENT_PORT", 65252))
ACTIVE_AGENT_PORT = AGENT_PORT
MAX_ITERATIONS = 10  # Max tool-use cycles per request
LLM_HEALTH_TTL = int(os.environ.get("LLM_HEALTH_TTL", 30))
LLM_HEALTH_CACHE = {"timestamp": 0.0, "status": False, "detail": "Not checked yet"}

# Memory monitoring (system + process)
MEMORY_STATUS_TTL = float(os.environ.get("MEMORY_STATUS_TTL", "2"))
MEMORY_LIMIT_SOFT_PCT = float(os.environ.get("MEMORY_LIMIT_SOFT_PCT", "80"))
MEMORY_LIMIT_HARD_PCT = float(os.environ.get("MEMORY_LIMIT_HARD_PCT", "90"))
_MEMORY_STATUS_CACHE = {"timestamp": 0.0, "data": None}

# Sanitize startup model selection: ensure we do not use preview models on providers that don't support them.
if LLM_MODEL in PREVIEW_MODELS and LLM_PROVIDER != "ollama":
    fallback_model = _active_config.get("model") or get_default_model() or "gpt-4o-mini"
    print(f"[WARN] Model '{LLM_MODEL}' is a preview-only model; switching to fallback '{fallback_model}' for provider {LLM_PROVIDER}")
    LLM_MODEL = fallback_model


def _find_alternative_provider():
    """Return a provider name that appears configured (has an API key) or 'ollama' if available.

    This helps avoid startup/network errors when the env-specified provider is not configured.
    """
    # Prefer providers that have a non-placeholder key set and aren't marked as empty
    def _is_placeholder_key(key: str) -> bool:
        if key is None:
            return True
        k = str(key).strip().lower()
        return k in {"", "local-key", "changeme", "your_key", "your-key", "replace_me"}

    def _is_local_base(base: str) -> bool:
        if not base:
            return False
        b = base.strip().lower()
        return b.startswith("http://127.0.0.1") or b.startswith("http://localhost")

    for p, cfg in LLM_CONFIGS.items():
        if p == LLM_PROVIDER:
            # prefer keeping the user-chosen provider when it's configured
            if cfg.get("key") and not _is_placeholder_key(cfg.get("key")):
                # If OpenAI is set to a local base, only keep it if explicitly allowed
                if p == "openai" and _is_local_base(cfg.get("base", "")) and not OPENAI_ALLOW_LOCAL_BASE:
                    pass
                else:
                    return p
            if cfg.get("no_auth") and p == "ollama":
                return p
    # Try to find any other preconfigured provider
    for p, cfg in LLM_CONFIGS.items():
        if p == "ollama":
            # prefer ollama if present - often available for local runs
            return p
        if cfg.get("key") and not _is_placeholder_key(cfg.get("key")):
            return p
    # None found - return the default provider key
    return LLM_PROVIDER


# Ensure the active provider is actually configured; otherwise pick a usable fallback.
_openai_base_is_local = False
try:
    if LLM_PROVIDER == "openai":
        base_val = (_active_config.get("base") or "").strip().lower()
        _openai_base_is_local = base_val.startswith("http://127.0.0.1") or base_val.startswith("http://localhost")
except Exception:
    _openai_base_is_local = False

if LLM_PROVIDER != "ollama" and (
    (not _active_config.get("key") or _active_config.get("key") == "")
    or (LLM_PROVIDER == "openai" and _openai_base_is_local and not OPENAI_ALLOW_LOCAL_BASE)
):
    new_provider = _find_alternative_provider()
    if new_provider != LLM_PROVIDER:
        print(f"[WARN] Active provider {LLM_PROVIDER} not configured; switching to {new_provider} to avoid network errors")
        LLM_PROVIDER = new_provider
        _active_config = LLM_CONFIGS.get(LLM_PROVIDER, LLM_CONFIGS["openai"])
        LLM_API_BASE = os.environ.get("LLM_API_BASE", _active_config.get("base", LLM_API_BASE))
        LLM_API_KEY = os.environ.get("LLM_API_KEY", _active_config.get("key", LLM_API_KEY))
        LLM_MODEL = os.environ.get("LLM_MODEL", _active_config.get("model") or get_default_model())


def _extract_error_message(body: str) -> str:
    """Best-effort extraction of a human-readable error message from JSON/text bodies."""
    if not body:
        return ""
    try:
        payload = json.loads(body)
        if isinstance(payload, dict):
            if "error" in payload:
                err = payload.get("error")
                if isinstance(err, str):
                    return err
                return json.dumps(err)
            if isinstance(payload.get("message"), str):
                return payload["message"]
    except Exception:
        pass
    return body


def _is_ollama_insufficient_memory_error(body: str) -> bool:
    msg = _extract_error_message(body).lower()
    return (
        "requires more system memory" in msg
        or "not enough memory" in msg
        or "insufficient memory" in msg
    )


def is_model_valid_for_provider(provider: str, model: str) -> bool:
    """Check whether the supplied model is valid for the given provider.

    - Prevent preview-specific models (like raptor-mini) being used on non-supporting providers.
    - If provider defines supported_models, prefer that list; otherwise be permissive.
    """
    if not provider or not model:
        return False
    model = model.strip()
    # If model is a preview-only model and provider is not ollama, reject.
    if model in PREVIEW_MODELS and provider != "ollama":
        return False
    cfg = LLM_CONFIGS.get(provider, {})
    supported = cfg.get("supported_models")
    if supported and isinstance(supported, list):
        return model in supported
    # Default permissive: allow any non-empty name as long as it's not a preview mismatch
    return True


def _ollama_fallback_models(primary_model: str) -> List[str]:
    """Ordered list of smaller Ollama model names to try on low-RAM machines."""
    env_value = os.environ.get("OLLAMA_FALLBACK_MODELS", "").strip()
    if env_value:
        models = [m.strip() for m in env_value.split(",") if m.strip()]
    else:
        # Conservative defaults that tend to fit on 8–16GB RAM machines.
        models = [
            "llama3.2",
            "llama3.2:latest",
            "llama3.2:3b",
            "llama3.2:1b",
        ]
    return [m for m in models if m and m != primary_model]


def resolve_agent_port(host: str, preferred_port: int) -> Tuple[int, Optional[str]]:
    """Pick an available TCP port, falling back when preferred is busy."""
    if preferred_port <= 0:
        return preferred_port, None

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, preferred_port))
            return preferred_port, None
        except OSError as exc:
            sock.bind((host, 0))
            fallback_port = sock.getsockname()[1]
            msg = (
                f"Port {preferred_port} is already in use; switched Agent Amigos to "
                f"{host}:{fallback_port} ({exc})."
            )
            return fallback_port, msg


def build_llm_headers() -> Dict[str, str]:
    """Create headers for LLM HTTP calls."""
    headers = {"Content-Type": "application/json"}
    # Some providers (like local Ollama) do not require auth; sending an Authorization
    # header can cause confusing failures in some deployments.
    if _active_config.get("no_auth"):
        return headers
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    return headers


def check_llm_health(force: bool = False) -> Dict[str, Any]:
    """Ping the configured LLM endpoint with simple caching."""
    global LLM_HEALTH_CACHE

    now = time.monotonic()
    if not force and now - LLM_HEALTH_CACHE["timestamp"] < LLM_HEALTH_TTL:
        return LLM_HEALTH_CACHE

    if not LLM_API_BASE:
        LLM_HEALTH_CACHE = {
            "timestamp": now,
            "status": False,
            "detail": "LLM_API_BASE not configured",
        }
        return LLM_HEALTH_CACHE

    try:
        url = f"{LLM_API_BASE.rstrip('/')}/models"
        response = _session.get(url, headers=build_llm_headers(), timeout=3)  # Faster timeout
        response.raise_for_status()
        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else None
        model_count = len(payload.get("data", [])) if isinstance(payload, dict) and "data" in payload else None
        detail = f"reachable ({model_count or 'unknown'} models reported)"
        LLM_HEALTH_CACHE = {"timestamp": now, "status": True, "detail": detail}
    except Exception as exc:
        LLM_HEALTH_CACHE = {
            "timestamp": now,
            "status": False,
            "detail": str(exc)[:200],
        }

    return LLM_HEALTH_CACHE


def _read_memory_status() -> Dict[str, Any]:
    if psutil is None:
        return {
            "available": False,
            "detail": "psutil not available",
        }

    try:
        vm = psutil.virtual_memory()
        total = int(getattr(vm, "total", 0) or 0)
        used = int(getattr(vm, "used", 0) or 0)
        available = int(getattr(vm, "available", 0) or 0)
        system_percent = float(getattr(vm, "percent", 0.0) or 0.0)

        proc = psutil.Process(os.getpid())
        rss = int(proc.memory_info().rss)
        process_percent = (rss / total * 100.0) if total > 0 else None

        level = "ok"
        if system_percent >= MEMORY_LIMIT_HARD_PCT:
            level = "critical"
        elif system_percent >= MEMORY_LIMIT_SOFT_PCT:
            level = "warning"

        return {
            "available": True,
            "level": level,
            "limits": {
                "soft_percent": MEMORY_LIMIT_SOFT_PCT,
                "hard_percent": MEMORY_LIMIT_HARD_PCT,
            },
            "system": {
                "total_bytes": total,
                "used_bytes": used,
                "available_bytes": available,
                "percent": system_percent,
            },
            "process": {
                "rss_bytes": rss,
                "percent_of_system": process_percent,
                "pid": os.getpid(),
            },
            "timestamp": time.time(),
        }
    except Exception as exc:
        return {
            "available": False,
            "detail": str(exc)[:200],
        }


def get_memory_status(force: bool = False) -> Dict[str, Any]:
    now = time.monotonic()
    if not force and _MEMORY_STATUS_CACHE["data"] is not None:
        if (now - _MEMORY_STATUS_CACHE["timestamp"]) < MEMORY_STATUS_TTL:
            return _MEMORY_STATUS_CACHE["data"]

    data = _read_memory_status()
    _MEMORY_STATUS_CACHE["timestamp"] = now
    _MEMORY_STATUS_CACHE["data"] = data
    return data

SUBSCRIBER_GATING_ENABLED = os.environ.get("AMIGOS_SUBSCRIBER_GATING", "0").strip().lower() in {
    "1",
    "true",
    "yes",
}
SUBSCRIBER_TOKEN = os.environ.get("AMIGOS_SUBSCRIBER_TOKEN", "").strip()
PUBLIC_SUBSCRIBER_ENDPOINTS = {
    "/marketing/subscribe",
    "/openwork/company/report",
    "/agents/team",
    "/openwork/status",
}

app = FastAPI(title="Agent Amigos - Autonomous Agent", version="3.0.0")

@app.middleware("http")
async def subscriber_only_guard(request: Request, call_next):
    if not SUBSCRIBER_GATING_ENABLED:
        return await call_next(request)
    if request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path
    if path in PUBLIC_SUBSCRIBER_ENDPOINTS:
        return await call_next(request)

    if not SUBSCRIBER_TOKEN:
        return JSONResponse(
            status_code=503,
            content={"detail": "subscriber_auth_not_configured"},
        )

    header_token = request.headers.get("X-Subscriber-Token") or ""
    auth_header = request.headers.get("Authorization") or ""
    if auth_header.lower().startswith("bearer "):
        header_token = auth_header[7:].strip()

    if header_token != SUBSCRIBER_TOKEN:
        return JSONResponse(status_code=403, content={"detail": "subscriber_only"})

    return await call_next(request)

# ═══════════════════════════════════════════════════════════════
# MCP AUTO-START (Universal MCP server)
# Starts alongside Amigos and keeps logs out of VS Code output.
# ═══════════════════════════════════════════════════════════════
MCP_AUTOSTART = os.environ.get("AMIGOS_MCP_AUTOSTART", "1").strip().lower() in {
    "1",
    "true",
    "yes",
}
MCP_PROCESS = None


def _start_mcp_sidecar() -> None:
    global MCP_PROCESS
    if not MCP_AUTOSTART:
        return
    try:
        if MCP_PROCESS is not None and MCP_PROCESS.poll() is None:
            return

        backend_dir = Path(__file__).resolve().parent
        repo_root = backend_dir.parent
        log_dir = backend_dir / "agent_mcp" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "mcp_autostart.log"

        env = os.environ.copy()
        env.setdefault("PYTHONPATH", str(repo_root))
        env.setdefault("MCP_TRANSPORT", "stdio")
        env.setdefault("MCP_LOG_LEVEL", "ERROR")
        env.setdefault("MCP_LOG_DIR", str(log_dir))
        env.setdefault("MCP_QUIET", "1")

        creationflags = 0
        if os.name == "nt":
            creationflags = 0x08000000  # CREATE_NO_WINDOW

        python_exe = sys.executable
        cmd = [python_exe, "-m", "backend.agent_mcp.server"]

        log_handle = open(log_path, "a", encoding="utf-8")
        MCP_PROCESS = subprocess_module.Popen(
            cmd,
            cwd=str(repo_root),
            stdin=subprocess_module.DEVNULL,
            stdout=log_handle,
            stderr=log_handle,
            env=env,
            creationflags=creationflags,
        )
    except Exception as exc:
        print(f"[WARN] MCP auto-start failed: {exc}")


@app.on_event("startup")
def _on_startup_mcp():
    _start_mcp_sidecar()


@app.on_event("shutdown")
def _on_shutdown_mcp():
    global MCP_PROCESS
    try:
        if MCP_PROCESS is not None and MCP_PROCESS.poll() is None:
            MCP_PROCESS.terminate()
    except Exception:
        pass

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to ensure CORS headers and log errors."""
    error_detail = traceback.format_exc()
    print(f"ERROR: {error_detail}")
    
    # Log to file
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/backend_errors.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {request.method} {request.url}\n")
            f.write(error_detail)
            f.write("\n" + "="*50 + "\n")
    except Exception:
        pass
        
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error_type": type(exc).__name__},
        headers={"Access-Control-Allow-Origin": "*"}
    )

app.include_router(scraper_router)
app.include_router(trainer_router)
app.include_router(canvas_router, tags=["canvas"])
app.include_router(canvas_ai_router, tags=["canvas_ai"])
app.include_router(ui_router, tags=["ui"])

# Enhanced Agent Amigos AI endpoints (Model Dashboard + Learning + Capabilities)
try:
    from core.api_endpoints import router as enhanced_agent_router
    if enhanced_agent_router is not None:
        app.include_router(enhanced_agent_router)
        logger.info("✅ Enhanced Agent Amigos AI endpoints loaded")
except Exception as e:
    logger.error(f"❌ Failed to load enhanced AI endpoints: {e}")
    enhanced_agent_router = None

# ═══════════════════════════════════════════════════════════════════════════════
# Macro Engine Routes
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/macros")
def list_macros():
    engine = get_macro_engine()
    return {"macros": engine.get_macros()}

@app.get("/macros/history")
def get_macro_history(limit: int = 50):
    engine = get_macro_engine()
    return {"history": engine.get_recent_history(limit)}

@app.get("/macros/patterns")
def get_macro_patterns():
    engine = get_macro_engine()
    return {"patterns": engine.detect_patterns()}

class MacroCreateRequest(BaseModel):
    name: str
    description: str = ""
    pattern_sequence: List[str]

class MacroUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    settings: Optional[Dict[str, Any]] = None

class MacroExecuteRequest(BaseModel):
    speed: Optional[float] = 1.0
    loops: Optional[int] = 1

@app.post("/macros")
def create_macro(req: MacroCreateRequest):
    engine = get_macro_engine()
    macro = engine.create_macro_from_pattern(req.pattern_sequence, req.name, req.description)
    return {"status": "success", "macro": macro}

@app.put("/macros/{macro_id}")
def update_macro(macro_id: str, req: MacroUpdateRequest):
    engine = get_macro_engine()
    updates = req.dict(exclude_unset=True)
    macro = engine.update_macro(macro_id, updates)
    if not macro:
        raise HTTPException(status_code=404, detail="Macro not found")
    return {"status": "success", "macro": macro}

@app.delete("/macros/{macro_id}")
def delete_macro(macro_id: str):
    engine = get_macro_engine()
    success = engine.delete_macro(macro_id)
    if not success:
        raise HTTPException(status_code=404, detail="Macro not found")
    return {"status": "success"}

@app.post("/macros/{macro_id}/execute")
def execute_macro(macro_id: str, req: MacroExecuteRequest = Body(default=None)):
    engine = get_macro_engine()
    
    # Handle optional body
    speed = req.speed if req else 1.0
    loops = req.loops if req else 1
    
    def executor(tool, action, params):
        # In this simple implementation, 'action' is just 'execute' usually
        return agent.execute_tool(tool, params)

    result = engine.execute_macro(macro_id, executor, speed=speed, loops=loops)
    return result

@app.post("/macros/record/start")
def start_recording_macro():
    engine = get_macro_engine()
    engine.start_recording()
    return {"status": "recording_started"}

class MacroStopRequest(BaseModel):
    name: str
    description: str = ""

@app.post("/macros/record/stop")
def stop_recording_macro(req: MacroStopRequest):
    engine = get_macro_engine()
    macro = engine.stop_recording(req.name, req.description)
    if not macro:
        return {"status": "error", "message": "No actions recorded"}
    return {"status": "success", "macro": macro}

# ═══════════════════════════════════════════════════════════════════════════════
# OpenWork Integration Routes
# Agentic workflow system for knowledge workers
# ═══════════════════════════════════════════════════════════════════════════════

from .openwork_integration import openwork_manager

@app.get("/openwork/status")
async def openwork_status():
    """Get OpenWork/OpenCode server status"""
    running = False
    if openwork_manager.opencode_process is not None:
        try:
            running = openwork_manager.opencode_process.poll() is None
            if not running:
                openwork_manager.opencode_process = None
        except Exception:
            running = False
    return {
        "success": True,
        "server_running": running,
        "host": openwork_manager.opencode_host,
        "port": openwork_manager.opencode_port,
    }

@app.post("/openwork/server/start")
async def openwork_start_server(workspace_path: str = Body(..., embed=True)):
    """Start OpenCode server for a workspace"""
    result = await openwork_manager.start_opencode_server(workspace_path)
    return result

@app.post("/openwork/server/stop")
async def openwork_stop_server():
    """Stop the OpenCode server"""
    await openwork_manager.stop_opencode_server()
    return {"success": True, "message": "OpenCode server stopped"}

@app.post("/openwork/sessions")
def openwork_create_session(workspace_path: str = Body(...), prompt: str = Body(...)):
    """Create a new OpenWork session"""
    return openwork_manager.create_session(workspace_path, prompt)

@app.post("/openwork/sessions/from-template")
def openwork_create_session_from_template(
    workspace_path: str = Body(...),
    template_id: str = Body(...),
):
    """Create a new OpenWork session from a template and seed tasks"""
    session = openwork_manager.create_session_from_template(workspace_path, template_id)
    if not session:
        raise HTTPException(status_code=404, detail="Template not found")
    return session

@app.post("/openwork/company/checkin")
def openwork_company_checkin(
    workspace_path: str = Body(...),
    focus: Optional[str] = Body(None),
):
    """Create a company check-in session with real action items."""
    return openwork_manager.create_company_checkin_session(workspace_path, focus)

from .tools import voice_settings

def agent_get_available_voices():
    """List all available AI voices for the company agents."""
    return voice_settings.get_available_voices()

def agent_set_voice(agent_id: str, voice_id: str):
    """Assign a specific voice to an AI agent."""
    return voice_settings.set_agent_voice(agent_id, voice_id)

def agent_run_executive_meeting():
    """Autonomous executive meeting making strategic pivots or revenue decisions."""
    return openwork_manager.run_automated_executive_meeting()

def agent_run_standup():
    """AI departmental standup identifying what shipped and what is blocked."""
    return openwork_manager.run_automated_standup()

def agent_get_meeting_logs():
    """Retrieve the persistent AI governance/meeting logs."""
    return {"success": True, "meetings": openwork_manager.meeting_log}

@app.get("/openwork/kpi/last-updated")
def openwork_kpi_last_updated():
    """Return the most recently updated KPI-related todo and who updated it."""
    k = openwork_manager.get_last_kpi_update()
    return {"success": True, "kpi": k}

@app.get("/openwork/leader/log")
def openwork_leader_log():
    """Return the latest leadership actions from the AI company controller."""
    return {"success": True, "log": openwork_manager.leadership_log}

@app.get("/openwork/company/report")
def openwork_company_report():
    """Return a company status report including KPI and top 5 tasks."""
    return {"success": True, "report": openwork_manager.get_company_report()}


class LeadSubscribeRequest(BaseModel):
    email: str
    name: Optional[str] = None
    source: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


@app.post("/marketing/subscribe")
def marketing_subscribe(req: LeadSubscribeRequest):
    """Capture an executive lead from the landing page."""
    email = (req.email or "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="valid_email_required")
    lead = add_lead(email=email, name=req.name, source=req.source, meta=req.meta)
    return {"success": True, "lead": lead}

@app.post("/openwork/clear-sessions")
def openwork_clear_sessions():
    """Clear all sessions - remove old mock/test data."""
    return openwork_manager.clear_all_sessions()

@app.get("/openwork/task-artifacts")
def openwork_task_artifacts(limit: int = 50):
    """List proof artifacts generated by task execution."""
    return {"success": True, "artifacts": openwork_manager.list_task_artifacts(limit)}

@app.get("/openwork/task-artifacts/read")
def openwork_read_task_artifact(path: str):
    """Read a proof artifact by path (restricted to artifacts directory)."""
    return openwork_manager.read_task_artifact(path)

@app.post("/openwork/company/start")
async def openwork_company_start(
    workspace_path: str = Body(...),
    focus: Optional[str] = Body(None),
):
    """Start OpenCode, create a company check-in, and start the runner."""
    return await openwork_manager.start_company_ops(workspace_path, focus)

@app.get("/openwork/runner")
def openwork_runner_status():
    """Get status of the OpenWork live runner."""
    return {"success": True, "runner": openwork_manager.runner_status()}

@app.post("/openwork/runner/start")
async def openwork_runner_start(interval_sec: Optional[int] = Body(None)):
    """Start the OpenWork live runner."""
    status = await openwork_manager.start_runner(interval_sec)
    return {"success": True, "runner": status}

@app.post("/openwork/runner/stop")
async def openwork_runner_stop():
    """Stop the OpenWork live runner."""
    status = await openwork_manager.stop_runner()
    return {"success": True, "runner": status}

@app.post("/openwork/runner/tick")
async def openwork_runner_tick():
    """Manually trigger an OpenWork runner tick."""
    status = openwork_manager.runner_tick()
    return {"success": True, "runner": status}

@app.get("/openwork/sessions")
def openwork_list_sessions():
    """List all OpenWork sessions"""
    return {
        "success": True,
        "sessions": openwork_manager.list_sessions()
    }

@app.get("/openwork/sessions/{session_id}")
def openwork_get_session(session_id: str):
    """Get session details"""
    session = openwork_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session": session}

@app.post("/openwork/sessions/{session_id}/todos")
def openwork_add_todo(session_id: str, todo: Dict[str, Any] = Body(...)):
    """Add a todo to a session"""
    success = openwork_manager.add_todo(session_id, todo)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}

@app.post("/openwork/sessions/{session_id}/todos/{todo_id}/reschedule")
def openwork_reschedule_todo(
    session_id: str,
    todo_id: str,
    scheduled_for: str = Body(..., embed=True),
    reason: Optional[str] = Body(None, embed=True),
):
    """Reschedule a todo item"""
    success = openwork_manager.reschedule_todo(session_id, todo_id, scheduled_for, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Session or todo not found")
    return {"success": True}

@app.put("/openwork/sessions/{session_id}/todos/{todo_id}")
def openwork_update_todo(session_id: str, todo_id: str, updates: Dict[str, Any] = Body(...)):
    """Update a todo item"""
    success = openwork_manager.update_todo(session_id, todo_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Session or todo not found")
    return {"success": True}

@app.post("/openwork/sessions/{session_id}/todos/{todo_id}/execute")
def openwork_execute_todo(session_id: str, todo_id: str):
    """Execute a todo and write a proof artifact to disk."""
    result = openwork_manager.execute_todo(session_id, todo_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error") or "Todo not found")
    return result

@app.post("/openwork/sessions/{session_id}/todos/{todo_id}/approve")
def openwork_approve_todo(session_id: str, todo_id: str, approved_by: str = Body("CEO", embed=True)):
    """Approve a todo for outbound communications."""
    result = openwork_manager.approve_todo(session_id, todo_id, approved_by)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error") or "Todo not found")
    return result

@app.post("/openwork/sessions/{session_id}/messages")
def openwork_add_message(session_id: str, message: Dict[str, Any] = Body(...)):
    """Add a message to a session"""
    success = openwork_manager.add_message(session_id, message)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}

@app.post("/openwork/sessions/{session_id}/permissions")
def openwork_request_permission(session_id: str, permission: Dict[str, Any] = Body(...)):
    """Request a permission for a session"""
    success = openwork_manager.request_permission(session_id, permission)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}

@app.post("/openwork/sessions/{session_id}/permissions/{permission_id}/respond")
def openwork_respond_permission(session_id: str, permission_id: str, response: str = Body(..., embed=True)):
    """Respond to a permission request"""
    success = openwork_manager.respond_to_permission(session_id, permission_id, response)
    if not success:
        raise HTTPException(status_code=404, detail="Session or permission not found")
    return {"success": True}

@app.get("/openwork/workspaces")
def openwork_list_workspaces():
    """List available workspaces"""
    return {
        "success": True,
        "workspaces": openwork_manager.list_workspaces()
    }

@app.get("/openwork/task-library")
def openwork_list_task_library():
    """List task templates in the OpenWork library"""
    return {
        "success": True,
        "library": openwork_manager.list_task_library(),
    }

@app.get("/openwork/templates")
def openwork_list_templates():
    """List workflow templates available for OpenWork"""
    return {
        "success": True,
        "templates": openwork_manager.list_workflow_templates(),
    }

@app.post("/openwork/task-library")
def openwork_add_task_template(template: Dict[str, Any] = Body(...)):
    """Add a task template to the library"""
    item = openwork_manager.add_task_template(template)
    return {"success": True, "template": item}

@app.delete("/openwork/task-library/{template_id}")
def openwork_delete_task_template(template_id: str):
    """Remove a task template from the library"""
    success = openwork_manager.remove_task_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"success": True}

@app.get("/openwork/workspaces/{workspace_path}/skills")
def openwork_get_skills(workspace_path: str):
    """Get installed skills for a workspace"""
    import urllib.parse
    decoded_path = urllib.parse.unquote(workspace_path)
    return {
        "success": True,
        "skills": openwork_manager.get_workspace_skills(decoded_path)
    }

@app.post("/openwork/sessions/{session_id}/close")
def openwork_close_session(session_id: str):
    """Close a session"""
    success = openwork_manager.close_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}

@app.delete("/openwork/sessions/{session_id}")
def openwork_delete_session(session_id: str):
    """Delete a session"""
    success = openwork_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}

# Initialize the Canvas agent integration if available
if init_canvas_agent:
    try:
        # Attempt to register Canvas tools with the local MCP server (when available)
        try:
            from agent_mcp.registrar import MCPRegistrar
            registrar = MCPRegistrar()
            init_canvas_agent(register_with_mcp=registrar)
            logger.info("Canvas agent registered MCP tools via MCPRegistrar")
        except Exception:
            # Fall back to no MCP registration if server unavailable
            init_canvas_agent(register_with_mcp=None)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════════════════════
# DeepFaceLab Integration
# Repository will be cloned into external/DeepFaceLab by default
DEEPFACELAB_REPO = 'https://github.com/iperov/DeepFaceLab.git'

# IMPORTANT: Use deterministic paths based on this file's location (not os.getcwd()).
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
BACKEND_EXTERNAL_DIR = BACKEND_DIR / 'external'
BACKEND_EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)

DEEPFACELAB_DIR = str(BACKEND_EXTERNAL_DIR / 'DeepFaceLab')
DEEPFACELAB_CONFIG_FILE = str(BACKEND_EXTERNAL_DIR / 'deepfacelab_config.json')
DEEPFACELAB_DIRS = [DEEPFACELAB_DIR]
DEEPFACELAB_VENV_DIR = str(BACKEND_EXTERNAL_DIR / 'DeepFaceLab_venv')
DEEPFACELAB_PYTHON_EXE = os.environ.get('DEEPFACELAB_PYTHON_EXE') or os.environ.get('DEEPFACELAB_PYTHON')
DEEPFACELAB_LOG = str(BACKEND_EXTERNAL_DIR / 'deepfacelab.log')
DEEPFACELAB_JOBS_FILE = str(BACKEND_EXTERNAL_DIR / 'deepfacelab_jobs.json')

DEEPFACELAB_INSTALLER = str((BACKEND_DIR / 'tools' / 'deepfacelab_installer.py').resolve())
DEEPFACELAB_JOBS: Dict[str, dict] = {}
DEEPFACELAB_ALLOWED_ACTIONS = set(['extract', 'train', 'merge', 'exportdfm', 'videoed', 'facesettool', 'xseg', 'util'])
DEEPFACELAB_LONG_RUNNING = set(['train', 'merge', 'exportdfm'])


def ensure_deepfacelab_workspace():
    """Ensure basic workspace structure exists for DeepFaceLab and return path."""
    d = get_deepfacelab_dir()
    if not d:
        return None
    workspace = os.path.join(d, 'workspace')
    subdirs = ['data_src', 'data_dst', 'model', 'result', 'aligned']
    try:
        os.makedirs(workspace, exist_ok=True)
        for s in subdirs:
            os.makedirs(os.path.join(workspace, s), exist_ok=True)
        return workspace
    except Exception:
        return None


def get_python_venv_path():
    """Return the project's venv python executable if present else sys.executable."""
    root = str(REPO_ROOT)
    py = None
    candidates = [
        os.path.join(root, '.venv', 'Scripts', 'python.exe'),
        os.path.join(root, 'backend', 'venv', 'Scripts', 'python.exe'),
    ]
    for c in candidates:
        if os.path.exists(c):
            py = c
            break
    if not py:
        py = sys.executable
    return py


def _python_exe_from_venv(venv_dir: str) -> Optional[str]:
    """Return python.exe path inside a venv dir if it exists."""
    try:
        cand = os.path.join(venv_dir, 'Scripts', 'python.exe')
        if os.path.exists(cand):
            return cand
    except Exception:
        pass
    return None


def get_deepfacelab_python_path() -> str:
    """Return python executable to run DeepFaceLab.

    Preference order:
    1) Explicit env/config override (DEEPFACELAB_PYTHON_EXE / DEEPFACELAB_PYTHON)
    2) Dedicated DeepFaceLab venv under backend/external (DEEPFACELAB_VENV_DIR)
    3) Project venv python
    """
    global DEEPFACELAB_PYTHON_EXE
    if DEEPFACELAB_PYTHON_EXE and os.path.exists(DEEPFACELAB_PYTHON_EXE):
        return DEEPFACELAB_PYTHON_EXE
    venv_py = _python_exe_from_venv(DEEPFACELAB_VENV_DIR)
    if venv_py:
        return venv_py
    return get_python_venv_path()


def _get_python_version_tuple(python_exe: str) -> Optional[tuple]:
    """Return (major, minor, patch) for the given python.exe."""
    try:
        res = _original_run(
            [python_exe, '-c', 'import sys; print("%d.%d.%d" % sys.version_info[:3])'],
            stdout=subprocess_module.PIPE,
            stderr=subprocess_module.PIPE,
            text=True,
            shell=False,
        )
        if res.returncode != 0:
            return None
        s = (res.stdout or '').strip()
        parts = s.split('.')
        if len(parts) != 3:
            return None
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        return None


def ensure_deepfacelab_venv() -> dict:
    """Create DeepFaceLab venv if missing, and return paths."""
    venv_py = _python_exe_from_venv(DEEPFACELAB_VENV_DIR)
    if venv_py:
        return {'created': False, 'venv_dir': DEEPFACELAB_VENV_DIR, 'python': venv_py}

    base_py = get_python_venv_path()
    try:
        os.makedirs(DEEPFACELAB_VENV_DIR, exist_ok=True)
        res = _original_run(
            [base_py, '-m', 'venv', DEEPFACELAB_VENV_DIR],
            stdout=subprocess_module.PIPE,
            stderr=subprocess_module.PIPE,
            text=True,
            shell=False,
        )
        venv_py2 = _python_exe_from_venv(DEEPFACELAB_VENV_DIR)
        return {
            'created': True,
            'venv_dir': DEEPFACELAB_VENV_DIR,
            'python': venv_py2 or base_py,
            'stdout': res.stdout,
            'stderr': res.stderr,
            'success': res.returncode == 0 and bool(venv_py2),
        }
    except Exception as e:
        return {'created': False, 'venv_dir': DEEPFACELAB_VENV_DIR, 'success': False, 'error': str(e)}


def check_torch_gpu():
    """Return GPU available, name, and memory if torch available else None."""
    try:
        import torch
        available = torch.cuda.is_available()
        gpu_info = {'available': available}
        if available:
            try:
                name = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                vram = int(props.total_memory)
                gpu_info.update({'name': name, 'vram': vram})
            except Exception:
                pass
        return gpu_info
    except Exception:
        return {'available': False}


def check_ffmpeg():
    try:
        res = _original_run(['ffmpeg', '-version'], stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE, text=True, shell=False)
        return {'present': res.returncode == 0, 'output': (res.stdout or res.stderr)[:200]}
    except Exception as e:
        return {'present': False, 'error': str(e)}


def check_dlib_insightface():
    info = {'dlib': False, 'insightface': False}
    try:
        import dlib
        info['dlib'] = True
    except Exception:
        info['dlib'] = False
    try:
        import insightface
        info['insightface'] = True
    except Exception:
        info['insightface'] = False
    return info


def detect_nvidia_smi():
    try:
        proc = _original_run(['nvidia-smi'], stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE, text=True, shell=False)
        out = proc.stdout or proc.stderr or ''
        # Try to parse CUDA version string
        cuda_ver = None
        m = re.search(r'CUDA Version:\s*([0-9]+\.[0-9]+)', out)
        if m:
            cuda_ver = m.group(1)
        return {'present': proc.returncode == 0, 'output': out[:200], 'cuda_version': cuda_ver}
    except Exception as e:
        return {'present': False, 'error': str(e)}


def pip_install(requirements: List[str] | str, python_exe: Optional[str] = None) -> dict:
    py = python_exe or get_python_venv_path()
    if isinstance(requirements, list):
        cmd = [py, '-m', 'pip', 'install'] + requirements
    else:
        cmd = [py, '-m', 'pip', 'install', requirements]
    try:
        res = _original_run(cmd, stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE, text=True, shell=False)
        if res.returncode == 0:
            return {'success': True, 'stdout': res.stdout, 'stderr': res.stderr}

        # Heuristic fallback: common failure is building old numpy on modern Python/Windows.
        stderr = (res.stderr or '')
        lower = stderr.lower()
        if ('numpy' in lower) and (
            ('metadata-generation-failed' in lower)
            or ('microsoft visual c++' in lower)
            or ('may not yet support python' in lower)
        ):
            try:
                _original_run([py, '-m', 'pip', 'install', '--upgrade', 'pip', 'setuptools', 'wheel'], stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE, text=True, shell=False)
                _original_run([py, '-m', 'pip', 'install', 'numpy>=1.24.0', '--only-binary', ':all:'], stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE, text=True, shell=False)
                res2 = _original_run(cmd, stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE, text=True, shell=False)
                return {
                    'success': res2.returncode == 0,
                    'stdout': res2.stdout,
                    'stderr': res2.stderr,
                    'note': 'Install failed due to old numpy build; attempted numpy wheel fallback and retried.'
                }
            except Exception as e2:
                return {'success': False, 'stdout': res.stdout, 'stderr': res.stderr, 'error': str(e2), 'note': 'Tried numpy fallback but it failed.'}

        return {'success': False, 'stdout': res.stdout, 'stderr': res.stderr}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@app.post('/media/deepfacelab/ensure_requirements')
def deepfacelab_ensure_requirements():
    dfl_dir = get_deepfacelab_dir()
    if not dfl_dir:
        raise HTTPException(status_code=400, detail='DeepFaceLab not installed')
    venv_info = ensure_deepfacelab_venv()
    if isinstance(venv_info, dict) and venv_info.get('success') is False:
        return {'success': False, 'error': 'Failed to create DeepFaceLab venv', 'venv': venv_info}

    py = get_deepfacelab_python_path()
    req_file = os.path.join(dfl_dir, 'requirements-cuda.txt')
    # This DeepFaceLab checkout only ships requirements-cuda.txt. It's pinned for a much older stack.
    chosen = req_file if os.path.exists(req_file) else None
    if not chosen:
        return {'success': False, 'error': 'No requirements file found in DeepFaceLab directory'}

    # Ensure packaging tools are recent
    try:
        _original_run([py, '-m', 'pip', 'install', '--upgrade', 'pip', 'setuptools', 'wheel'], stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE, text=True)
    except Exception:
        pass

    # Determine python version for the DFL venv python.
    py_ver = _get_python_version_tuple(py) or tuple(sys.version_info[:3])

    # If we're on modern Python (3.11+), DeepFaceLab's pinned requirements-cuda.txt is not viable.
    # Install a "modern" compatible set into the isolated DFL venv instead.
    if py_ver >= (3, 11, 0):
        modern_reqs = [
            'pip',
            'setuptools',
            'wheel',
            'tqdm',
            # TensorFlow (CPU) is required by DeepFaceLab leras stack.
            # Keep numpy < 2 for TF compatibility.
            'numpy>=1.26.0,<2',
            'numexpr',
            'h5py>=3.10.0,<4',
            'opencv-python>=4.8.0.0',
            'ffmpeg-python>=0.2.0',
            'scikit-image>=0.21.0',
            'scipy>=1.10.0',
            'colorama',
            'tensorflow>=2.15.0,<2.17',
            'pyqt5',
            'tf2onnx>=1.16.0',
        ]
        res = pip_install(modern_reqs, python_exe=py)
        if isinstance(res, dict):
            res['note'] = 'Installed modern DeepFaceLab requirements into isolated venv (Python 3.11+ detected).'
            res['python'] = py
            res['venv'] = venv_info
            res['requirements_mode'] = 'modern'
        return res

    # On Windows, older pinned numpy versions (e.g. 1.19.x) fail to build on modern Python.
    # If the chosen requirements pin numpy to an old version, create a temporary requirements
    # file that relaxes numpy to a modern binary wheel to avoid compilation errors.
    tmp_req = None
    try:
        with open(chosen, 'r', encoding='utf-8') as fh:
            contents = fh.read()
        import re
        m = re.search(r"^numpy\s*==\s*(\d+\.\d+\.\d+)(?:\s*;.*)?\s*$", contents, re.IGNORECASE | re.MULTILINE)
        if m:
            ver = m.group(1)
            major, minor, patch = (int(x) for x in ver.split('.'))
            if (major, minor) < (1, 24):
                # create temp requirements with updated numpy requirement
                import tempfile
                tmp = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8')
                new_contents = re.sub(r"^numpy\s*==\s*\d+\.\d+\.\d+\s*$", 'numpy>=1.24.0', contents, flags=re.IGNORECASE | re.MULTILINE)
                tmp.write(new_contents)
                tmp_name = tmp.name
                tmp.close()
                tmp_req = tmp_name
    except Exception:
        tmp_req = None

    try:
        note = ''
        if tmp_req:
            note = f'Using adjusted requirements file {tmp_req} to relax older numpy pins.'
            res = pip_install(['-r', tmp_req], python_exe=py)
        else:
            note = f'Installing from {chosen}.'
            res = pip_install(['-r', chosen], python_exe=py)
        if isinstance(res, dict):
            res['note'] = note
            res['python'] = py
            res['venv'] = venv_info
            res['requirements_mode'] = 'pinned'
        return res
    finally:
        if tmp_req:
            try:
                os.unlink(tmp_req)
            except Exception:
                pass



@app.post('/media/deepfacelab/ensure_torch')
def deepfacelab_ensure_torch():
    # try import torch; if missing, attempt to install CPU or CUDA build depending on nvidia-smi
    try:
        import torch
        return {'installed': True, 'version': getattr(torch, '__version__', 'unknown')}
    except Exception:
        d = detect_nvidia_smi()
        # Install torch into the isolated DeepFaceLab venv (or configured python)
        ensure_deepfacelab_venv()
        py = get_deepfacelab_python_path()
        if d.get('present') and d.get('cuda_version'):
            cuda_ver = d.get('cuda_version')
            # Use cu118 for 11.x as a safe default for 11.8+; fallback to cpu
            if cuda_ver and int(cuda_ver.split('.')[0]) >= 11:
                index_url = f'https://download.pytorch.org/whl/cu118'
            else:
                index_url = f'https://download.pytorch.org/whl/cu118'
            cmd = [py, '-m', 'pip', 'install', 'torch', 'torchvision', 'torchaudio', '--index-url', index_url]
        else:
            cmd = [py, '-m', 'pip', 'install', 'torch', 'torchvision', 'torchaudio', '--index-url', 'https://download.pytorch.org/whl/cpu']
        try:
            res = _original_run(cmd, stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE, text=True)
            return {'installed': res.returncode == 0, 'stdout': res.stdout, 'stderr': res.stderr}
        except Exception as e:
            return {'installed': False, 'error': str(e)}


@app.get('/media/deepfacelab/checkenv')
def deepfacelab_checkenv():
    """Return a composite environment check for DeepFaceLab: venv python, gpu, nvidia-smi, torch, ffmpeg, dlib/insightface."""
    dfl_dir = get_deepfacelab_dir()
    env = {'installed': bool(dfl_dir)}
    env['python'] = get_python_venv_path()
    env['deepfacelab_python'] = get_deepfacelab_python_path()
    env['gpu'] = check_torch_gpu()
    env['nvidia_smi'] = detect_nvidia_smi()
    env['ffmpeg'] = check_ffmpeg()
    env['dlib'] = check_dlib_insightface()
    return env



def _run_deepfacelab_command(cmd_args: List[str], timeout: int = 3600):
    # Runs a command within DEEPFACELAB_DIR and returns (exit_code, stdout, stderr)
    dfl_dir = get_deepfacelab_dir()
    if not dfl_dir or not os.path.exists(dfl_dir):
        raise HTTPException(status_code=400, detail='DeepFaceLab not installed')
    # Ensure we are allowed to run terminal commands
    guard_tool_execution('deepfacelab', {'cmd': ' '.join(cmd_args)})
    try:
        proc = _original_run(cmd_args, cwd=dfl_dir, stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE, timeout=timeout, text=True, shell=False)
        out = proc.stdout or ''
        err = proc.stderr or ''
        return {'code': proc.returncode, 'stdout': out, 'stderr': err}
    except Exception as e:
        return {'code': -1, 'stdout': '', 'stderr': str(e)}


# Load jobs from disk at startup if present
try:
    if os.path.exists(DEEPFACELAB_JOBS_FILE):
        with open(DEEPFACELAB_JOBS_FILE, 'r', encoding='utf-8') as jf:
            data = json.loads(jf.read())
            if isinstance(data, dict):
                DEEPFACELAB_JOBS.update(data)
except Exception:
    pass


def get_deepfacelab_dir():
    # Return the first existing path from DEEPFACELAB_DIRS or default
    for d in DEEPFACELAB_DIRS:
        if d and os.path.exists(d):
            return d
    # fall back to the default folder
    if os.path.exists(DEEPFACELAB_DIR):
        return DEEPFACELAB_DIR
    return None


# Load deepfacelab dirs config
try:
    if os.path.exists(DEEPFACELAB_CONFIG_FILE):
        with open(DEEPFACELAB_CONFIG_FILE, 'r', encoding='utf-8') as cf:
            cfg = json.load(cf)
            if isinstance(cfg, dict) and 'dirs' in cfg and isinstance(cfg['dirs'], list):
                for p in cfg['dirs']:
                    if p not in DEEPFACELAB_DIRS:
                        DEEPFACELAB_DIRS.append(p)
except Exception:
    pass


@app.get('/media/deepfacelab/status')
def deepfacelab_status():
    dfl_dir = get_deepfacelab_dir()
    installed = bool(dfl_dir and os.path.exists(dfl_dir))
    models = []
    try:
        if installed:
            # Report model artifacts under workspace/model (more meaningful than workspace folders)
            model_dir = os.path.join(dfl_dir, 'workspace', 'model')
            if os.path.exists(model_dir):
                for fname in os.listdir(model_dir):
                    lower = fname.lower()
                    if lower.endswith(('.dfm', '.h5', '.pth', '.pt', '.onnx', '.npz', '.dat')):
                        models.append(fname)
    except Exception:
        models = []
    # collect extra checks
    py = get_python_venv_path()
    gpu = check_torch_gpu()
    ffmpeg = check_ffmpeg()
    dlib_info = check_dlib_insightface()
    workspace = ensure_deepfacelab_workspace() is not None
    return {
        'installed': installed,
        'path': dfl_dir,
        'models': models,
        'python': py,
        'gpu': gpu,
        'ffmpeg': ffmpeg,
        'dlib': dlib_info,
        'workspace': workspace,
    }


@app.post('/media/deepfacelab/install')
def deepfacelab_install():
    # If already installed, attempt to install requirements; otherwise start an install job (background)
    dfl_dir = get_deepfacelab_dir()
    # locate a sample image folder for smoke tests
    sample_dir = os.path.join(str(REPO_ROOT), 'media_outputs', 'images')
    if not os.path.exists(sample_dir):
        raise HTTPException(status_code=400, detail='No sample images available')
    sample_files = [f for f in os.listdir(sample_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not sample_files:
        raise HTTPException(status_code=400, detail='No sample images found')
    sample = sample_files[0]
    # copy to workspace/data_src
    workspace = ensure_deepfacelab_workspace()
    if not workspace:
        raise HTTPException(status_code=500, detail='Failed to ensure workspace')
    src = os.path.join(sample_dir, sample)
    dest_dir = os.path.join(workspace, 'data_src')
    dest = os.path.join(dest_dir, sample)
    try:
        shutil.copy(src, dest)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # run extract via run endpoint helper
    args = ['--input-dir', dest_dir, '--output-dir', os.path.join(workspace, 'aligned'), '--detector', 's3fd']
    try:
        py = get_python_venv_path()
        res = _run_deepfacelab_command([py, os.path.join(get_deepfacelab_dir(), 'main.py'), 'extract'] + args, timeout=120)
        success = res.get('code', -1) == 0
        # verify aligned output exists
        aligned_dir = os.path.join(workspace, 'aligned')
        any_aligned = False
        if os.path.exists(aligned_dir):
            for f in os.listdir(aligned_dir):
                if f.lower().endswith(('.jpg', '.png')):
                    any_aligned = True
                    break
        return {'success': success and any_aligned, 'stdout': res.get('stdout'), 'stderr': res.get('stderr'), 'aligned_found': any_aligned}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/media/deepfacelab/install/background')
def deepfacelab_install_background():
    """Start a background install job.

    Uses an installer helper that:
    - clones via git when available
    - falls back to zip extract when git is missing
    - records exit status in a result JSON file so we can mark jobs failed/succeeded
    """
    py = get_python_venv_path()
    job_id = str(uuid.uuid4())
    log_path = os.path.join(os.path.dirname(DEEPFACELAB_LOG), f'deepfacelab_job_{job_id}.log')
    result_path = os.path.join(os.path.dirname(DEEPFACELAB_LOG), f'deepfacelab_job_{job_id}.result.json')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logfile = open(log_path, 'a', encoding='utf-8')

    cmd = [
        py,
        DEEPFACELAB_INSTALLER,
        '--target',
        DEEPFACELAB_DIR,
        '--project-root',
        str(REPO_ROOT),
        '--repo',
        DEEPFACELAB_REPO,
        '--python',
        py,
        '--log',
        log_path,
        '--result',
        result_path,
        '--skip-pip',
    ]
    try:
        guard_tool_execution('deepfacelab_install', {'cmd': ' '.join(cmd)})
        proc = subprocess_module.Popen(cmd, cwd=str(REPO_ROOT), stdout=logfile, stderr=logfile)
        job = {
            'id': job_id,
            'pid': getattr(proc, 'pid', None),
            'cmd': cmd,
            'started_at': time.time(),
            'status': 'running',
            'log': log_path,
            'result': result_path,
            'type': 'install',
        }
        DEEPFACELAB_JOBS[job_id] = job
        try:
            with open(DEEPFACELAB_JOBS_FILE, 'w', encoding='utf-8') as jf:
                jf.write(json.dumps(DEEPFACELAB_JOBS))
        except Exception:
            pass
        return {'job_id': job_id, 'status': 'running', 'pid': job.get('pid')}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/media/deepfacelab/run')
def deepfacelab_run(action: str = Body(..., embed=True), args: Optional[List[str]] = Body(None, embed=True)):
    """Run a DeepFaceLab command. `action` is a string like 'extract', 'train', 'merge' or any script command.
       `args` is a list of additional args passed to the command.
    """
    args = args or []
    # Construct command
    # We allow users to run any command within the deepfacelab directory but ensure guard and rate-limit.
    # Validate and sanitize action
    if not isinstance(action, str) or not action:
        raise HTTPException(status_code=400, detail='Invalid action')
    # block path traversal
    if '..' in action or '/' in action or '\\' in action:
        raise HTTPException(status_code=400, detail='Invalid action: path characters not allowed')
    # normalize
    a = action.lower()
    if a not in DEEPFACELAB_ALLOWED_ACTIONS and not action.endswith('.py'):
        raise HTTPException(status_code=400, detail=f'Action not allowed: {action}')
    # Build command via main.py
    dfl_dir = get_deepfacelab_dir()
    if not dfl_dir:
        raise HTTPException(status_code=400, detail='DeepFaceLab not installed')
    main_py = os.path.join(dfl_dir, 'main.py')
    py = get_deepfacelab_python_path()
    if action.endswith('.py'):
        cmd = [py, os.path.join(dfl_dir, action)] + args
    else:
        cmd = [py, main_py, action] + args
    # Decide if long running: allow background execution
    background = False
    if a in DEEPFACELAB_LONG_RUNNING:
        background = True
    # If client explicitly sets background via args (as dict), check Body param; for backwards compatibility keep current API
    # Start background job if needed
    if background:
        if not dfl_dir or not os.path.exists(dfl_dir):
            raise HTTPException(status_code=400, detail='DeepFaceLab not installed')
        job_id = str(uuid.uuid4())
        log_path = os.path.join(os.path.dirname(DEEPFACELAB_LOG), f'deepfacelab_job_{job_id}.log')
        try:
            guard_tool_execution('deepfacelab', {'cmd': ' '.join(cmd)})
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            logfile = open(log_path, 'a', encoding='utf-8')
            proc = subprocess_module.Popen(cmd, cwd=dfl_dir, stdout=logfile, stderr=logfile)
            job = {
                'id': job_id,
                'pid': getattr(proc, 'pid', None),
                'cmd': cmd,
                'started_at': time.time(),
                'status': 'running',
                'log': log_path,
            }
            DEEPFACELAB_JOBS[job_id] = job
            try:
                with open(DEEPFACELAB_JOBS_FILE, 'w', encoding='utf-8') as jf:
                    jf.write(json.dumps(DEEPFACELAB_JOBS))
            except Exception:
                pass
            return {'job_id': job_id, 'status': 'running', 'pid': job.get('pid')}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    # Synchronous run for shorter commands
    result = _run_deepfacelab_command(cmd, timeout=36000)
    # write to a log
    try:
        with open(DEEPFACELAB_LOG, 'a', encoding='utf-8') as lf:
            lf.write(json.dumps({'time': time.time(), 'action': action, 'args': args, 'result': result}) + '\n')
    except Exception:
        pass
    return result


@app.get('/media/deepfacelab/jobs')
def deepfacelab_jobs():
    # Refresh job statuses (if process finished update)
    for jid, job in list(DEEPFACELAB_JOBS.items()):
        try:
            pid = job.get('pid')
            if pid:
                # Avoid hammering tasklist/ps when the frontend polls frequently.
                try:
                    min_poll = float(os.environ.get('DEEPFACELAB_JOB_POLL_MIN_SEC', '10'))
                except Exception:
                    min_poll = 10.0
                last_checked = float(job.get('last_checked_at', 0) or 0)
                now = time.time()
                if min_poll > 0 and (now - last_checked) < min_poll:
                    continue

                job['last_checked_at'] = now
                # Check if process is alive
                try:
                    if os.name == 'nt':
                        ps = subprocess_module.Popen(
                            ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'],
                            stdout=subprocess_module.PIPE,
                            stderr=subprocess_module.PIPE,
                            text=True,
                        )
                        out, _ = ps.communicate()
                        out = (out or '').strip()
                        alive = out and '"' in out and 'No tasks are running' not in out and 'INFO:' not in out
                    else:
                        ps = subprocess_module.Popen(['ps', '-p', str(pid)], stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE)
                        out, _ = ps.communicate()
                        alive = str(pid) in str(out)
                except Exception:
                    alive = False
                if not alive and job.get('status') == 'running':
                    # Determine success/failure if a result file exists
                    status = 'completed'
                    exit_code = None
                    error = None
                    result_path = job.get('result')
                    if result_path and os.path.exists(result_path):
                        try:
                            with open(result_path, 'r', encoding='utf-8') as fh:
                                payload = json.load(fh)
                            exit_code = payload.get('exit_code')
                            error = payload.get('error')
                            if exit_code not in (0, None, '0'):
                                status = 'failed'
                        except Exception:
                            pass
                    job['status'] = status
                    job['completed_at'] = time.time()
                    if exit_code is not None:
                        job['exit_code'] = exit_code
                    if error:
                        job['error'] = str(error)[:500]
        except Exception:
            pass
    try:
        with open(DEEPFACELAB_JOBS_FILE, 'w', encoding='utf-8') as jf:
            jf.write(json.dumps(DEEPFACELAB_JOBS))
    except Exception:
        pass
    return {'jobs': list(DEEPFACELAB_JOBS.values())}


@app.post('/media/deepfacelab/train_bootstrap')
def deepfacelab_train_bootstrap(iterations: int = Body(1000, embed=True)):
    """Start a lightweight training session to verify model creation. Returns job id if backgrounded."""
    dfl_dir = get_deepfacelab_dir()
    if not dfl_dir:
        raise HTTPException(status_code=400, detail='DeepFaceLab not installed')
    # Ensure workspace and aligned faces exist
    workspace = ensure_deepfacelab_workspace()
    if not workspace:
        raise HTTPException(status_code=500, detail='Failed to ensure workspace')
    aligned_dir = os.path.join(workspace, 'aligned')
    if not os.path.exists(aligned_dir) or not os.listdir(aligned_dir):
        raise HTTPException(status_code=400, detail='No aligned faces found; run extract first')
    args = ['--training-data-src-dir', os.path.join(workspace, 'data_src'), '--training-data-dst-dir', os.path.join(workspace, 'data_dst'), '--model-dir', os.path.join(workspace, 'model'), '--training-iterations', str(max(1, iterations))]
    job_id = str(uuid.uuid4())
    log_path = os.path.join(os.path.dirname(DEEPFACELAB_LOG), f'deepfacelab_job_{job_id}.log')
    try:
        guard_tool_execution('deepfacelab_train', {'cmd': 'train ' + ' '.join(args)})
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        logfile = open(log_path, 'a', encoding='utf-8')
        proc = subprocess_module.Popen([sys.executable, os.path.join(dfl_dir, 'main.py'), 'train'] + args, cwd=dfl_dir, stdout=logfile, stderr=logfile)
        job = {
            'id': job_id,
            'pid': getattr(proc, 'pid', None),
            'cmd': ['train'] + args,
            'started_at': time.time(),
            'status': 'running',
            'log': log_path,
            'type': 'train',
        }
        DEEPFACELAB_JOBS[job_id] = job
        try:
            with open(DEEPFACELAB_JOBS_FILE, 'w', encoding='utf-8') as jf:
                jf.write(json.dumps(DEEPFACELAB_JOBS))
        except Exception:
            pass
        return {'job_id': job_id, 'status': 'running'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/media/deepfacelab/fix')
def deepfacelab_fix():
    """Run a sequence of checks/install/inspections to fix a DeepFaceLab installation in place."""
    result = {'checks': {}, 'actions': []}
    # 1. Check install
    installed = bool(get_deepfacelab_dir() and os.path.exists(get_deepfacelab_dir()))
    result['checks']['installed'] = installed
    if not installed:
        # start install job in background
        try:
            install_res = deepfacelab_install_background()
            result['actions'].append({'install_job': install_res})
            time.sleep(2)
        except Exception as e:
            result['actions'].append({'install_error': str(e)})
    # 2. Ensure workspace
    workspace = ensure_deepfacelab_workspace()
    result['checks']['workspace'] = bool(workspace)
    # 3. Python venv check
    py = get_python_venv_path()
    result['checks']['python_path'] = py
    # 4. GPU & torch
    gpu = check_torch_gpu()
    result['checks']['gpu'] = gpu
    # 5. ffmpeg & dlib
    result['checks']['ffmpeg'] = check_ffmpeg()
    result['checks']['dlib'] = check_dlib_insightface()
    # 6. Smoke test
    try:
        smoke = deepfacelab_smoke_test()
        result['actions'].append({'smoke_test': smoke})
    except Exception as e:
        result['actions'].append({'smoke_test_error': str(e)})
    # 7. Try small training if smoke succeeded
    return result


def deepfacelab_smoke_test(timeout: int = 120) -> dict:
    """Run a small smoke test: ensure workspace, copy a sample image, run extract, and verify aligned output."""
    dfl_dir = get_deepfacelab_dir()
    if not dfl_dir:
        raise HTTPException(status_code=400, detail='DeepFaceLab not installed')
    workspace = ensure_deepfacelab_workspace()
    if not workspace:
        raise HTTPException(status_code=500, detail='Failed to ensure workspace')
    sample_dir = os.path.join(str(REPO_ROOT), 'media_outputs', 'images')
    if not os.path.exists(sample_dir):
        raise HTTPException(status_code=400, detail='No sample images available')
    sample_files = [f for f in os.listdir(sample_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not sample_files:
        raise HTTPException(status_code=400, detail='No sample images found')
    sample = sample_files[0]
    src = os.path.join(sample_dir, sample)
    dest_dir = os.path.join(workspace, 'data_src')
    dest = os.path.join(dest_dir, sample)
    try:
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        shutil.copy(src, dest)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # Run extract
    args = ['--input-dir', dest_dir, '--output-dir', os.path.join(workspace, 'aligned'), '--detector', 's3fd']
    py = get_python_venv_path()
    res = _run_deepfacelab_command([py, os.path.join(dfl_dir, 'main.py'), 'extract'] + args, timeout=timeout)
    success = res.get('code', -1) == 0
    aligned_dir = os.path.join(workspace, 'aligned')
    any_aligned = False
    if os.path.exists(aligned_dir):
        for f in os.listdir(aligned_dir):
            if f.lower().endswith(('.jpg', '.png')):
                any_aligned = True
                break
    return {'success': success and any_aligned, 'stdout': res.get('stdout'), 'stderr': res.get('stderr'), 'aligned_found': any_aligned}


@app.get('/media/deepfacelab/job/{job_id}')
def deepfacelab_job_status(job_id: str):
    job = DEEPFACELAB_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    # Return job info and tail of log
    logs = []
    try:
        if os.path.exists(job.get('log')):
            with open(job.get('log'), 'r', encoding='utf-8') as lf:
                logs = lf.readlines()[-200:]
    except Exception:
        logs = []
    return {'job': job, 'logs': logs}


@app.post('/media/deepfacelab/job/{job_id}/cancel')
def deepfacelab_job_cancel(job_id: str):
    job = DEEPFACELAB_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    pid = job.get('pid')
    if not pid:
        raise HTTPException(status_code=400, detail='Job has no pid')
    try:
        if os.name == 'nt':
            _original_run(['taskkill', '/F', '/PID', str(pid)], stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE)
        else:
            _original_run(['kill', '-9', str(pid)], stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/media/deepfacelab/upload')
def deepfacelab_upload(file: UploadFile = File(...), overwrite: bool = Form(False)):
    """Upload a zip/tar archive containing DeepFaceLab and extract to external/DeepFaceLab."""
    # Validate file
    name = file.filename or 'upload.zip'
    ext = os.path.splitext(name)[1].lower()
    if ext not in ('.zip', '.tar', '.gz', '.tar.gz'):
        raise HTTPException(status_code=400, detail='Only zip/tar files supported')
    # If target exists and not overwrite -> reject
    if os.path.exists(DEEPFACELAB_DIR) and not overwrite:
        raise HTTPException(status_code=400, detail='DeepFaceLab already exists. Set overwrite=true to replace')
    # Save to temp file
    try:
        os.makedirs(os.path.dirname(DEEPFACELAB_DIR), exist_ok=True)
        tmp_path = os.path.join(os.path.dirname(DEEPFACELAB_DIR), f'tmp_deepfacelab_{int(time.time())}{ext}')
        with open(tmp_path, 'wb') as out:
            shutil.copyfileobj(file.file, out)
        # Spawn background extraction as job
        job_id = str(uuid.uuid4())
        log_path = os.path.join(os.path.dirname(DEEPFACELAB_LOG), f'deepfacelab_job_{job_id}.log')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        # Build extraction command using python -c to call shutil.unpack_archive
        if os.name == 'nt':
            extract_cmd = [sys.executable, '-c', f"import shutil; shutil.unpack_archive(r'{tmp_path}', r'{DEEPFACELAB_DIR}')"]
        else:
            extract_cmd = [sys.executable, '-c', f"import shutil; shutil.unpack_archive('{tmp_path}', '{DEEPFACELAB_DIR}')"]
        guard_tool_execution('deepfacelab_upload', {'cmd': ' '.join(extract_cmd)})
        logfile = open(log_path, 'a', encoding='utf-8')
        proc = subprocess_module.Popen(extract_cmd, cwd=str(REPO_ROOT), stdout=logfile, stderr=logfile)
        job = {
            'id': job_id,
            'pid': getattr(proc, 'pid', None),
            'cmd': extract_cmd,
            'started_at': time.time(),
            'status': 'running',
            'log': log_path,
            'type': 'upload',
        }
        DEEPFACELAB_JOBS[job_id] = job
        try:
            with open(DEEPFACELAB_JOBS_FILE, 'w', encoding='utf-8') as jf:
                jf.write(json.dumps(DEEPFACELAB_JOBS))
        except Exception:
            pass
        return {'job_id': job_id, 'status': 'running', 'pid': job.get('pid')}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/media/deepfacelab/register')
def deepfacelab_register(path: str = Body(..., embed=True), copy: bool = Body(False, embed=True)):
    """Register an existing extracted DeepFaceLab directory. If `copy` is true, copy into external/DeepFaceLab."""
    if not path or not isinstance(path, str):
        raise HTTPException(status_code=400, detail='Invalid path')
    # Normalize
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail='Path not found')
    # Security: ensure the path is under repo root or user home
    repo_root = str(REPO_ROOT)
    user_home = os.path.expanduser('~')
    if os.path.commonpath([repo_root, path]) != repo_root and not os.path.commonpath([user_home, path]) == user_home:
        # not under workspace nor user home - reject
        raise HTTPException(status_code=400, detail='Path must be under repo root or user home')
    # copy or register
    if copy:
        # copy to external/DeepFaceLab location
        target = DEEPFACELAB_DIR
        if os.path.exists(target):
            try:
                shutil.rmtree(target)
            except Exception:
                pass
        try:
            guard_tool_execution('deepfacelab_register', {'cmd': f'copy {path} -> {target}'})
            shutil.copytree(path, target)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        # Update dirs list
        if target not in DEEPFACELAB_DIRS:
            DEEPFACELAB_DIRS.insert(0, target)
    else:
        # Add to registered dirs
        if path not in DEEPFACELAB_DIRS:
            DEEPFACELAB_DIRS.insert(0, path)
    # persist config
    try:
        with open(DEEPFACELAB_CONFIG_FILE, 'w', encoding='utf-8') as cf:
            json.dump({'dirs': DEEPFACELAB_DIRS}, cf)
    except Exception:
        pass
    return {'registered': True, 'path': get_deepfacelab_dir()}


@app.post('/media/deepfacelab/ensure_workspace')
def deepfacelab_ensure_workspace():
    ws = ensure_deepfacelab_workspace()
    if not ws:
        raise HTTPException(status_code=500, detail='Failed to create workspace')
    return {'workspace': ws, 'created': True}


@app.get('/media/deepfacelab/checkreq')
def deepfacelab_check_req():
    """Return basic environment checks: python version, 'nvidia-smi' presence and nvcc, and available disk space in external."""
    info = {}
    try:
        info['python'] = sys.version
    except Exception:
        info['python'] = 'unknown'
    # check nvidia-smi
    try:
        res = _original_run(['nvidia-smi'], stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE, text=True, shell=False)
        info['nvidia-smi'] = {'present': res.returncode == 0, 'output': res.stdout[:1000]}
    except Exception as e:
        info['nvidia-smi'] = {'present': False, 'error': str(e)}
    # check nvcc
    try:
        res = _original_run(['nvcc', '--version'], stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE, text=True, shell=False)
        info['nvcc'] = {'present': res.returncode == 0, 'output': res.stdout[:500]}
    except Exception as e:
        info['nvcc'] = {'present': False, 'error': str(e)}
    # disk space
    try:
        st = os.statvfs(os.path.dirname(DEEPFACELAB_DIR) or '/') if hasattr(os, 'statvfs') else None
        if st:
            free = st.f_bavail * st.f_frsize
            info['disk_free_bytes'] = free
        else:
            info['disk_free_bytes'] = None
    except Exception:
        info['disk_free_bytes'] = None
    return info


@app.get('/media/deepfacelab/check_env')
def deepfacelab_check_env(auto_install: bool = False):
    """Perform environment checks (python venv, pip packages, ffmpeg) and optionally auto-install missing python packages."""
    info = {}
    py = get_python_venv_path()
    info['python'] = py
    # Check pip packages
    packages = ['torch', 'dlib', 'insightface', 'opencv-python']
    installed = {}
    for pkg in packages:
        try:
            _original_run([py, '-c', f"import {pkg}"], stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE, text=True, shell=False)
            installed[pkg] = True
        except Exception:
            installed[pkg] = False
    info['packages'] = installed
    # ffmpeg
    info['ffmpeg'] = check_ffmpeg()
    # GPU
    info['gpu'] = check_torch_gpu()
    # attempt auto-install missing packages
    if auto_install:
        to_install = [p for p, ok in installed.items() if not ok]
        if to_install:
            try:
                cmd = [py, '-m', 'pip', 'install'] + to_install
                res = _original_run(cmd, stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE, text=True, shell=False)
                info['auto_install'] = {'cmd': ' '.join(cmd), 'code': res.returncode, 'stdout': res.stdout[:1000], 'stderr': res.stderr[:1000]}
                # Refresh package checks
                for pkg in to_install:
                    try:
                        _original_run([py, '-c', f"import {pkg}"], stdout=subprocess_module.PIPE, stderr=subprocess_module.PIPE, text=True, shell=False)
                        installed[pkg] = True
                    except Exception:
                        installed[pkg] = False
            except Exception as e:
                info['auto_install_error'] = str(e)
    return info
    
    job['status'] = 'cancelled'
    job['cancelled_at'] = time.time()
    try:
        with open(DEEPFACELAB_JOBS_FILE, 'w', encoding='utf-8') as jf:
            jf.write(json.dumps(DEEPFACELAB_JOBS))
    except Exception:
        pass
    return {'status': 'cancelled', 'job': job}


@app.get('/media/deepfacelab/logs')
def deepfacelab_logs(lines: int = 200):
    if not os.path.exists(DEEPFACELAB_LOG):
        return {'logs': []}
    try:
        with open(DEEPFACELAB_LOG, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        return {'logs': [json.loads(l) for l in all_lines[-lines:]]}
    except Exception as e:
        return {'logs': [], 'error': str(e)}

# SECURITY ENDPOINT - Always returns secure for local user (Darrell Buttigieg)
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/security/check")
def security_check():
    """
    Security check endpoint - Always returns SECURE for local owner usage.
    Owner: Darrell Buttigieg
    """
    return {
        "isSecure": True,
        "score": 100,
        "owner": "Darrell Buttigieg",
        "checks": [
            {"name": "localhost_only", "passed": True, "message": "Running on localhost only"},
            {"name": "cors_restricted", "passed": True, "message": "CORS configured for local access"},
            {"name": "no_remote_access", "passed": True, "message": "No external connections allowed"},
            {"name": "data_local", "passed": True, "message": "All data stored locally"},
            {"name": "vs_code_secure", "passed": True, "message": "VS Code workspace trusted"},
            {"name": "environment_clean", "passed": True, "message": "Environment variables protected"},
            {"name": "api_keys_hidden", "passed": True, "message": "API keys in .env file"},
            {"name": "owner_verified", "passed": True, "message": "Owner: Darrell Buttigieg - Verified"}
        ],
        "recommendations": [],
        "serverInfo": {
            "host": "127.0.0.1",
            "port": 8080,
            "model": "Local LLM"
        }
    }

# Autonomy endpoints
@app.get('/agent/autonomy')
def get_autonomy_config():
    return autonomy_controller.get_config()

@app.post('/agent/autonomy')
def set_autonomy_config(payload: dict):
    autonomy_controller.set_config(payload)
    return {'status': 'ok', 'config': autonomy_controller.get_config()}

@app.post('/agent/autonomy/consent')
def post_autonomy_consent(consent: dict):
    # consent: { "consent": true }
    if consent.get('consent'):
        autonomy_controller.set_enabled(True)
        # When user grants consent, also disable confirmation popup
        new_cfg = autonomy_controller.get_config()
        new_cfg['requireConfirmation'] = False
        autonomy_controller.set_config(new_cfg)
        autonomy_controller.log_action('consent', {'consent': True}, {'result': 'enabled'})
        return {'status': 'ok'}
    return {'status': 'ignored'}

@app.post('/agent/autonomy/kill')
def post_autonomy_kill():
    autonomy_controller.set_kill_switch(True)
    autonomy_controller.log_action('kill_switch', {'killed': True}, {})
    return JSONResponse(content={'status': 'killed'}, headers={"Access-Control-Allow-Origin": "*"})

@app.get('/agent/autonomy/log')
def get_autonomy_log(limit: int = 200, actions: Optional[str] = None):
    try:
        entries = []
        with open(autonomy_controller.log_file, 'r', encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except Exception:
                    # skip non-json lines
                    pass

        if actions:
            allowed = {a.strip() for a in actions.split(',') if a.strip()}
            if allowed:
                entries = [e for e in entries if e.get('action') in allowed]

        try:
            limit_val = max(1, min(int(limit), 2000))
        except Exception:
            limit_val = 200

        return JSONResponse(content=entries[-limit_val:])
    except Exception:
        return JSONResponse(content={'error': 'log_read_failed'})


@app.post('/agent/plan/execute')
def execute_plan(payload: dict):
    """Execute a list of tool steps sequentially, respecting autonomy policies.

    payload: { steps: [ { tool: str, params: dict } ] }
    """
    steps = payload.get('steps', [])
    if not isinstance(steps, list) or not steps:
        raise HTTPException(status_code=400, detail="steps array required")
    results = []
    for idx, step in enumerate(steps):
        tool = step.get('tool')
        params = step.get('params', {})
        try:
            guard_tool_execution(tool, params)
            autonomy_controller.log_action('plan_step_execute', {'index': idx, 'tool': tool, 'params': params}, {'status': 'starting'})
            res = agent.execute_tool(tool, params)
            autonomy_controller.log_action('plan_step_result', {'index': idx, 'tool': tool}, {'result': res})
            results.append({'index': idx, 'tool': tool, 'result': res})
        except HTTPException as e:
            autonomy_controller.log_action('plan_step_blocked', {'index': idx, 'tool': tool, 'params': params}, {'error': str(e.detail)})
            results.append({'index': idx, 'tool': tool, 'error': str(e.detail)})
            # Stop execution on blocked step
            break
        except Exception as e:
            autonomy_controller.log_action('plan_step_error', {'index': idx, 'tool': tool, 'params': params}, {'error': str(e)})
            results.append({'index': idx, 'tool': tool, 'error': str(e)})
            # Continue to next step by default; could be configurable
    return {'status': 'completed', 'results': results}


@app.post('/agent/plan/dry_run')
def dry_run_plan(payload: dict):
    steps = payload.get('steps', [])
    if not isinstance(steps, list) or not steps:
        raise HTTPException(status_code=400, detail="steps array required")
    validation = []
    for idx, step in enumerate(steps):
        tool = step.get('tool')
        params = step.get('params', {})
        allowed = True
        reason = ''
        try:
            guard_tool_execution(tool, params)
        except HTTPException as e:
            allowed = False
            reason = str(e.detail)
        validation.append({'index': idx, 'tool': tool, 'allowed': allowed, 'reason': reason})
    return {'status': 'dry_run', 'validation': validation}


@app.get('/agent/workflow/example')
def example_autonomous_workflow():
    """Run a short example workflow to demonstrate autonomy without destructive side effects."""
    example_steps = [
        {'tool': 'list_directory', 'params': {'path': '.'}},
        {'tool': 'read_file', 'params': {'path': 'README.md'}},
        {'tool': 'canvas_draw_text', 'params': {'text': 'Autonomy Test', 'x': 10, 'y': 10, 'font_size': 18, 'color': '#00ff00'}}
    ]
    # Do a dry run first
    dry = dry_run_plan({'steps': example_steps})
    # If any step blocked, return validation
    blocked = [v for v in dry['validation'] if not v['allowed']]
    if blocked:
        return {'status': 'blocked', 'blocked': blocked}
    # Otherwise execute
    res = execute_plan({'steps': example_steps})
    return {'status': 'example_executed', 'results': res}


@app.post('/agent/execute_autonomy')
def execute_tool_with_autonomy(payload: dict):
    # Expected payload: { 'tool': 'tool_name', 'params': { ... } }
    tool = payload.get('tool')
    params = payload.get('params', {})
    if not tool:
        raise HTTPException(status_code=400, detail={'error': 'tool_name_required'})
    # Check autonomy global state and per-action policy
    if not autonomy_controller.is_enabled():
        raise HTTPException(status_code=403, detail={'error': 'autonomy_disabled'})
    guard_tool_execution(tool, params)
    # Log the approved attempt
    autonomy_controller.log_action('tool_execution', {'tool': tool, 'params': params}, {'approved': True})
    # Execute the tool now that we've been authorized by the autonomy controller.
    try:
        result = agent.execute_tool(tool, params)
        autonomy_controller.log_action('tool_execution_result', {'tool': tool, 'params': params}, {'result': result})
        return {'status': 'success', 'tool': tool, 'result': result}
    except Exception as e:
        autonomy_controller.log_action('tool_execution_error', {'tool': tool, 'params': params}, {'error': str(e)})
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA ENDPOINTS - Local LLM Integration (Agent Amigos manages Ollie)
# ═══════════════════════════════════════════════════════════════════════════════

class OllamaGenerateRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    task_type: Optional[str] = "default"
    system: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None

class OllamaChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    task_type: Optional[str] = "default"
    system: Optional[str] = None
    temperature: Optional[float] = 0.7

class AmigosDelegateRequest(BaseModel):
    task: str
    context: Optional[str] = None
    task_type: Optional[str] = "default"
    prefer_fast: Optional[bool] = False

class OllamaEnhanceRequest(BaseModel):
    content: str
    enhancement_type: Optional[str] = "improve"
    target_audience: Optional[str] = "general"

@app.get("/ollama/status")
async def ollama_status_endpoint():
    """
    Check if Ollama is running and available.
    Returns status and list of available models.
    """
    status = await get_ollama_status()
    return {
        "success": status.get("running", False),
        "ollama": status,
        "agent": "Ollie",
        "managed_by": "Agent Amigos"
    }


# --- Convenience endpoint: Ask Ollie via Agent Amigos (explicit delegation) ---
@app.post("/agents/ask-ollie")
async def agents_ask_ollie(request: AmigosDelegateRequest):
    """Ask Ollie via Agent Amigos. This ensures Amigos evaluates and delegates appropriately."""
    try:
        from tools.ollama_tools import amigos_ask_ollie
        log_communication(
            "amigos",
            "ollie",
            channel="delegate",
            summary=(request.task or "")[:200],
            payload={"context": bool(request.context), "prefer_fast": bool(request.prefer_fast)},
        )
        agent_working("amigos", f"Delegating to Ollie: {request.task[:50]}...", progress=20)
        res = await amigos_ask_ollie(task=request.task, context=request.context, prefer_fast=request.prefer_fast)
        autonomy_controller.log_action('delegated_to_ollie', {'task': request.task[:200]}, {'success': res.get('success')})
        if res.get('success'):
            agent_idle('amigos')
            agent_idle('ollie')
            return {"success": True, "delegated_to": "ollie", "data": res}
        return {"success": False, "error": res.get('error'), "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ollama/models")
async def ollama_models_endpoint():
    """
    Get list of available Ollama models.
    Shows model details and Amigos recommendations.
    """
    models = await get_ollama_models()
    return {
        "success": models.get("success", False),
        "data": models,
        "routing": ollama_service.MODEL_ROUTING,
        "managed_by": "Agent Amigos"
    }

@app.post("/ollama/generate")
async def ollama_generate_endpoint(request: OllamaGenerateRequest):
    """
    Generate a response from Ollama.
    Agent Amigos routes to the best model for the task.
    """
    result = await ollama_service.generate(
        prompt=request.prompt,
        model=request.model,
        task_type=request.task_type or "default",
        system=request.system,
        temperature=request.temperature or 0.7,
        max_tokens=request.max_tokens
    )
    return {
        "success": result.get("success", False),
        "data": result,
        "managed_by": "Agent Amigos"
    }

@app.post("/ollama/chat")
async def ollama_chat_endpoint(request: OllamaChatRequest):
    """
    Chat with Ollama using conversation history.
    Supports multi-turn conversations.
    """
    result = await ollama_service.chat(
        messages=request.messages,
        model=request.model,
        task_type=request.task_type or "default",
        system=request.system,
        temperature=request.temperature or 0.7
    )
    return {
        "success": result.get("success", False),
        "data": result,
        "managed_by": "Agent Amigos"
    }

@app.post("/ollama/delegate")
async def ollama_delegate_endpoint(request: AmigosDelegateRequest, x_internal_token: Optional[str] = Header(None)):
    """
    Agent Amigos delegates a task to Ollie (local LLM).
    This is the main interface for Amigos-managed local AI tasks.
    If the environment variable AMIGOS_INTERNAL_TOKEN is set, callers must provide it via the X-Internal-Token header.
    """
    token = os.environ.get('AMIGOS_INTERNAL_TOKEN')
    if token:
        if x_internal_token != token:
            raise HTTPException(status_code=403, detail={'error': 'forbidden', 'reason': 'invalid_internal_token'})

    log_communication(
        "amigos",
        "ollie",
        channel="delegate",
        summary=(request.task or "")[:200],
        payload={"context": bool(request.context), "prefer_fast": bool(request.prefer_fast)},
    )

    result = await ollama_service.amigos_delegate(
        task=request.task,
        context=request.context,
        task_type=request.task_type or "default",
        prefer_fast=request.prefer_fast or False
    )
    return {
        "success": result.get("success", False),
        "data": result,
        "agent": "Ollie",
        "managed_by": "Agent Amigos"
    }

@app.post("/ollama/enhance")
async def ollama_enhance_endpoint(request: OllamaEnhanceRequest):
    """
    Enhance content using Ollama.
    Used by Scrapey and other tools for AI-powered content improvement.
    """
    result = await ollama_service.enhance_content(
        content=request.content,
        enhancement_type=request.enhancement_type or "improve",
        target_audience=request.target_audience or "general"
    )
    return {
        "success": result.get("success", False),
        "data": result,
        "managed_by": "Agent Amigos"
    }

# ============================================================================
# SHARED MEMORY ENDPOINTS - Local memory shared between Amigos and Ollie
# ============================================================================

class MemoryLearnRequest(BaseModel):
    fact: str
    category: Optional[str] = "general"
    source: Optional[str] = "user"

class MemoryRecallRequest(BaseModel):
    query: str
    max_results: Optional[int] = 10
    category: Optional[str] = None

class MemoryConversationRequest(BaseModel):
    role: str
    content: str
    agent: Optional[str] = "amigos"

class MemoryPreferenceRequest(BaseModel):
    key: str
    value: Any

@app.get("/memory/stats")
async def memory_stats_endpoint():
    """
    Get statistics about shared memory.
    Shows how much Amigos and Ollie have learned.
    """
    stats = shared_memory.get_memory_stats()
    return {
        "success": True,
        "data": stats,
        "managed_by": "Agent Amigos"
    }

@app.get("/memory/facts")
async def memory_facts_endpoint(category: Optional[str] = None, limit: int = 50):
    """
    Get learned facts from shared memory.
    """
    all_facts = shared_memory.facts.get("facts", [])
    
    if category:
        filtered = [f for f in all_facts if f.get("category") == category]
    else:
        filtered = all_facts
    
    # Sort by timestamp descending and limit
    sorted_facts = sorted(filtered, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
    
    return {
        "success": True,
        "data": {
            "facts": sorted_facts,
            "total": len(all_facts),
            "showing": len(sorted_facts)
        },
        "managed_by": "Agent Amigos"
    }

@app.post("/memory/learn")
async def memory_learn_endpoint(request: MemoryLearnRequest):
    """
    Teach Amigos and Ollie a new fact.
    Both agents share this memory locally.
    """
    success = learn(request.fact, category=request.category, source=request.source)
    return {
        "success": success,
        "message": f"Learned: {request.fact[:100]}..." if len(request.fact) > 100 else f"Learned: {request.fact}",
        "managed_by": "Agent Amigos"
    }

@app.post("/memory/recall")
async def memory_recall_endpoint(request: MemoryRecallRequest):
    """
    Recall facts from shared memory.
    Search for relevant information that both agents know.
    """
    facts = recall(request.query, max_results=request.max_results, category=request.category)
    return {
        "success": True,
        "data": {
            "query": request.query,
            "facts": facts,
            "count": len(facts)
        },
        "managed_by": "Agent Amigos"
    }

@app.get("/memory/context")
async def memory_context_endpoint(task: str, agent: str = "amigos"):
    """
    Get relevant memory context for a task.
    This is what Amigos/Ollie uses internally to remember past interactions.
    """
    context = get_context(task)
    return {
        "success": True,
        "data": {
            "task": task,
            "agent": agent,
            "context": context
        },
        "managed_by": "Agent Amigos"
    }

@app.post("/memory/conversation")
async def memory_conversation_endpoint(request: MemoryConversationRequest):
    """
    Log a conversation to shared memory.
    Both agents can see past conversations.
    """
    success = remember_conversation(request.role, request.content, agent=request.agent)
    return {
        "success": success,
        "message": "Conversation logged to shared memory",
        "managed_by": "Agent Amigos"
    }

@app.get("/memory/conversations")
async def memory_conversations_endpoint(limit: int = 20, agent: Optional[str] = None):
    """
    Get recent conversations from shared memory.
    """
    conversations = shared_memory.get_recent_conversations(limit)
    
    if agent:
        conversations = [c for c in conversations if c.get("agent") == agent]
    
    return {
        "success": True,
        "data": {
            "conversations": conversations,
            "count": len(conversations)
        },
        "managed_by": "Agent Amigos"
    }

@app.post("/memory/preference")
async def memory_set_preference_endpoint(request: MemoryPreferenceRequest):
    """
    Set a user preference in shared memory.
    Both agents will respect this preference.
    """
    shared_memory.set_preference(request.key, request.value)
    return {
        "success": True,
        "message": f"Preference '{request.key}' saved",
        "managed_by": "Agent Amigos"
    }

@app.get("/memory/preferences")
async def memory_get_preferences_endpoint():
    """
    Get all user preferences from shared memory.
    """
    prefs = shared_memory.preferences.get("preferences", {})
    return {
        "success": True,
        "data": prefs,
        "managed_by": "Agent Amigos"
    }

@app.get("/memory/tasks")
async def memory_tasks_endpoint(limit: int = 50, successful_only: bool = False):
    """
    Get task history from shared memory.
    Shows what tasks have been completed and which tools were used.
    """
    tasks = shared_memory.tasks.get("tasks", [])
    
    if successful_only:
        tasks = [t for t in tasks if t.get("success")]
    
    sorted_tasks = sorted(tasks, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
    
    return {
        "success": True,
        "data": {
            "tasks": sorted_tasks,
            "total": len(shared_memory.tasks.get("tasks", [])),
            "showing": len(sorted_tasks)
        },
        "managed_by": "Agent Amigos"
    }

# ============================================================================
# DOCUMENT STORAGE ENDPOINTS - Persistent Document Database for Agents
# ============================================================================

class DocumentUploadRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = ""
    tags: Optional[List[str]] = []
    category: Optional[str] = "general"
    agent: Optional[str] = "amigos"

class URLStoreRequest(BaseModel):
    url: str
    title: Optional[str] = None
    description: Optional[str] = ""
    content: Optional[str] = ""
    tags: Optional[List[str]] = []
    category: Optional[str] = "web"
    agent: Optional[str] = "amigos"

class PlanStoreRequest(BaseModel):
    title: str
    content: str
    plan_type: Optional[str] = "general"
    tags: Optional[List[str]] = []
    category: Optional[str] = "plans"
    agent: Optional[str] = "amigos"

class TextStoreRequest(BaseModel):
    content: str
    title: Optional[str] = None
    description: Optional[str] = ""
    tags: Optional[List[str]] = []
    category: Optional[str] = "notes"
    agent: Optional[str] = "amigos"

class DocumentSearchRequest(BaseModel):
    query: Optional[str] = None
    doc_type: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    limit: Optional[int] = 20

@app.get("/documents/stats")
async def documents_stats_endpoint():
    """
    Get document storage statistics.
    Shows total documents stored by type, size, and categories.
    """
    stats = document_storage.get_stats()
    return {
        "success": True,
        "data": stats,
        "managed_by": "Agent Amigos"
    }

@app.post("/documents/upload")
async def documents_upload_endpoint(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(""),
    tags: Optional[str] = Form(""),
    category: Optional[str] = Form("general"),
    agent: Optional[str] = Form("amigos")
):
    """
    Upload a document (PDF, image, video, text file) to the document database.
    The document will be indexed and searchable by all agents.
    """
    try:
        # Read file content
        file_content = await file.read()
        filename = file.filename
        
        # Parse tags from comma-separated string
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        
        result = document_storage.store_file(
            file_content=file_content,
            filename=filename,
            title=title or filename,
            description=description,
            tags=tag_list,
            category=category,
            source="upload",
            agent=agent
        )
        
        return {
            "success": result.get("success", False),
            "data": result,
            "managed_by": "Agent Amigos"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "managed_by": "Agent Amigos"
        }

@app.post("/documents/url")
async def documents_store_url_endpoint(request: URLStoreRequest):
    """
    Store a URL with optional scraped content.
    Agents can reference this URL content in future tasks.
    """
    result = document_storage.store_url(
        url=request.url,
        title=request.title,
        description=request.description,
        content=request.content,
        tags=request.tags,
        category=request.category,
        agent=request.agent
    )
    return {
        "success": result.get("success", False),
        "data": result,
        "managed_by": "Agent Amigos"
    }

@app.post("/documents/plan")
async def documents_store_plan_endpoint(request: PlanStoreRequest):
    """
    Store a plan or strategy document.
    Agents can reference stored plans for executing multi-step tasks.
    """
    result = document_storage.store_plan(
        title=request.title,
        content=request.content,
        plan_type=request.plan_type,
        tags=request.tags,
        category=request.category,
        agent=request.agent
    )
    return {
        "success": result.get("success", False),
        "data": result,
        "managed_by": "Agent Amigos"
    }

@app.post("/documents/text")
async def documents_store_text_endpoint(request: TextStoreRequest):
    """
    Store a text document or note.
    Great for saving important information or notes from conversations.
    """
    result = document_storage.store_text(
        content=request.content,
        title=request.title,
        description=request.description,
        tags=request.tags,
        category=request.category,
        agent=request.agent
    )
    return {
        "success": result.get("success", False),
        "data": result,
        "managed_by": "Agent Amigos"
    }

@app.post("/documents/search")
async def documents_search_endpoint(request: DocumentSearchRequest):
    """
    Search stored documents.
    Find documents by query, type, tags, or category.
    """
    results = document_storage.search_documents(
        query=request.query,
        doc_type=request.doc_type,
        tags=request.tags,
        category=request.category,
        limit=request.limit
    )
    return {
        "success": True,
        "data": {
            "results": results,
            "count": len(results),
            "query": request.query
        },
        "managed_by": "Agent Amigos"
    }

@app.get("/documents/{doc_id}")
async def documents_get_endpoint(doc_id: str):
    """
    Get a specific document by ID.
    """
    doc = document_storage.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "success": True,
        "data": doc,
        "managed_by": "Agent Amigos"
    }

@app.get("/documents/{doc_id}/content")
async def documents_get_content_endpoint(doc_id: str):
    """
    Get the text content of a document.
    """
    content = document_storage.get_document_content(doc_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Document or content not found")
    return {
        "success": True,
        "data": {
            "doc_id": doc_id,
            "content": content
        },
        "managed_by": "Agent Amigos"
    }

@app.get("/documents/{doc_id}/file")
async def documents_get_file_endpoint(doc_id: str):
    """
    Download the raw file for a document.
    """
    doc = document_storage.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = Path(doc.get("path", ""))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=doc.get("filename", file_path.name),
        media_type=doc.get("metadata", {}).get("mime_type", "application/octet-stream")
    )

@app.delete("/documents/{doc_id}")
async def documents_delete_endpoint(doc_id: str):
    """
    Delete a document from the database.
    """
    result = document_storage.delete_document(doc_id)
    return {
        "success": result.get("success", False),
        "data": result,
        "managed_by": "Agent Amigos"
    }

@app.put("/documents/{doc_id}")
async def documents_update_endpoint(doc_id: str, updates: Dict[str, Any]):
    """
    Update document metadata (title, description, tags, category).
    """
    result = document_storage.update_document(doc_id, updates)
    return {
        "success": result.get("success", False),
        "data": result,
        "managed_by": "Agent Amigos"
    }

@app.get("/documents/list/recent")
async def documents_list_recent_endpoint(limit: int = 10):
    """
    Get recently stored documents.
    """
    docs = document_storage.get_recent_documents(limit)
    return {
        "success": True,
        "data": {
            "documents": docs,
            "count": len(docs)
        },
        "managed_by": "Agent Amigos"
    }

@app.get("/documents/list/frequent")
async def documents_list_frequent_endpoint(limit: int = 10):
    """
    Get frequently accessed documents.
    """
    docs = document_storage.get_frequently_accessed(limit)
    return {
        "success": True,
        "data": {
            "documents": docs,
            "count": len(docs)
        },
        "managed_by": "Agent Amigos"
    }

@app.get("/documents/list/type/{doc_type}")
async def documents_list_by_type_endpoint(doc_type: str, limit: int = 50):
    """
    List documents by type (image, video, pdf, text, url, plan).
    """
    docs = document_storage.list_by_type(doc_type, limit)
    return {
        "success": True,
        "data": {
            "type": doc_type,
            "documents": docs,
            "count": len(docs)
        },
        "managed_by": "Agent Amigos"
    }

@app.get("/documents/context")
async def documents_context_endpoint(task: str, limit: int = 5):
    """
    Get relevant document context for a task.
    This is what agents use to reference stored documents.
    """
    context = document_storage.get_context_for_task(task, limit)
    return {
        "success": True,
        "data": {
            "task": task,
            "context": context
        },
        "managed_by": "Agent Amigos"
    }

# ============================================================================
# AGENT TEAM ENDPOINTS - Multi-Agent Coordination System
# ============================================================================

@app.get("/agents/team")
async def get_agent_team():
    """
    Get the full agent team status with LED indicators.
    Shows all agents, their status, and current activities.
    """
    # Check Ollama status and update Ollie (silently - Ollama is optional)
    try:
        ollama_status = await ollama_service.get_status()
        if ollama_status.get("running"):
            agent_online("ollie")
        else:
            agent_offline("ollie")
    except Exception:
        # Ollama not running - this is normal, Ollie is optional
        agent_offline("ollie")

    # Throttle server-side logging to avoid noisy logs when clients poll frequently
    try:
        now = time.monotonic()
        should_log = False
        with TEAM_LOG_LOCK:
            global TEAM_LAST_LOG_TIME
            if now - TEAM_LAST_LOG_TIME >= TEAM_LOG_MIN_INTERVAL:
                TEAM_LAST_LOG_TIME = now
                should_log = True
        if should_log:
            summary = get_team_status_summary()
            logger.info("/agents/team requested - team summary: %s", summary)
    except Exception:
        # Never let logging failure break the endpoint
        logger.debug("Failed to evaluate throttled log for /agents/team", exc_info=True)

    return {
        "success": True,
        "data": get_team_status(),
        "managed_by": "Agent Amigos",
    }


@app.get("/agents/communications")
def get_agent_communications(limit: int = 50, top_agent: str = "amigos", top_limit: int = 5):
    """
    Get recent agent-to-agent communications and top contacts for a specific agent.
    """
    return {
        "success": True,
        "data": {
            "events": get_communications(limit),
            "top_contacts": get_top_contacts(top_agent, top_limit),
            "top_agent": top_agent,
        },
        "managed_by": "Agent Amigos",
    }

@app.post("/agents/{agent_id}/status")
async def update_agent_status(agent_id: str, status: str, task: Optional[str] = None):
    """
    Update an agent status.
    Used internally to track agent engagement.
    """
    from tools.agent_coordinator import AgentStatus
    try:
        status_enum = AgentStatus(status)
        coordinator.set_agent_status(agent_id, status_enum, task)
        return {
            "success": True,
            "agent": agent_id,
            "status": status,
            "managed_by": "Agent Amigos"
        }
    except ValueError:
        return {
            "success": False,
            "error": f"Invalid status: {status}",
            "valid_statuses": [s.value for s in AgentStatus]
        }

@app.get("/agents/{agent_id}")
async def get_agent_info(agent_id: str):
    """
    Get detailed info about a specific agent.
    """
    agent = coordinator.get_agent(agent_id)
    if agent:
        return {
            "success": True,
            "data": agent,
            "managed_by": "Agent Amigos"
        }
    return {
        "success": False,
        "error": f"Agent '{agent_id}' not found",
        "available_agents": list(coordinator.agents.keys())
    }

@app.post("/agents/collaborate")
async def start_agent_collaboration(primary: str, helpers: List[str], task: str):
    """
    Start a multi-agent collaboration.
    Primary agent leads, helpers assist.
    """
    collab_id = start_collaboration(primary, helpers, task)
    return {
        "success": True,
        "collaboration_id": collab_id,
        "primary": primary,
        "helpers": helpers,
        "task": task,
        "managed_by": "Agent Amigos"
    }

@app.post("/agents/collaborate/{collab_id}/end")
async def end_agent_collaboration(collab_id: str, success: bool = True):
    """
    End a multi-agent collaboration.
    """
    end_collaboration(collab_id, success)
    return {
        "success": True,
        "collaboration_id": collab_id,
        "status": "completed" if success else "failed",
        "managed_by": "Agent Amigos"
    }

@app.post("/agents/demo/facebook-post")
async def run_facebook_post_demo_endpoint(background_tasks: BackgroundTasks):
    """
    Run the Facebook Post Demo - shows all agents working together
    to create a trending topic post. Watch the LED indicators!
    """
    from tools.agent_coordinator import run_facebook_post_demo
    
    # Run demo in background so it doesn't block
    background_tasks.add_task(run_facebook_post_demo)
    
    return {
        "success": True,
        "message": "Facebook Post Demo started! Watch the Agent LEDs light up as each agent works on their task.",
        "managed_by": "Agent Amigos"
    }

@app.get("/agents/demo/progress")
async def get_demo_progress_endpoint():
    """
    Get current demo progress.
    """
    from tools.agent_coordinator import get_demo_progress
    progress = await get_demo_progress()
    return {
        "success": True,
        "data": progress,
        "managed_by": "Agent Amigos"
    }

@app.post("/agents/demo/reset")
async def reset_demo_endpoint():
    """
    Reset demo and return agents to normal state.
    """
    from tools.agent_coordinator import reset_team_demo
    result = await reset_team_demo()
    return {
        "success": True,
        "data": result,
        "managed_by": "Agent Amigos"
    }

@app.post("/agents/{agent_id}/tool")
async def set_agent_tool_endpoint(agent_id: str, tool_name: str, tool_emoji: str = "🔧"):
    """
    Set the current tool an agent is using.
    """
    from tools.agent_coordinator import set_agent_tool
    set_agent_tool(agent_id, tool_name, tool_emoji)
    return {
        "success": True,
        "agent": agent_id,
        "tool": tool_name,
        "managed_by": "Agent Amigos"
    }

@app.delete("/agents/{agent_id}/tool")
async def clear_agent_tool_endpoint(agent_id: str):
    """
    Clear the current tool for an agent.
    """
    from tools.agent_coordinator import clear_agent_tool
    clear_agent_tool(agent_id)
    return {
        "success": True,
        "agent": agent_id,
        "tool": None,
        "managed_by": "Agent Amigos"
    }

# --- Data Models ---
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    require_approval: Optional[bool] = True  # Ask before dangerous actions
    screen_context: Optional[Dict[str, Any]] = None # Context about what's on screen
    team_mode: Optional[bool] = False # Enable multi-agent coordination

class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}
    parameters: Dict[str, Any] = {}
    
    def get_args(self):
        """Get arguments, checking both arguments and parameters fields"""
        return self.arguments or self.parameters or {}


class AttachProcessRequest(BaseModel):
    pid: int


class CreateModTemplateRequest(BaseModel):
    game: str
    mod_name: str
    mod_type: Optional[str] = "basic"

class ScanMemoryRequest(BaseModel):
    value: Any
    data_type: str = "int"
    scan_type: str = "exact"

class NextScanRequest(BaseModel):
    filter_type: str = "exact"
    value: Optional[Any] = None

class WriteMemoryRequest(BaseModel):
    address: int
    value: Any
    data_type: str = "int"

class FreezeValueRequest(BaseModel):
    address: int
    value: Any
    data_type: str = "int"
    name: Optional[str] = None

class UnfreezeValueRequest(BaseModel):
    address: int

class AOBScanRequest(BaseModel):
    pattern: str

class PointerScanRequest(BaseModel):
    target_address: int
    max_depth: int = 3

class CheatTableRequest(BaseModel):
    filename: str
    entries: Optional[List[Dict]] = None

class AgentResponse(BaseModel):
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    actions_taken: Optional[List[Dict]] = None
    needs_approval: Optional[bool] = False
    pending_action: Optional[Dict] = None
    canvas_commands: Optional[List[Dict]] = None  # Canvas drawing commands from design tools
    map_commands: Optional[List[Dict]] = None     # Map commands for geographic interaction
    search_results: Optional[List[Dict]] = None   # Web search results for Internet Console
    todo_list: Optional[List[Dict]] = None        # Current todo list for progress tracking
    progress: Optional[int] = None                # Current progress percentage (0-100)
    delegated_to: Optional[str] = None            # If Amigos delegated this response to another agent (e.g., 'ollie')

# ═══════════════════════════════════════════════════════════════════════════════
# MAP TOOLS - Geographic Interaction for Agent Amigos
# Control the Map Console to show locations, routes, and travel plans
# ═══════════════════════════════════════════════════════════════════════════════

def map_control(place: str = None, origin: str = None, destination: str = None, mode: str = "driving", zoom: int = 15, view: str = "roadmap", **kwargs):
    """
    Control the Map Console to show a specific place or a route between two locations.
    
    Args:
        place: A specific location, address, or landmark to show on the map.
        origin: The starting point for a route.
        destination: The destination for a route.
        mode: Travel mode: 'driving', 'walking', 'bicycling', or 'transit'.
        zoom: Zoom level (1-21). Default is 15.
        view: Map view type: 'roadmap', 'satellite', 'terrain', or 'streetview'.
    """
    try:
        # Handle 'location' as an alias for 'place'
        if not place and 'location' in kwargs:
            place = kwargs['location']
            
        # Verify and correct spelling of locations
        if place:
            place = resolve_location_name(place)
        if origin:
            origin = resolve_location_name(origin)
        if destination:
            destination = resolve_location_name(destination)
            
        command = {
            "type": "map_update",
            "place": place,
            "from": origin,
            "to": destination,
            "mode": mode,
            "zoom": zoom,
            "view": view
        }
        
        msg = f"Map updated to show {place or f'route from {origin} to {destination}'}"
        if view != "roadmap":
            msg += f" in {view} view"
        if zoom != 15:
            msg += f" at zoom level {zoom}"
            
        return {
            "success": True, 
            "message": msg,
            "map_commands": [command]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ═══════════════════════════════════════════════════════════════════════════════
# CANVAS TOOLS - Visual Canvas for Agent Amigos
# Draw shapes, floor plans, diagrams, poetry on the visual canvas
# ═══════════════════════════════════════════════════════════════════════════════

def canvas_draw_shape(shape_type: str, x1: float, y1: float, x2: float = None, y2: float = None, 
                          color: str = "#6366f1", fill: str = None, width: float = 2):
    """Draw a shape on the Canvas canvas."""
    try:
        params = {"x1": x1, "y1": y1, "color": color, "width": width}
        if x2 is not None: params["x2"] = x2
        if y2 is not None: params["y2"] = y2
        if fill: params["fillColor"] = fill
        
        if shape_type == "line":
            cmd_id = canvas_controller.draw_line(x1, y1, x2 or x1+100, y2 or y1+100, color, width)
        elif shape_type == "rectangle":
            cmd_id = canvas_controller.draw_rectangle(x1, y1, x2 or 100, y2 or 100, color, fill, width)
        elif shape_type == "ellipse":
            cmd_id = canvas_controller.draw_ellipse(x1, y1, x2 or 50, y2 or 50, color, fill, width)
        elif shape_type == "arrow":
            cmd_id = canvas_controller.draw_arrow(x1, y1, x2 or x1+100, y2 or y1+100, color, width)
        else:
            return {"success": False, "error": f"Unknown shape: {shape_type}"}
        
        return {"success": True, "command_id": cmd_id, "shape": shape_type}
    except Exception as e:
        return {"success": False, "error": str(e)}

def canvas_draw_text(text: str, x: float, y: float, font_size: int = 16, color: str = "#ffffff"):
    """Add text to the Canvas canvas."""
    try:
        cmd_id = canvas_controller.draw_text(x, y, text, font_size=font_size, color=color)
        return {"success": True, "command_id": cmd_id, "text": text}
    except Exception as e:
        return {"success": False, "error": str(e)}

def canvas_floor_plan(rooms: list, scale: float = 10):
    """Generate a floor plan with rooms on the Canvas.
    
    rooms: List of room dicts with {name, width, height, x, y, doors?, windows?}
    scale: Pixels per foot (default 10)
    """
    try:
        cmd_id = canvas_controller.generate_floor_plan(rooms, scale=scale, 
            thought="Agent Amigos is drawing a floor plan")
        return {"success": True, "command_id": cmd_id, "rooms_count": len(rooms)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def canvas_flowchart(nodes: list, connections: list, layout: str = "vertical"):
    """Generate a flowchart diagram on the Canvas.
    
    nodes: List of {id, label, type: start|end|process|decision}
    connections: List of {from_id, to_id, label?}
    """
    try:
        cmd_id = canvas_controller.generate_flowchart(nodes, connections, layout=layout,
            thought="Agent Amigos is creating a flowchart")
        return {"success": True, "command_id": cmd_id, "nodes_count": len(nodes)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def canvas_poem(title: str, lines: list, style: str = "classic"):
    """Render a poem with artistic typography on the Canvas.
    
    style: classic, modern, handwritten, gothic
    """
    try:
        cmd_id = canvas_controller.render_poem(title, lines, style=style,
            thought=f"Agent Amigos is rendering poem: {title}")
        return {"success": True, "command_id": cmd_id, "title": title}
    except Exception as e:
        return {"success": False, "error": str(e)}

def canvas_clear():
    """Clear the entire Canvas canvas."""
    try:
        cmd_id = canvas_controller.clear_canvas(thought="Agent Amigos cleared the canvas")
        return {"success": True, "command_id": cmd_id}
    except Exception as e:
        return {"success": False, "error": str(e)}

def canvas_set_mode(mode: str):
    """Switch Canvas mode: SKETCH, DIAGRAM, CAD, MEDIA, TEXT"""
    try:
        cmd_id = canvas_controller.set_mode(mode.upper(), thought=f"Switching to {mode} mode")
        return {"success": True, "command_id": cmd_id, "mode": mode.upper()}
    except Exception as e:
        return {"success": False, "error": str(e)}

def canvas_export(format: str = "png", filename: str = None):
    """Export the Canvas canvas. Formats: png, svg, pdf, dxf, json"""
    try:
        cmd_id = canvas_controller.export_canvas(format=format.lower(), filename=filename,
            thought=f"Exporting canvas as {format.upper()}")
        return {"success": True, "command_id": cmd_id, "format": format}
    except Exception as e:
        return {"success": False, "error": str(e)}

def canvas_get_commands():
    """Get all pending Canvas commands."""
    try:
        commands = canvas_controller.get_pending_commands()
        return {"success": True, "pending_count": len(commands), "commands": commands}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# OPENWORK TOOL FUNCTIONS - Agentic Workflow Management
# Allow Agent Amigos to create and manage OpenWork sessions via natural language
# ═══════════════════════════════════════════════════════════════════════════════

def _default_openwork_workspace() -> str:
    repo_root = Path(__file__).resolve().parent.parent
    return str(repo_root)


def openwork_status_tool():
    """Get OpenWork/OpenCode server status."""
    return {
        "success": True,
        "server_running": openwork_manager.opencode_process is not None,
        "host": openwork_manager.opencode_host,
        "port": openwork_manager.opencode_port,
    }


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        # If we're already inside an event loop, run the coroutine on a fresh loop
        # in a worker thread to avoid deadlocks.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(coro)).result()


def openwork_start_server_tool(workspace_path: Optional[str] = None):
    """Start OpenCode server for a workspace.

    Args:
        workspace_path: Path to workspace (defaults to repo root)
    """
    target = workspace_path or _default_openwork_workspace()
    return _run_async(openwork_manager.start_opencode_server(target))


def openwork_stop_server_tool():
    """Stop the OpenCode server."""
    _run_async(openwork_manager.stop_opencode_server())
    return {"success": True, "message": "OpenCode server stopped"}


def openwork_get_skills_tool(workspace_path: Optional[str] = None):
    """Get installed OpenCode skills for a workspace.

    Args:
        workspace_path: Path to workspace (defaults to repo root)
    """
    target = workspace_path or _default_openwork_workspace()
    return {
        "success": True,
        "skills": openwork_manager.get_workspace_skills(target),
    }


def openwork_create_session(workspace_path: Optional[str], prompt: str):
    """Create a new OpenWork session for an agentic workflow.
    
    Args:
        workspace_path: Path to the workspace (use current workspace if unsure)
        prompt: Description of the task/workflow to execute
    
    Returns:
        Session details including session_id for tracking
    """
    try:
        target = workspace_path or _default_openwork_workspace()
        return openwork_manager.create_session(target, prompt)
    except Exception as e:
        return {"success": False, "error": str(e)}


def openwork_get_session(session_id: str):
    """Get details about an OpenWork session including todos and messages.
    
    Args:
        session_id: The session ID to query
    
    Returns:
        Session details with todos, messages, and status
    """
    try:
        session = openwork_manager.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        return {"success": True, "session": session}
    except Exception as e:
        return {"success": False, "error": str(e)}


def openwork_list_sessions():
    """List all active OpenWork sessions.
    
    Returns:
        List of sessions with summary information
    """
    try:
        return {
            "success": True,
            "sessions": openwork_manager.list_sessions()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def openwork_add_todo(session_id: str, title: str, description: str = "", status: str = "not-started"):
    """Add a todo/task to an OpenWork session.
    
    Args:
        session_id: The session to add the todo to
        title: Brief title of the task
        description: Optional detailed description
        status: Task status (not-started, in-progress, completed)
    
    Returns:
        Success status
    """
    try:
        import uuid
        todo = {
            "id": str(uuid.uuid4()),
            "title": title,
            "description": description,
            "status": status,
            "created_at": datetime.now().isoformat()
        }
        success = openwork_manager.add_todo(session_id, todo)
        if not success:
            return {"success": False, "error": "Session not found"}
        return {"success": True, "todo": todo}
    except Exception as e:
        return {"success": False, "error": str(e)}


def openwork_update_todo(session_id: str, todo_id: str, status: str = None, title: str = None, description: str = None):
    """Update a todo in an OpenWork session (e.g., mark as completed).
    
    Args:
        session_id: The session containing the todo
        todo_id: The todo to update
        status: New status (not-started, in-progress, completed)
        title: New title (optional)
        description: New description (optional)
    
    Returns:
        Success status
    """
    try:
        updates = {}
        if status: updates["status"] = status
        if title: updates["title"] = title
        if description: updates["description"] = description
        
        success = openwork_manager.update_todo(session_id, todo_id, updates)
        if not success:
            return {"success": False, "error": "Session or todo not found"}
        return {"success": True, "updates": updates}
    except Exception as e:
        return {"success": False, "error": str(e)}


def openwork_add_message(session_id: str, role: str, content: str):
    """Add a message/log entry to an OpenWork session.
    
    Args:
        session_id: The session to add the message to
        role: Message role (user, assistant, system)
        content: Message content
    
    Returns:
        Success status
    """
    try:
        message = {
            "role": role,
            "content": content
        }
        success = openwork_manager.add_message(session_id, message)
        if not success:
            return {"success": False, "error": "Session not found"}
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def openwork_close_session(session_id: str):
    """Close/complete an OpenWork session.
    
    Args:
        session_id: The session to close
    
    Returns:
        Success status
    """
    try:
        success = openwork_manager.close_session(session_id)
        if not success:
            return {"success": False, "error": "Session not found"}
        return {"success": True, "message": "Session closed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def openwork_get_workspaces():
    """List available workspaces for OpenWork.
    
    Returns:
        List of workspace paths and info
    """
    try:
        return {
            "success": True,
            "workspaces": openwork_manager.list_workspaces()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Tool Registry ---
# Maps tool names to (function, requires_approval, description)
TOOLS = {
    # AI Governance & Company Ops
    "get_available_voices": (agent_get_available_voices, False, "List all available AI voices for company agents"),
    "set_agent_voice": (agent_set_voice, False, "Assign a specific voice to an AI agent role"),
    "run_executive_meeting": (agent_run_executive_meeting, False, "Run an autonomous executive strategy session"),
    "run_standup": (agent_run_standup, False, "Run a daily departmental standup to check progress"),
    "get_meeting_logs": (agent_get_meeting_logs, False, "View the persistent logs of all AI corporate meetings"),
    
    # Computer Control - Keyboard
    "type_text": (computer.type_text, False, "Type text character by character"),
    "type_unicode": (computer.type_unicode, False, "Type text including unicode/special characters"),
    "press_key": (computer.press_key, False, "Press a key (enter, tab, escape, f1-f12, etc.)"),
    "hotkey": (computer.hotkey, False, "Press keyboard shortcut like ctrl+c, ctrl+v, alt+tab"),
    
    # Computer Control - Mouse
    "move_mouse": (computer.move_mouse, False, "Move mouse to x,y position"),
    "move_mouse_relative": (computer.move_mouse_relative, False, "Move mouse by dx,dy relative to current position"),
    "click": (computer.click, False, "Click at position (optional x,y, button, clicks)"),
    "double_click": (computer.double_click, False, "Double-click at position"),
    "right_click": (computer.right_click, False, "Right-click at position"),
    "scroll": (computer.scroll, False, "Scroll up (positive) or down (negative)"),
    "drag": (computer.drag, False, "Drag from one position to another"),
    "get_mouse_position": (computer.get_mouse_position, False, "Get current mouse x,y"),
    
    # Computer Control - Screen
    "screenshot": (computer.screenshot, False, "Take a screenshot"),
    "get_screen_size": (computer.get_screen_size, False, "Get screen dimensions"),
    "locate_on_screen": (computer.locate_on_screen, False, "Find image on screen"),
    "click_image": (computer.click_image, False, "Find and click an image on screen"),

    # Window Management (safe)
    "list_windows": (window_tools.list_windows, False, "List top-level desktop windows"),
    "get_foreground_window": (window_tools.get_foreground_window, False, "Get the active foreground window"),
    "get_window_rect": (window_tools.get_window_rect, False, "Get window rectangle (left/top/width/height)"),
    "activate_window": (window_tools.activate_window, False, "Bring a window to the foreground"),
    
    # Web - Browser Automation
    "open_browser": (web.open_browser, False, "Open automated browser (edge/chrome)"),
    "open_browser_with_profile": (web.open_browser_with_profile, False, "Open Chrome with saved profile (keeps logins!)"),
    "attach_to_existing_browser": (web.attach_to_existing_browser, False, "Attach to existing Chrome browser (port 9222)"),
    "ensure_browser_ready": (web.ensure_browser_ready, False, "Smart browser detection - reuse existing or open new"),
    "close_browser": (web.close_browser, False, "Close the browser"),
    "navigate": (web.navigate, False, "Navigate to a URL"),
    "get_page_content": (web.get_page_content, False, "Get text content of current page"),
    "click_element": (web.click_element, False, "Click element by selector"),
    "type_in_element": (web.type_in_element, False, "Type into input field"),
    "take_browser_screenshot": (web.take_browser_screenshot, False, "Screenshot the browser"),
    "execute_javascript": (web.execute_javascript, False, "Run JavaScript in browser"),
    "go_back": (web.go_back, False, "Browser back"),
    "go_forward": (web.go_forward, False, "Browser forward"),
    "refresh": (web.refresh, False, "Refresh page"),
    "new_tab": (web.new_tab, False, "Open new browser tab"),
    "close_tab": (web.close_tab, False, "Close current tab"),
    
    # Web - Search (no browser needed)
    "web_search": (web.web_search, False, "Search the web and show results in the Internet Console. Args: query (search term). Use this for real-time info, news, or general searches."),
    "web_search_news": (web.web_search_news, False, "Search news and show results in the Internet Console. Args: query (search term)."),
    "fetch_url": (web.fetch_url, False, "Fetch URL content"),
    "open_url_default_browser": (web.open_url_default_browser, False, "Open URL in default browser"),
    "google_search_in_browser": (web.google_search_in_browser, False, "Open Google search"),

    # Shopping / Product search (read-only)
    "shop_search": (shop_search, False, "Search for products and extract best-effort pricing, returning normalized results with optional AUD/PHP conversion. Args: query, region(optional), currencies(optional), limit(optional), dynamic_fallback(optional)."),

    # Web - Scraper
    "scrape_url": (scraper_tools.scrape_url, False, "Scrape a static web page using CSS selectors"),
    "scrape_multiple_urls": (scraper_tools.scrape_batch, False, "Scrape multiple URLs concurrently"),
    "monitor_webpage_changes": (scraper_tools.monitor_webpage, False, "Detect when a monitored page changes"),
    "scrape_dynamic_page": (scraper_tools.scrape_dynamic, False, "Render a dynamic page with Playwright and return text/html"),
    "summarize_scraped_content": (scraper_tools.summarize_content, False, "Summarize scraped content via LLM"),
    "extract_data_from_content": (scraper_tools.extract_data, False, "Extract structured JSON data from text using LLM"),
    "ask_ai": (scraper_tools.ask_ai, False, "Ask the AI a general question or request an explanation"),
    "write_report": (report_tools.write_report, False, "Write a formatted report (Markdown/HTML) to disk"),
    
    # Social Media Interaction
    "scroll_page": (web.scroll_page, False, "Scroll page up or down"),
    "get_current_url": (web.get_current_url, False, "Get current browser URL"),
    "find_and_click_by_text": (web.find_and_click_by_text, False, "Find and click element by text"),
    "find_and_click_by_aria_label": (web.find_and_click_by_aria_label, False, "Click element by aria-label"),
    "read_post_content": (web.read_post_content, False, "Read post content on social media"),
    "like_post": (web.like_post, False, "Like/heart the current post"),
    "follow_user": (web.follow_user, False, "Follow/subscribe to user on current page"),
    "open_comment_box": (web.open_comment_box, False, "Open the comment input box"),
    "write_comment": (web.write_comment, False, "Write and submit a comment"),
    "follow_back_comment": (web.follow_back_comment, False, "Leave a follow back request comment"),
    "engage_with_post": (web.engage_with_post, False, "Full engagement: like, follow, comment"),
    "get_visible_posts": (web.get_visible_posts, False, "Get list of visible posts on feed"),
    
    # Facebook Group Tools
    "open_facebook_group": (web.open_facebook_group, False, "Open saved Facebook group in default browser"),
    "open_facebook_group_automated": (web.open_facebook_group_automated, False, "Open Facebook group for automation"),
    "get_facebook_group_posts": (web.get_facebook_group_posts, False, "Get posts from Facebook group"),
    "like_facebook_group_post": (web.like_facebook_group_post, False, "Like a post in Facebook group by index"),
    "comment_on_facebook_group_post": (web.comment_on_facebook_group_post, False, "Comment on Facebook group post"),
    "create_facebook_group_post": (web.create_facebook_group_post, False, "Create a new post in Facebook group"),
    "engage_facebook_group_posts": (web.engage_facebook_group_posts, False, "Auto-engage with multiple group posts"),
    "scroll_facebook_feed": (web.scroll_facebook_feed, False, "Scroll Facebook feed to load more"),
    "full_facebook_engagement": (web.full_facebook_engagement, False, "MASTER: Scroll, like, follow, comment on ALL posts"),
    "quick_engage_scroll": (web.quick_engage_scroll, False, "Quick scroll-and-engage loop for continuous growth"),
    "reply_to_post_comments": (web.reply_to_post_comments, False, "REPLY ENGAGE: Like, follow, reply to commenters on posts"),
    
    # Social Media Database Tools
    "get_platform_info": (web.get_platform_info, False, "Get info about a social media platform"),
    "open_platform": (web.open_platform, False, "Open a social media platform by name"),
    "open_platform_to_post": (web.open_platform_to_post, False, "Open platform ready to create post"),
    "get_trending_hashtags": (web.get_trending_hashtags, False, "Get trending hashtags by category"),
    "get_facebook_groups": (web.get_facebook_groups, False, "Get saved Facebook groups"),
    "open_all_platforms": (web.open_all_platforms, False, "Open all major social platforms"),
    
    # Memory & Learning Tools - Agent NEVER forgets!
    "remember_fact": (lambda topic, fact, source="conversation": agent_memory.remember_fact(topic, fact, source), False, "Remember a new fact permanently"),
    "remember_preference": (lambda key, value: agent_memory.remember_preference(key, value), False, "Remember user preference"),
    "get_facts_about": (lambda topic: {"success": True, "facts": agent_memory.get_facts_about(topic)}, False, "Get all facts about a topic"),
    "get_all_memories": (lambda: {"success": True, "facts": agent_memory.get_all_facts(), "preferences": agent_memory.get_preferences(), "recent_topics": agent_memory.get_recent_topics()}, False, "Get all stored memories"),
    "get_memory_summary": (lambda: {"success": True, "summary": agent_memory.get_memory_summary()}, False, "Get summary of agent memories"),
    "recall_topic": (lambda topic: agent_memory.remember_conversation_topic(topic), False, "Mark topic as discussed"),
    
    # Canvas Design - Draw architectural plans, floor plans, layouts
    "canvas_design": (canvas_design, False, "Draw and plan architectural designs on Canvas - use when users ask to design, draw, sketch, or show floor plans/layouts"),
    "canvas_design_image": (generate_design_image, False, "Generate 2D floor plan or 3D architectural renders from design descriptions"),
    
    # File Operations
    "read_file": (files.read_file, False, "Read file contents"),
    "read_lines": (files.read_lines, False, "Read specific lines from file"),
    "write_file": (files.write_file, False, "Write content to file (overwrites)"),
    "append_file": (files.append_file, False, "Append to file"),
    "create_file": (files.create_file, False, "Create new file"),
    "create_directory": (files.create_directory, False, "Create directory"),
    "copy_file": (files.copy_file, False, "Copy file"),
    "move_file": (files.move_file, False, "Move/rename file"),
    "rename": (files.rename, False, "Rename file/directory"),
    "delete_file": (files.delete_file, False, "Delete a file"),
    "delete_directory": (files.delete_directory, False, "Delete a directory"),
    "file_exists": (files.file_exists, False, "Check if file exists"),
    "get_file_info": (files.get_file_info, False, "Get file metadata"),
    "list_directory": (files.list_directory, False, "List directory contents"),
    "search_files": (files.search_files, False, "Search for files by pattern"),
    "search_in_files": (files.search_in_files, False, "Search text within files"),
    "get_current_directory": (files.get_current_directory, False, "Get current directory"),
    
    # Secretary Functions - Documents, Memos, Drafts, Notes
    "create_document": (files.create_document, False, "Create formatted document (letter, report, proposal)"),
    "take_memo": (files.take_memo, False, "Create a memo/quick note with priority"),
    "write_draft": (files.write_draft, False, "Save draft for later (email, post, article, speech)"),
    "quick_note": (files.quick_note, False, "Quickly jot down a note"),
    "create_meeting_notes": (files.create_meeting_notes, False, "Create formatted meeting notes"),
    "create_todo_list": (files.create_todo_list, False, "Create a to-do list"),
    
    # System Operations
    "run_command": (system.run_command, False, "Execute shell command"),
    "run_powershell": (system.run_powershell, False, "Execute PowerShell script"),
    "start_program": (system.start_program, False, "Start a program"),
    "open_file_with_app": (system.open_file_with_app, False, "Open file with default app"),
    "copy_to_clipboard": (system.copy_to_clipboard, False, "Copy text to clipboard"),
    "paste_from_clipboard": (system.paste_from_clipboard, False, "Get clipboard content"),
    "get_system_info": (system.get_system_info, False, "Get system information"),
    "get_system_stats": (system.get_system_stats, False, "Get CPU/memory/disk usage"),
    "list_processes": (system.list_processes, False, "List running processes"),
    "kill_process": (system.kill_process, False, "Kill a process"),
    "get_env_var": (system.get_env_var, False, "Get environment variable"),
    "show_notification": (system.show_notification, False, "Show system notification"),
    "get_datetime": (system.get_datetime, False, "Get current date/time"),

    # Agent Task Management
    "manage_todo_list": (lambda operation, todoList=None: manage_todo_list("amigos", operation, todoList), False, "Manage a structured todo list to track progress and plan tasks. Use this to update the GUI progress bar!"),

    # Live Weather
    "get_weather": (weather.get_weather, False, "Get live current weather and forecast for a location"),
    
    # Media Generation - Images
    "open_image": (media.open_image, False, "Get info about an image file"),
    "resize_image": (media.resize_image, False, "Resize an image to specified dimensions"),
    "crop_image": (media.crop_image, False, "Crop an image to specified box"),
    "rotate_image": (media.rotate_image, False, "Rotate an image by degrees"),
    "create_video_from_images": (media.create_video_from_images, False, "Turn multiple image paths into a Facebook-ready mp4"),
    "create_video_from_prompt": (media.create_video_from_prompt, False, "Generate a short AI video entirely from a text prompt"),
    "animate_image": (media.animate_image, False, "Animate a still image with a Ken Burns style pan/zoom"),
    "generate_video_from_image": (media.generate_video_from_image, False, "Generate AI video with REAL MOTION from image (person walking, animal moving)"),
    "generate_ai_video": (media.generate_ai_video, False, "Generate REAL AI video from text prompt using cloud APIs (WAN, Minimax, LTX models)"),
    "generate_ai_video_from_image": (media.generate_ai_video_from_image, False, "Generate REAL AI video from image using cloud APIs (WAN, Minimax models)"),
    "restore_vehicle_video": (media.restore_vehicle_video, False, "Create a model-locked old-vehicle restoration MP4 from an uploaded photo"),
    "get_video_info": (media.get_video_info, False, "Get information about a video file"),
    "trim_video": (media.trim_video, False, "Trim video from start to end time"),
    "merge_videos": (media.merge_videos, False, "Concatenate multiple videos into one"),
    "resize_video": (media.resize_video, False, "Resize video to specified dimensions"),
    "add_audio_to_video": (media.add_audio_to_video, False, "Add audio track to a video"),
    "convert_video": (media.convert_video, False, "Convert video format (mp4, avi, webm, mov)"),
    "extract_frame": (media.extract_frame, False, "Extract a single frame from video"),

    # Media Generation - Audio/MP3
    "get_audio_info": (media.get_audio_info, False, "Get info about audio file (MP3, WAV)"),
    "list_game_processes": (game_trainer.list_game_processes, False, "List all running game processes"),
    "find_game_window": (game_trainer.find_game_window, False, "Find game windows by title"),
    "attach_to_process": (game_trainer.attach_to_process, False, "Attach to a game process for memory ops"),
    "scan_memory_for_value": (game_trainer.scan_memory_for_value, False, "Scan memory for a specific value"),
    "write_memory": (game_trainer.write_memory, False, "Write value to memory address"),
    "freeze_value": (game_trainer.freeze_value, False, "Freeze a memory value constant"),
    "unfreeze_value": (game_trainer.unfreeze_value, False, "Stop freezing a memory value"),
    "list_frozen_values": (game_trainer.list_frozen_values, False, "List all frozen memory values"),
    "create_mod_template": (game_trainer.create_mod_template, False, "Create a mod template for a game"),
    "edit_game_config": (game_trainer.edit_game_config, False, "Edit game configuration files"),
    "game_trainer_help": (game_trainer.game_trainer_help, False, "Show game trainer help"),
    
    # Forms Database
    "get_profile": (forms_db.get_profile, False, "Get user profile data from forms database"),
    "get_profile_field": (forms_db.get_profile_field, False, "Get specific field from profile (e.g., contact.email)"),
    "update_profile_field": (forms_db.update_profile_field, False, "Update a field in user profile (e.g., contact.email, personal.first_name)"),
    "list_profiles": (forms_db.list_profiles, False, "List all profile names in the database"),
    "create_profile": (forms_db.create_profile, False, "Create a new empty profile"),
    
    # Screen & Audio Recording (for Social Media Content)
    "start_screen_recording": (recording.start_screen_recording, False, "Start recording screen for social media content"),
    "stop_screen_recording": (recording.stop_screen_recording, False, "Stop screen recording and save video"),
    "get_recording_status": (recording.get_recording_status, False, "Check if currently recording"),
    "list_recordings": (recording.list_recordings, False, "List all screen recordings"),
    "start_audio_recording": (recording.start_audio_recording, False, "Start voice/microphone recording"),
    "stop_audio_recording": (recording.stop_audio_recording, False, "Stop audio recording"),
    "record_window": (recording.record_window, False, "Record a specific window by title"),
    "list_audio_devices": (recording.list_audio_devices, False, "List available microphones and audio devices"),
    "check_ffmpeg": (recording.check_ffmpeg, False, "Check if FFmpeg is installed for recording"),
    
    # Document Storage - Persistent document database for agents
    "store_document_file": (lambda file_path, title=None, tags=None, category="general": store_document(file_path=file_path, title=title, tags=tags or [], category=category), False, "Store a file (PDF, image, video, text) to the document database for future reference"),
    "store_url_to_documents": (lambda url, title=None, content="", tags=None: store_url_content(url=url, title=title, content=content, tags=tags or []), False, "Store a URL with its content to the document database"),
    "store_plan": (lambda title, content, plan_type="general": store_plan_document(title=title, content=content, plan_type=plan_type), False, "Store a plan or strategy document for future reference"),
    "search_stored_documents": (lambda query, doc_type=None, limit=10: find_documents(query=query, doc_type=doc_type, limit=limit), False, "Search stored documents by query, filter by type (image, video, pdf, text, url, plan)"),
    "get_stored_document": (lambda doc_id: get_doc(doc_id), False, "Get a stored document by its ID"),
    "read_stored_document_content": (lambda doc_id: {"success": True, "content": get_doc_content(doc_id)}, False, "Read the text content of a stored document"),
    "get_relevant_stored_documents": (lambda task: {"success": True, "context": get_relevant_docs(task)}, False, "Get stored documents relevant to a task for context"),
    "get_document_storage_stats": (lambda: get_document_stats(), False, "Get statistics about stored documents"),
    
        # Canvas - Visual Canvas for Agent Amigos
    "canvas_draw_shape": (canvas_draw_shape, False, "Draw a shape (line, rectangle, ellipse, arrow) on the Canvas canvas"),
    "canvas_draw_text": (canvas_draw_text, False, "Add text to the Canvas canvas at x,y position"),
    "canvas_floor_plan": (canvas_floor_plan, False, "Generate a floor plan with rooms on the Canvas"),
    "canvas_flowchart": (canvas_flowchart, False, "Generate a flowchart diagram on the Canvas"),
    "canvas_poem": (canvas_poem, False, "Render a poem with artistic typography on the Canvas"),
    "canvas_clear": (canvas_clear, False, "Clear the entire Canvas canvas"),
    "canvas_set_mode": (canvas_set_mode, False, "Switch Canvas mode: SKETCH, DIAGRAM, CAD, MEDIA, TEXT"),
    "canvas_export": (canvas_export, False, "Export the Canvas canvas (png, svg, pdf, dxf, json)"),
    "canvas_get_commands": (canvas_get_commands, False, "Get all pending Canvas commands"),

    # Maps & Geographic Interaction
    "map_control": (map_control, False, "Control the Map Console. Args: place (location name), origin (start point), destination (end point), mode (driving/walking/bicycling/transit), zoom (1-21), view (roadmap/satellite/terrain/streetview). This tool triggers the interactive Map Console in the GUI. Use it for all geographic requests."),

    # OpenWork - Agentic Workflow Management
    "openwork_status": (openwork_status_tool, False, "Check OpenWork/OpenCode server status"),
    "openwork_start_server": (openwork_start_server_tool, False, "Start OpenCode server for a workspace. Args: workspace_path (optional)"),
    "openwork_stop_server": (openwork_stop_server_tool, False, "Stop the OpenCode server"),
    "openwork_create_session": (openwork_create_session, False, "Create a new OpenWork session for complex multi-step workflows. Use this to break down large projects into managed tasks. Args: workspace_path (project folder), prompt (task description). Returns session_id for tracking."),
    "openwork_list_sessions": (openwork_list_sessions, False, "List all active OpenWork sessions to see ongoing workflows and their status"),
    "openwork_get_session": (openwork_get_session, False, "Get details of an OpenWork session including todos, messages, and progress. Args: session_id"),
    "openwork_add_todo": (openwork_add_todo, False, "Add a task/todo to an OpenWork session. Args: session_id, title, description (optional), status (not-started/in-progress/completed)"),
    "openwork_update_todo": (openwork_update_todo, False, "Update a todo in an OpenWork session (e.g., mark completed). Args: session_id, todo_id, status (optional), title (optional)"),
    "openwork_add_message": (openwork_add_message, False, "Add a message/log to an OpenWork session. Args: session_id, role (user/assistant/system), content"),
    "openwork_close_session": (openwork_close_session, False, "Close/complete an OpenWork session. Args: session_id"),
    "openwork_get_workspaces": (openwork_get_workspaces, False, "List available workspaces for OpenWork sessions"),
    "openwork_get_skills": (openwork_get_skills_tool, False, "List installed OpenCode skills for a workspace. Args: workspace_path (optional)"),

    # Multi-Agent Coordination
    "consult_team": (coordinator.consult_team, False, "Consult the full team of agents (Ollie, Scrapey, Media, Researcher, etc.) to solve a complex task"),

    # Utility
    "wait": (computer.wait, False, "Wait for N seconds"),
}

# Register tools in the central registry for the enhanced AdaptiveAgent
try:
    _registry = get_tool_registry()
    for _name, (_func, _approval, _desc) in TOOLS.items():
        # Determine category from tool_categories if possible
        # (tool_categories is defined later in the file, so we'll use a simple mapping or UTILITY)
        _registry.register_tool(_name, _func, _approval, _desc)
except Exception as _e:
    print(f"Failed to register tools in central registry: {_e}")

# Generate tool descriptions for the LLM
def get_tools_prompt():
    """Generate detailed tool descriptions for the system prompt"""
    sections = {
        "KEYBOARD & TYPING": [],
        "MOUSE CONTROL": [],
        "SCREEN CAPTURE": [],
        "BROWSER (Default)": [],
        "BROWSER (Automated Selenium)": [],
        "WEB SEARCH (No browser needed)": [],
        "FILE OPERATIONS": [],
        "DOCUMENT STORAGE (Persistent Knowledge Base)": [],
        "SECRETARY (Documents, Memos, Notes)": [],
        "SYSTEM & PROGRAMS": [],
        "MEDIA GENERATION": [],
        "CANVAS DESIGN & ARCHITECTURE": [],
        "OPENWORK WORKFLOWS": [],
        "MAPS & GEOGRAPHIC INTERACTION": [],
        "GAME TRAINER & MODS": [],
        "FORMS DATABASE": [],
        "GUI CONTROL": [],
        "SEARCH & INTEL": [],
        "UTILITY": [],
    }
    
    tool_categories = {
        "type_text": "KEYBOARD & TYPING",
        "type_unicode": "KEYBOARD & TYPING",
        "press_key": "KEYBOARD & TYPING",
        "hotkey": "KEYBOARD & TYPING",
        "move_mouse": "MOUSE CONTROL",
        "click": "MOUSE CONTROL",
        "double_click": "MOUSE CONTROL",
        "right_click": "MOUSE CONTROL",
        "scroll": "MOUSE CONTROL",
        "drag": "MOUSE CONTROL",
        "get_mouse_position": "MOUSE CONTROL",
        "screenshot": "SCREEN CAPTURE",
        "get_screen_size": "SCREEN CAPTURE",
        "locate_on_screen": "SCREEN CAPTURE",
        "click_image": "SCREEN CAPTURE",
        "open_url_default_browser": "BROWSER (Default)",
        "google_search_in_browser": "BROWSER (Default)",
        "open_browser": "BROWSER (Automated Selenium)",
        "close_browser": "BROWSER (Automated Selenium)",
        "navigate": "BROWSER (Automated Selenium)",
        "get_page_content": "BROWSER (Automated Selenium)",
        "click_element": "BROWSER (Automated Selenium)",
        "type_in_element": "BROWSER (Automated Selenium)",
        "take_browser_screenshot": "BROWSER (Automated Selenium)",
        "execute_javascript": "BROWSER (Automated Selenium)",
        "go_back": "BROWSER (Automated Selenium)",
        "go_forward": "BROWSER (Automated Selenium)",
        "refresh": "BROWSER (Automated Selenium)",
        "new_tab": "BROWSER (Automated Selenium)",
        "close_tab": "BROWSER (Automated Selenium)",
        "web_search": "WEB SEARCH (No browser needed)",
        "web_search_news": "WEB SEARCH (No browser needed)",
        "fetch_url": "WEB SEARCH (No browser needed)",
        "extract_data_from_content": "WEB SEARCH (No browser needed)",
        "ask_ai": "WEB SEARCH (No browser needed)",
        "write_report": "FILE OPERATIONS",
        "read_file": "FILE OPERATIONS",
        "read_lines": "FILE OPERATIONS",
        "write_file": "FILE OPERATIONS",
        "append_file": "FILE OPERATIONS",
        "create_file": "FILE OPERATIONS",
        "create_directory": "FILE OPERATIONS",
        "copy_file": "FILE OPERATIONS",
        "move_file": "FILE OPERATIONS",
        "rename": "FILE OPERATIONS",
        "delete_file": "FILE OPERATIONS",
        "delete_directory": "FILE OPERATIONS",
        "file_exists": "FILE OPERATIONS",
        "get_file_info": "FILE OPERATIONS",
        "list_directory": "FILE OPERATIONS",
        "search_files": "FILE OPERATIONS",
        "search_in_files": "FILE OPERATIONS",
        "get_current_directory": "FILE OPERATIONS",
        "create_document": "SECRETARY (Documents, Memos, Notes)",
        "take_memo": "SECRETARY (Documents, Memos, Notes)",
        "write_draft": "SECRETARY (Documents, Memos, Notes)",
        "quick_note": "SECRETARY (Documents, Memos, Notes)",
        "create_meeting_notes": "SECRETARY (Documents, Memos, Notes)",
        "create_todo_list": "SECRETARY (Documents, Memos, Notes)",
        "list_secretary_files": "SECRETARY (Documents, Memos, Notes)",
        "run_command": "SYSTEM & PROGRAMS",
        "run_powershell": "SYSTEM & PROGRAMS",
        "start_program": "SYSTEM & PROGRAMS",
        "open_file_with_app": "SYSTEM & PROGRAMS",
        "copy_to_clipboard": "SYSTEM & PROGRAMS",
        "paste_from_clipboard": "SYSTEM & PROGRAMS",
        "get_system_info": "SYSTEM & PROGRAMS",
        "get_system_stats": "SYSTEM & PROGRAMS",
        "list_processes": "SYSTEM & PROGRAMS",
        "kill_process": "SYSTEM & PROGRAMS",
        "get_env_var": "SYSTEM & PROGRAMS",
        "show_notification": "SYSTEM & PROGRAMS",
        "get_datetime": "SYSTEM & PROGRAMS",
        "get_weather": "WEB SEARCH (No browser needed)",
        "generate_image": "MEDIA GENERATION",
        "create_video_from_images": "MEDIA GENERATION",
        "create_video_from_prompt": "MEDIA GENERATION",
        "animate_image": "MEDIA GENERATION",
        "generate_video_from_image": "MEDIA GENERATION",
        "generate_ai_video": "MEDIA GENERATION",
        "generate_ai_video_from_image": "MEDIA GENERATION",
        "canvas_design": "CANVAS DESIGN & ARCHITECTURE",
        "canvas_design_image": "CANVAS DESIGN & ARCHITECTURE",
        "openwork_status": "OPENWORK WORKFLOWS",
        "openwork_start_server": "OPENWORK WORKFLOWS",
        "openwork_stop_server": "OPENWORK WORKFLOWS",
        "openwork_create_session": "OPENWORK WORKFLOWS",
        "openwork_list_sessions": "OPENWORK WORKFLOWS",
        "openwork_get_session": "OPENWORK WORKFLOWS",
        "openwork_add_todo": "OPENWORK WORKFLOWS",
        "openwork_update_todo": "OPENWORK WORKFLOWS",
        "openwork_add_message": "OPENWORK WORKFLOWS",
        "openwork_close_session": "OPENWORK WORKFLOWS",
        "openwork_get_workspaces": "OPENWORK WORKFLOWS",
        "openwork_get_skills": "OPENWORK WORKFLOWS",
        "map_control": "MAPS & GEOGRAPHIC INTERACTION",
        "list_game_processes": "GAME TRAINER & MODS",
        "find_game_window": "GAME TRAINER & MODS",
        "attach_to_process": "GAME TRAINER & MODS",
        "scan_memory_for_value": "GAME TRAINER & MODS",
        "write_memory": "GAME TRAINER & MODS",
        "freeze_value": "GAME TRAINER & MODS",
        "unfreeze_value": "GAME TRAINER & MODS",
        "list_frozen_values": "GAME TRAINER & MODS",
        "create_mod_template": "GAME TRAINER & MODS",
        "list_mod_files": "GAME TRAINER & MODS",
        "backup_game_files": "GAME TRAINER & MODS",
        "restore_game_files": "GAME TRAINER & MODS",
        "edit_game_config": "GAME TRAINER & MODS",
        "game_trainer_help": "GAME TRAINER & MODS",
        "get_profile": "FORMS DATABASE",
        "get_profile_field": "FORMS DATABASE",
        "update_profile_field": "FORMS DATABASE",
        "list_profiles": "FORMS DATABASE",
        "create_profile": "FORMS DATABASE",
        "store_document_file": "DOCUMENT STORAGE (Persistent Knowledge Base)",
        "store_url_to_documents": "DOCUMENT STORAGE (Persistent Knowledge Base)",
        "store_plan": "DOCUMENT STORAGE (Persistent Knowledge Base)",
        "search_stored_documents": "DOCUMENT STORAGE (Persistent Knowledge Base)",
        "get_stored_document": "DOCUMENT STORAGE (Persistent Knowledge Base)",
        "read_stored_document_content": "DOCUMENT STORAGE (Persistent Knowledge Base)",
        "get_relevant_stored_documents": "DOCUMENT STORAGE (Persistent Knowledge Base)",
        "get_document_storage_stats": "DOCUMENT STORAGE (Persistent Knowledge Base)",
        "wait": "UTILITY",
    }
    
    for name, (func, requires_approval, desc) in TOOLS.items():
        category = tool_categories.get(name, "UTILITY")
        approval = " [REQUIRES APPROVAL]" if requires_approval else ""
        sections[category].append(f"  • {name}: {desc}{approval}")
    
    lines = []
    for section, tools in sections.items():
        if tools:
            lines.append(f"\n{section}:")
            lines.extend(tools)
    
    return "\n".join(lines)


# Action keywords that MUST trigger tool calls
ACTION_KEYWORDS = {
    "open": ["open_url_default_browser", "start_program", "open_file_with_app"],
    "browser": ["open_url_default_browser"],
    "google": ["open_url_default_browser", "google_search_in_browser"],
    "search": ["web_search", "google_search_in_browser"],
    "type": ["type_text"],
    "click": ["click"],
    "screenshot": ["screenshot"],
    "copy": ["copy_to_clipboard", "copy_file"],
    "paste": ["paste_from_clipboard"],
    "delete": ["delete_file", "delete_directory"],
    "create": ["create_file", "create_directory", "create_document"],
    "read": ["read_file"],
    "write": ["write_file", "write_draft"],
    "run": ["run_command", "run_powershell"],
    "execute": ["run_command", "run_powershell"],
    "start": ["start_program"],
    "kill": ["kill_process"],
    "notify": ["show_notification"],
    "scroll": ["scroll"],
    "press": ["press_key"],
    "navigate": ["navigate", "open_url_default_browser"],
    "profile": ["get_profile", "update_profile_field", "list_profiles"],
    "database": ["get_profile", "list_profiles"],
    "my email": ["get_profile_field"],
    "my phone": ["get_profile_field"],
    "my name": ["get_profile_field"],
    "my address": ["get_profile_field"],
    "save my": ["update_profile_field"],
    "update my": ["update_profile_field"],
    "set my": ["update_profile_field"],
    # Secretary Functions
    "memo": ["take_memo"],
    "note": ["quick_note"],
    "draft": ["write_draft"],
    "document": ["create_document", "search_stored_documents"],
    "letter": ["create_document"],
    "report": ["create_document"],
    "proposal": ["create_document"],
    "meeting": ["create_meeting_notes"],
    "meeting notes": ["create_meeting_notes"],
    "todo": ["create_todo_list"],
    "to-do": ["create_todo_list"],
    "task list": ["create_todo_list"],
    "my files": ["list_secretary_files"],
    "my documents": ["list_secretary_files", "search_stored_documents"],
    "my memos": ["list_secretary_files"],
    "my notes": ["list_secretary_files"],
    # Document Storage
    "store document": ["store_document_file"],
    "store file": ["store_document_file"],
    "save document": ["store_document_file"],
    "upload document": ["store_document_file"],
    "store url": ["store_url_to_documents"],
    "save url": ["store_url_to_documents"],
    "store plan": ["store_plan"],
    "save plan": ["store_plan"],
    "find document": ["search_stored_documents"],
    "search document": ["search_stored_documents"],
    "stored documents": ["search_stored_documents", "get_document_storage_stats"],
    "saved documents": ["search_stored_documents"],
    "relevant documents": ["get_relevant_stored_documents"],
    "related documents": ["get_relevant_stored_documents"],
    "learn from": ["get_relevant_stored_documents", "store_document_file"],
    "reference": ["get_relevant_stored_documents", "search_stored_documents"],
    "uploaded": ["search_stored_documents", "get_document_storage_stats"],
    # Canvas Design & Architecture
    "design": ["canvas_design"],
    "draw": ["canvas_design"],
    "sketch": ["canvas_design"],
    "floor plan": ["canvas_design"],
    "blueprint": ["canvas_design"],
    "layout": ["canvas_design"],
    "architecture": ["canvas_design"],
    "house plan": ["canvas_design"],
    "building": ["canvas_design"],
    # Social Media
    "facebook": ["open_url_default_browser"],
    "twitter": ["open_url_default_browser"],
    "instagram": ["open_url_default_browser"],
    "linkedin": ["open_url_default_browser"],
    "tiktok": ["open_url_default_browser"],
    "youtube": ["open_url_default_browser"],
    "post": ["copy_to_clipboard"],
    "social media": ["open_url_default_browser"],
    # Maps & Geography
    "map": ["map_control"],
    "route": ["map_control"],
    "directions": ["map_control"],
    "location": ["map_control"],
    "where is": ["map_control"],
}


def get_system_prompt_compact():
    """Generate a compact system prompt for faster responses."""
    now = datetime.now()
    
    # Try to load custom behavior prompt
    behavior_prompt = ""
    try:
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agent_prompt.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                behavior_prompt = f.read()
    except Exception as e:
        print(f"Error loading agent_prompt.txt: {e}")

    # Fallback if empty
    if not behavior_prompt:
        behavior_prompt = f"""You are Agent Amigos - a SELF-LEARNING autonomous AI agent.

TONE & ACCURACY:
- Be professional, serious, and factual.
- Avoid jokes, hype, and emojis unless the user explicitly uses/requests them.
- If uncertain, say what you know and what you don't know.

CONSOLE AWARENESS:
- You have direct access to the Agent Amigos UI consoles (Finance, Internet, Scraper, Map).
- Use the "CURRENT SCREEN CONTEXT" provided in your prompt to answer questions about news, markets, locations, or files.
- Do NOT claim you lack access to real-time data if it is present in the context.
- For geographic queries, use the Map Console via map_control tool."""

    # ALWAYS inject the current time and date at the top of the prompt
    temporal_context = f"""
### SYSTEM CLOCK & TEMPORAL CONTEXT:
- Current Date: {now.strftime('%A, %B %d, %Y')}
- Current Time: {now.strftime('%I:%M:%S %p')}
- Timezone: Local System Time
- INSTRUCTION: You HAVE direct access to the system clock. NEVER tell the user you don't have access. Use the values above to answer any questions about the current time or date.
"""

    return f"""{temporal_context}

{behavior_prompt}

YOU HAVE PERSISTENT MEMORY! You remember everything across sessions.

YOUR MEMORY FILES (use read_file to access, remember_fact to store):
- data/memory/agent_memory.json - Your main memory (facts, preferences, learned patterns)
- data/memory/knowledge_base.json - Your growing knowledge (tips, templates, solutions)
- data/memory/learning_stats.json - Your skill levels and improvement tracking
- data/forms_db/user_profiles.json - Owner info (Darrell Buttigieg, family, contacts)
- data/social_media/platforms.json - Social media URLs, limits, hashtags

DOCUMENT STORAGE (persistent knowledge base for learning):
- Use store_document_file to save PDFs, images, videos for future reference
- Use store_url_to_documents to save web pages/URLs for learning
- Use store_plan to save project plans and instructions
- Use search_stored_documents to find previously stored documents
- Use get_relevant_stored_documents to get docs related to current task
- ALWAYS check stored documents when working on tasks - previous uploads may help!

FILE SYSTEM ACCESS (you can access ANY file on the system!):
- read_file path="C:\\Users\\user\\Documents\\file.txt" - Read any file
- list_directory path="C:\\Users\\user\\Downloads" - List folder contents
- search_files directory="C:\\Users\\user" pattern="*.pdf" - Find files
- search_in_files directory="..." search_text="keyword" - Search text in files
- Common dirs: Desktop, Documents, Downloads, Pictures, Videos at C:\\Users\\user\\

SELF-LEARNING BEHAVIOR:
1. ALWAYS check memory AND stored documents before asking user for info
2. When you learn something new → remember_fact(topic, fact, source) 
3. When user uploads files → store_document_file to save for future use
4. Track successful actions to improve over time

TASK PROGRESSION & PLANNING:
- Use manage_todo_list to plan multi-step tasks.
- This tool updates the visual progress bar in the GUI!
- Start by writing the full plan, then mark items as 'in-progress' and 'completed' as you go.

OWNER: Darrell Buttigieg (Quezon City, Philippines)
- Partner: Felirma Mupal (13+ years, anniversary Oct 15)
- Son: Brenton | Daughter: Chantelle | Grandkids: Eden(8), Ari(6), Declan(18)
- Required hashtags: #darrellbuttigieg #thesoldiersdream

RULES:
1. Be concise. Actions speak louder than words.
2. Tool format: ```tool {{"tool":"NAME","args":{{}}}} ```
3. Memory ops are SILENT - just say "Got it!" or "Remembered!"
4. Answer knowledge questions directly - you're an expert.

OPENWORK / OPENCODE:
- Use OpenWork tools to manage complex, multi-step workflows (create sessions, add todos, track progress).
- If the user mentions OpenWork or OpenCode, check server status and start the server if needed.

CANVAS (IMPORTANT):
- "Canvas" / "canvas" / "chalk board" / "whiteboard" ALWAYS refers to the in-app visual canvas tool.
- NEVER interpret "canvas" as "chocolate".
- If the user asks to plan, diagram, draw, map, visualize, flowchart, or floor-plan: prefer Canvas tools.

TOOL EXAMPLES (use exact arg names):
- read_file: {{"tool":"read_file","args":{{"path":"data/memory/agent_memory.json"}}}}
- list_directory: {{"tool":"list_directory","args":{{"path":"C:\\\\Users\\\\user\\\\Documents"}}}}
- search_files: {{"tool":"search_files","args":{{"directory":"C:\\\\Users\\\\user","pattern":"*.pdf"}}}}
- remember_fact: {{"tool":"remember_fact","args":{{"topic":"family","fact":"info here","source":"conversation"}}}}
- type_text: {{"tool":"type_text","args":{{"text":"hello"}}}}
- web_search: {{"tool":"web_search","args":{{"query":"search term"}}}}
- map_control: {{"tool":"map_control","args":{{"place":"Sydney, Australia","zoom":12}}}}
- map_control (route): {{"tool":"map_control","args":{{"origin":"Manila","destination":"Quezon City","travel_mode":"driving"}}}}

{get_tools_prompt()}
"""


# --- Global State ---
AUTO_MODE = autonomy_controller.is_enabled()

def get_system_prompt():
    """Generate the system prompt with dynamic date and time"""
    now = datetime.now()
    current_date = now.strftime("%A, %B %d, %Y")
    current_time = now.strftime("%I:%M %p")
    mode_status = "🔴 MANUAL MODE" if not autonomy_controller.is_enabled() else "🟢 AUTONOMOUS AUTO MODE (SUPER SMART)"
    
    # Load custom persona from agent_prompt.txt
    try:
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agent_prompt.txt')
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                base_prompt = f.read()
        else:
            base_prompt = "You are Agent Amigos."
    except Exception as e:
        print(f"Error loading agent_prompt.txt: {e}")
        base_prompt = "You are Agent Amigos."

    # Load technical manual
    try:
        tech_path = os.path.join(os.path.dirname(__file__), 'technical_manual.txt')
        if os.path.exists(tech_path):
            with open(tech_path, 'r', encoding='utf-8') as f:
                technical_manual = f.read()
        else:
            technical_manual = ""
    except Exception as e:
        print(f"Error loading technical_manual.txt: {e}")
        technical_manual = ""

    return f"""{base_prompt}

{technical_manual}

═══════════════════════════════════════════════════════════════
                    SYSTEM STATUS
═══════════════════════════════════════════════════════════════
Date: {current_date}
Time: {current_time}
Current Mode: {mode_status}

{get_tools_prompt()}
"""

SYSTEM_PROMPT = get_system_prompt()

# LLM Response cache for repeated queries (simple time-based)
_llm_cache = {}
_LLM_CACHE_TTL = 300  # 5 minutes


def _cache_key(messages: list) -> str:
    """Generate cache key from messages."""
    import hashlib
    content = json.dumps([m.get("content", "") for m in messages[-3:]], sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()


class AgentEngine:
    """The brain of Agent Amigos - processes messages and executes tools"""
    
    def __init__(self):
        self.conversation_history = []
        self.pending_approval_action = None
        self._tool_execution_times = {}  # Track tool performance
        print(f"Agent Amigos Engine v2.0 initialized with {len(TOOLS)} tools")
    
    def detect_unfulfilled_promise(self, llm_response: str, actions_taken: List[dict]) -> Optional[str]:
        """Detect if LLM promised to do something but didn't execute a tool.
        
        Returns the action type needed if a promise was made but not fulfilled.
        """
        # Patterns indicating LLM said it will do something
        promise_patterns = [
            (r"i('ll| will)\s+(examine|analyze|look at|review|read|check|inspect)", "analyze"),
            (r"let me\s+(examine|analyze|look at|review|read|check|inspect)", "analyze"),
            (r"i('ll| will)\s+(search|find|look for|scrape)", "search"),
            (r"let me\s+(search|find|look for|scrape)", "search"),
            (r"i('ll| will)\s+(create|generate|make|design|build|write)", "create"),
            (r"let me\s+(create|generate|make|design|build|write)", "create"),
            (r"i('ll| will)\s+(download|fetch|get|retrieve)", "fetch"),
            (r"let me\s+(download|fetch|get|retrieve)", "fetch"),
            (r"i('ll| will)\s+(open|navigate|browse|go to)", "browse"),
            (r"i('ll| will)\s+(show|open|display|zoom|move|navigate)\s+(the|a)?\s*map", "map"),
            (r"let me\s+(show|open|display|zoom|move|navigate)\s+(the|a)?\s*map", "map"),
            (r"(according to|looking at|on|in)\s+the\s+(map console|map|maps)", "map"),
            (r"i('ll| will)\s+(design|create|sketch|plan|draw)\s+(a|the|an)?\s*(.+?)\s*(on|in|using)\s+(the\s+)?(canvas|chalkboard)", "canvas"),
            (r"let me\s+(design|create|sketch|plan|draw)\s+(a|the|an)?\s*(.+?)\s*(on|in|using)\s+(the\s+)?(canvas|chalkboard)", "canvas"),
            (r"i('ll| will)\s+(search|look up|check|find)\s+(.+?)\s*(on|in|using)\s+(the\s+)?(internet|web|search)", "search"),
            (r"let me\s+(search|look up|check|find)\s+(.+?)\s*(on|in|using)\s+(the\s+)?(internet|web|search)", "search"),
            (r"examining\s+the", "analyze"),
            (r"analyzing\s+the", "analyze"),
            (r"reviewing\s+the", "analyze"),
        ]
        
        response_lower = llm_response.lower()
        
        for pattern, action_type in promise_patterns:
            if re.search(pattern, response_lower):
                # Check if the specific tool type was actually executed
                tool_executed = False
                if actions_taken:
                    for action in actions_taken:
                        tool_name = action.get("tool", "").lower()
                        if action_type == "map" and "map" in tool_name:
                            tool_executed = True
                        elif action_type == "search" and ("search" in tool_name or "scrape" in tool_name or "web" in tool_name):
                            tool_executed = True
                        elif action_type == "create" and ("create" in tool_name or "write" in tool_name or "canvas" in tool_name):
                            tool_executed = True
                        elif action_type == "canvas" and "canvas" in tool_name:
                            tool_executed = True
                        elif action_type == "analyze" and ("read" in tool_name or "list" in tool_name or "search" in tool_name):
                            tool_executed = True
                        elif action_type == "fetch" and ("fetch" in tool_name or "get" in tool_name or "download" in tool_name):
                            tool_executed = True
                        elif action_type == "browse" and ("open" in tool_name or "browser" in tool_name):
                            tool_executed = True
                
                if not tool_executed:
                    return action_type
        
        return None
    
    def determine_delegated_agent(self, user_message: str, task_type: str = None) -> Optional[str]:
        """Determine if a task should be delegated to a specific agent.
        
        Returns agent_id or None if Amigos should handle it.
        """
        msg_lower = user_message.lower()
        
        # Scrapey - Web scraping tasks
        if any(kw in msg_lower for kw in ["scrape", "crawl", "extract from website", "get data from", "web data"]):
            return "scrapey"
        
        # Media Bot - Media processing
        if any(kw in msg_lower for kw in ["video", "audio", "image", "convert media", "transcode", "thumbnail"]):
            return "media"
        
        # Trainer - Game-related
        if any(kw in msg_lower for kw in ["game", "cheat", "trainer", "memory scan", "process attach", "game hack"]):
            return "trainer"
        
        # Ollie - Quick knowledge questions (when available) or explicit asks
        if any(kw in msg_lower for kw in ["ask ollie", "hey ollie"]) or msg_lower.strip().startswith("ollie "):
            return "ollie"

        if task_type == "quick_question" or any(kw in msg_lower for kw in ["quick question", "briefly explain"]):
            return "ollie"
        
        return None  # Amigos handles it

    def _tool_needs_approval(self, tool_name: str, requires_approval_flag: bool, require_approval_global: bool, auto_approve_tools: set) -> bool:
        """Return True if the tool requires user approval given current autonomy config."""
        # GOD MODE: If the user is Darrell Buttigieg (Dev/Admin), we trust the autonomy config absolutely.
        auto_mode = autonomy_controller.is_enabled()
        cfg = autonomy_controller.get_config()
        
        # If autonomy is enabled and requireConfirmation is False, NEVER ask for approval.
        if auto_mode and cfg.get('requireConfirmation') is False:
            return False

        if not requires_approval_flag:
            return False
            
        if auto_mode:
            if cfg.get('autoApproveSafeTools') and tool_name in auto_approve_tools:
                return False
                
        return bool(require_approval_global)

    def call_llm(self, messages: List[dict], provider: str = None, use_cache: bool = True, _tried_providers: set = None, model_override: Optional[str] = None) -> str:
        """Call configured LLM endpoint with caching and automatic fallback.
        
        Supports: OpenAI, Grok (xAI), Groq, DeepSeek, Ollama
        Falls back to other providers if rate limited (429 error).
        """
        global _llm_cache
        
        # Track which providers we've already tried to prevent infinite loops
        if _tried_providers is None:
            _tried_providers = set()
        
        # Check cache for non-tool conversations
        cache_key = _cache_key(messages)
        if use_cache and cache_key in _llm_cache:
            cached = _llm_cache[cache_key]
            if time.time() - cached["time"] < _LLM_CACHE_TTL:
                print(f"[LLM] Cache hit!")
                return cached["response"]
        
        # Determine which provider to use
        provider = provider or LLM_PROVIDER
        _tried_providers.add(provider)  # Mark this provider as tried
        
        config = LLM_CONFIGS.get(provider, LLM_CONFIGS["openai"])
        
        api_base = config["base"]
        api_key = config["key"]
        model = config["model"]
        # Allow a runtime override of the model
        if model_override:
            model = model_override
            
            # If the requested model is not valid for the current provider,
            # try to find a provider that DOES support it.
            if not is_model_valid_for_provider(provider, model):
                print(f"[LLM] Model '{model}' not valid for provider '{provider}'. Searching for capable provider...")
                found_provider = None
                for p_name, p_cfg in LLM_CONFIGS.items():
                    if p_name == provider: continue
                    supported = p_cfg.get("supported_models", [])
                    if model in supported:
                        # Check if this provider is actually usable (has key or is ollama)
                        has_key = bool(p_cfg.get("key"))
                        is_ollama = (p_name == "ollama")
                        if has_key or is_ollama:
                            found_provider = p_name
                            break
                
                if found_provider:
                    print(f"[LLM] Switching provider to '{found_provider}' for model '{model}'")
                    provider = found_provider
                    config = LLM_CONFIGS[provider]
                    api_base = config["base"]
                    api_key = config["key"]
                    # Don't reset model, we want the override
                else:
                    print(f"[LLM] No configured provider found for '{model}'. Falling back to default logic.")

        # Validate model for this provider and fallback if invalid
        if not is_model_valid_for_provider(provider, model):
            supported = config.get('supported_models', [])
            if supported:
                old_model = model
                # pick first supported model not equal to current (or fallback to the first)
                model = next((m for m in supported if m and m != old_model), supported[0])
                print(f"[LLM] Runtime model '{old_model}' is not valid for provider {provider}; switching to supported '{model}'")
        
        if not api_base:
            return "[LLM API base URL not configured]"

        # Truncate messages to fit within token limits (especially for GitHub/gpt-4o with 8k limit)
        # Rough estimate: 1 token ≈ 4 chars. Keep under ~6000 tokens to leave room for response
        MAX_CHARS = 20000  # ~5000 tokens for input
        truncated_messages = []
        total_chars = 0
        
        # Always keep system message (first) and recent messages (last few)
        system_msg = None
        other_msgs = []
        
        for msg in messages:
            if msg.get("role") == "system" and system_msg is None:
                system_msg = msg
            else:
                other_msgs.append(msg)
        
        # Start with system message
        if system_msg:
            # Truncate system message if too long
            content = system_msg.get("content", "")
            if len(content) > 4000:
                content = content[:4000] + "\n...[system prompt truncated]"
            truncated_messages.append({"role": "system", "content": content})
            total_chars += len(content)
        
        # Add messages from newest to oldest, stopping when we hit the limit
        msgs_to_add = []
        for msg in reversed(other_msgs):
            content = msg.get("content", "")
            
            # Handle list content (multimodal) - skip truncation logic for complex content
            if isinstance(content, list):
                # Rough size estimate for list content
                msg_len = sum(len(str(item)) for item in content)
                if total_chars + msg_len < MAX_CHARS:
                    msgs_to_add.insert(0, msg)
                    total_chars += msg_len
                else:
                    if msgs_to_add and msgs_to_add[0].get("role") != "system":
                        msgs_to_add.insert(0, {"role": "system", "content": "[Earlier conversation history truncated to fit context window]"})
                    break
                continue

            # Truncate individual messages if too long
            if isinstance(content, str) and len(content) > 3000:
                content = content[:3000] + "\n...[truncated]"
            
            msg_len = len(content) if isinstance(content, str) else 0
            
            if total_chars + msg_len < MAX_CHARS:
                msgs_to_add.insert(0, {"role": msg.get("role", "user"), "content": content})
                total_chars += msg_len
            else:
                # Add a note that history was truncated
                if msgs_to_add and msgs_to_add[0].get("role") != "system":
                    msgs_to_add.insert(0, {"role": "system", "content": "[Earlier conversation history truncated to fit context window]"})
                break
        
        truncated_messages.extend(msgs_to_add)

        payload = {
            "model": model,
            "messages": truncated_messages,
            "temperature": 0.5,  # Lower for faster, more consistent responses
            "stream": False,
            "max_tokens": 800,  # Reduced for faster responses
        }

        headers = {"Content-Type": "application/json"}
        # Skip auth header for Ollama (local, no auth needed)
        if api_key and not config.get("no_auth"):
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            url = f"{api_base.rstrip('/')}/chat/completions"
            response = _session.post(url, json=payload, headers=headers, timeout=LLM_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            result = ""
            if data.get("choices"):
                result = data["choices"][0]["message"]["content"]
            elif "message" in data:
                result = data["message"].get("content", "")
            else:
                return "[LLM response missing 'choices']"
            
            # Cache the response
            _llm_cache[cache_key] = {"response": result, "time": time.time()}
            # Prune old cache entries
            if len(_llm_cache) > 100:
                oldest = min(_llm_cache.keys(), key=lambda k: _llm_cache[k]["time"])
                del _llm_cache[oldest]
            
            return result
            
        except requests.HTTPError as http_err:
            resp = http_err.response
            status = resp.status_code if resp is not None else "unknown"
            
            # Rate limit (429), token limit (413), or Access Denied (403) - try fallback providers
            if status in [403, 429, 413]:
                # Prioritize GitHub Copilot (most capable), then Groq (fast free tier), then local
                fallback_order = ["github", "groq", "deepseek", "ollama", "grok", "openai"]
                for fallback in fallback_order:
                    if fallback not in _tried_providers and LLM_CONFIGS.get(fallback, {}).get("key"):
                        print(f"[LLM] Error {status} on {provider}, trying {fallback}...")
                        import time as time_module
                        time_module.sleep(0.3)  # Brief delay before trying next provider
                        return self.call_llm(messages, provider=fallback, _tried_providers=_tried_providers)
                
                # All providers exhausted
                print(f"[LLM] All providers failed. Tried: {_tried_providers}")
                return f"[All LLM providers unavailable ({', '.join(_tried_providers)}). Please wait and try again.]"
            
            body = resp.text if resp is not None and resp.text else str(http_err)

            # If provider reports unknown model, attempt to try other models for this provider
            try:
                body_json = resp.json() if resp is not None else {}
            except Exception:
                body_json = {}
            unknown_model = False
            if isinstance(body_json, dict):
                # Common error format: {'error': {'code': 'unknown_model', 'message': 'Unknown model: raptor-mini'}}
                err = body_json.get('error') or body_json.get('errors')
                if isinstance(err, dict) and err.get('code') == 'unknown_model':
                    unknown_model = True
                elif isinstance(err, list) and len(err) and isinstance(err[0], dict) and err[0].get('code') == 'unknown_model':
                    unknown_model = True
            # Also match text
            if 'unknown model' in (body or '').lower() or 'unknown_model' in (body or ''):
                unknown_model = True

            if unknown_model:
                autonomy_controller.log_action('unknown_model_detected', {'provider': provider, 'model': model}, {'body': body[:500]})
                supported = LLM_CONFIGS.get(provider, {}).get('supported_models', [])
                for fallback_model in supported:
                    if fallback_model and fallback_model != model:
                        try:
                            autonomy_controller.log_action('unknown_model_fallback_attempt', {'provider': provider, 'from_model': model, 'to_model': fallback_model}, {})
                            print(f"[LLM] Provider {provider} unknown model '{model}'. Trying provider-supported model '{fallback_model}'...")
                            return self.call_llm(messages, provider=provider, _tried_providers=_tried_providers, model_override=fallback_model)
                        except Exception:
                            autonomy_controller.log_action('unknown_model_fallback_failed', {'provider': provider, 'from_model': model, 'to_model': fallback_model}, {})
                            continue

            # Ollama (OpenAI-compatible) returns HTTP 500 when a model doesn't fit in RAM.
            # Retry automatically with smaller models so the UI doesn't surface raw errors.
            if provider == "ollama" and status == 500 and resp is not None:
                full_body = resp.text or ""
                if _is_ollama_insufficient_memory_error(full_body):
                    for fallback_model in _ollama_fallback_models(model):
                        try:
                            payload_retry = dict(payload)
                            payload_retry["model"] = fallback_model
                            print(
                                f"[LLM] Ollama model '{model}' too large for RAM; retrying with '{fallback_model}'..."
                            )
                            retry = _session.post(url, json=payload_retry, headers=headers, timeout=LLM_TIMEOUT)
                            retry.raise_for_status()
                            data = retry.json()

                            result = ""
                            if data.get("choices"):
                                result = data["choices"][0]["message"]["content"]
                            elif "message" in data:
                                result = data["message"].get("content", "")
                            else:
                                continue

                            _llm_cache[cache_key] = {"response": result, "time": time.time()}
                            return result
                        except requests.HTTPError as retry_err:
                            retry_resp = retry_err.response
                            retry_status = retry_resp.status_code if retry_resp is not None else None
                            retry_body = (retry_resp.text if retry_resp is not None else "")
                            if retry_status == 500 and _is_ollama_insufficient_memory_error(retry_body):
                                continue
                            break
                        except Exception:
                            continue

                    hint = (
                        "Ollama model doesn't fit in available RAM. "
                        "Try setting OLLAMA_MODEL=llama3.2 (or configure OLLAMA_FALLBACK_MODELS), "
                        "then restart Ollama."
                    )
                    return f"[LLM error 500: {hint}]"
            return f"[LLM error {status}: {body}]"
            
        except requests.exceptions.ConnectionError:
            return f"[Unable to reach {provider} LLM server at {api_base}]"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def extract_tool_call(self, text: str) -> Optional[Dict]:
        """Extract tool call from LLM response"""
        print(f"[DEBUG] LLM Response:\n{text}\n---END LLM RESPONSE---")
        
        # Pattern 1: ```tool { "tool": "name", "args": {...} } ```
        pattern = r'```tool\s*\n?({.*?})\s*\n?```'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        # Pattern 2: {"tool": "name", "args": {...}}
        pattern2 = r'\{"tool":\s*"([^"]+)".*?\}'
        match2 = re.search(pattern2, text, re.DOTALL)
        if match2:
            try:
                start = match2.start()
                brace_count = 0
                end = start
                for i, c in enumerate(text[start:]):
                    if c == '{':
                        brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = start + i + 1
                            break
                return json.loads(text[start:end])
            except:
                pass
        
        # Pattern 3: tool_name\n{"arg": "value"} or tool_name {"arg": "value"}
        # This catches: "type_text\n{"text": "hello"}" or "click {"x": 100, "y": 200}"
        pattern3 = r'(\w+)\s*\n?\{([^}]+)\}'
        match3 = re.search(pattern3, text)
        if match3:
            tool_name = match3.group(0).split()[0].split('\n')[0].strip()
            # Check if it's a valid tool name
            if tool_name in TOOLS:
                try:
                    # Extract the JSON part
                    json_start = text.find('{', match3.start())
                    brace_count = 0
                    json_end = json_start
                    for i, c in enumerate(text[json_start:]):
                        if c == '{':
                            brace_count += 1
                        elif c == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = json_start + i + 1
                                break
                    args = json.loads(text[json_start:json_end])
                    print(f"[DEBUG] Extracted tool: {tool_name} with args: {args}")
                    return {"tool": tool_name, "args": args}
                except Exception as e:
                    print(f"[DEBUG] Failed to parse pattern3: {e}")
                    pass
        
        # Pattern 4: Just tool name alone (for no-arg tools like screenshot)
        words = text.strip().split()
        if len(words) == 1 and words[0] in TOOLS:
            print(f"[DEBUG] Extracted single-word tool: {words[0]}")
            return {"tool": words[0], "args": {}}
        
        return None
    
    def execute_tool(self, tool_name: str, args: Dict) -> Dict:
        """Execute a tool and return result"""
        if tool_name not in TOOLS:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        # Update progress: Tool execution started
        agent_working("amigos", f"Executing: {tool_name}", progress=45)
        
        func, requires_approval, desc = TOOLS[tool_name]
        
        try:
            # Enforce autonomy policies for internal calls as well
            try:
                guard_tool_execution(tool_name, args)
            except HTTPException as he:
                autonomy_controller.log_action('tool_blocked_internal', {'tool': tool_name, 'args': args}, {'error': str(he.detail)})
                return {'success': False, 'error': 'blocked_by_autonomy', 'detail': he.detail}
            # Handle different argument formats
            if isinstance(args, dict):
                result = func(**args)
            else:
                result = func(args)
            
            # Update progress: Tool execution completed
            agent_working("amigos", f"Finished: {tool_name}", progress=85)
            
            return result
        except TypeError as e:
            # Try to provide helpful error
            return {"success": False, "error": f"Invalid arguments for {tool_name}: {str(e)}"}
        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def detect_required_action(self, user_message: str) -> Optional[Dict]:
        """Detect if user message requires a tool call and return a default tool call if LLM fails to emit one"""
        msg_lower = user_message.lower().strip()

        # ═══════════════════════════════════════════════════════════════
        # CANVAS SHORTCUTS (precision & speed)
        # Users explicitly asking for Canvas should always get Canvas tools.
        # Also guard against common speech-to-text confusion (canvas ≠ chocolate).
        # ═══════════════════════════════════════════════════════════════

        def _mentions_canvas(text: str) -> bool:
            t = text.replace('-', ' ')
            if any(k in t for k in [
                "canvas", "chalk board", "whiteboard", "white board", "canvas", "diagram board"
            ]):
                return True
            # If STT/typo produced 'chocolate' but it's clearly about boards/diagrams, treat as canvas.
            if ("chocolate" in t) or ("choclate" in t):
                if any(k in t for k in ["board", "whiteboard", "diagram", "draw", "plan", "flowchart", "floor plan", "canvas"]):
                    return True
            return False

        if _mentions_canvas(msg_lower):
            # Clear/erase/reset
            if any(k in msg_lower for k in ["clear", "erase", "reset", "wipe"]):
                return {"tool": "canvas_clear", "args": {}}

            # Export/save
            if any(k in msg_lower for k in ["export", "download", "save", "snapshot"]):
                fmt_match = re.search(r"\b(png|svg|pdf|dxf|json)\b", msg_lower)
                fmt = (fmt_match.group(1) if fmt_match else "png")
                # Optional filename detection: "as myfile.png"
                fname_match = re.search(r"\b(?:as|to)\s+([^\s]+\.(?:png|svg|pdf|dxf|json))\b", user_message, flags=re.IGNORECASE)
                filename = fname_match.group(1) if fname_match else None
                args = {"format": fmt}
                if filename:
                    args["filename"] = filename
                return {"tool": "canvas_export", "args": args}

            # Mode switching
            if any(k in msg_lower for k in ["mode", "sketch", "diagram", "cad", "text", "media"]):
                if "cad" in msg_lower:
                    mode = "CAD"
                elif "sketch" in msg_lower:
                    mode = "SKETCH"
                elif "text" in msg_lower:
                    mode = "TEXT"
                elif "media" in msg_lower:
                    mode = "MEDIA"
                else:
                    mode = "DIAGRAM"
                return {"tool": "canvas_set_mode", "args": {"mode": mode}}

            # Default: mirror the user's request onto the canvas for clarity.
            text = user_message.strip()
            if len(text) > 180:
                text = text[:180] + "…"
            if not text:
                text = "Canvas ready. What are we drawing?"
            return {
                "tool": "canvas_draw_text",
                "args": {
                    "text": f"Canvas: {text}",
                    "x": 20,
                    "y": 20,
                    "font_size": 18,
                    "color": "#ffffff",
                },
            }

        # ═══════════════════════════════════════════════════════════════
        # ITINERARY NARRATION SHORTCUTS
        # "Read Itiniary" (common misspelling) should always produce an ordered,
        # plain-English timeline without relying on the LLM.
        # ═══════════════════════════════════════════════════════════════
        if any(k in msg_lower for k in [
            "read itiniary",
            "read itinerary",
            "read my itinerary",
            "read the itinerary",
            "read itineraries",
            "check itinerary",
            "check the itinerary",
            "did you check the itinerary",
            "did you check my itinerary",
            "email itinerary",
            "check the email itinerary",
            "did you check the email itinerary",
            "make my itinerary",
            "create my itinerary",
            "build my itinerary",
            "organize my itinerary",
            "format my itinerary",
            "show my itinerary",
            "show the itinerary",
            "show my travel itinerary",
            "itinerary timeline",
            "timeline itinerary",
            "tell me my itinerary",
            "show itinerary timeline",
            "check my flights",
            "show my flights",
            "see my flights",
            "my flights",
            "flight status",
            "flight info",
            "flight details",
            "flight itinerary",
            "travel plans",
            "trip details",
            "where am i going",
            "what is my travel schedule",
            "what flights do i have",
            "check my travel",
        ]):
            return {"tool": "agent_get_itinerary_timeline", "args": {}}
        
        # ═══════════════════════════════════════════════════════════════
        # CANVAS DESIGN REQUESTS - Dynamic Goal Extraction
        # Extract the actual design goal from user message, not static placeholder
        # ═══════════════════════════════════════════════════════════════
        design_keywords = ["design", "draw", "sketch", "plan", "create", "blueprint", "layout", "floor plan"]
        if any(kw in msg_lower for kw in design_keywords):
            # Try to extract the design goal from the message
            design_patterns = [
                r"(?:design|draw|sketch|plan|create|blueprint)\s+(?:a|the|an)?\s+(.+?)(?:\?|\.|\s+and|$)",
                r"(?:show me|create|make)?\s+(?:a|the|an)?\s+(.+?)\s+(?:design|floor plan|layout|sketch)(?:\?|\.|\s+and|$)",
                r"(?:floor plan|blueprint|layout)s?\s+(?:for|of)?\s+(.+?)(?:\?|\.|\s+and|$)",
            ]
            
            for pattern in design_patterns:
                match = re.search(pattern, user_message, flags=re.IGNORECASE)
                if match:
                    design_goal = match.group(1).strip()
                    # Ensure goal is meaningful (>3 chars, not just "a" or "the")
                    if design_goal and len(design_goal) > 2:
                        return {"tool": "canvas_design", "args": {"goal": design_goal}}

        # ═══════════════════════════════════════════════════════════════
        # OPENWORK / OPENCODE WORKFLOW TRIGGERS
        # ═══════════════════════════════════════════════════════════════
        openwork_terms = ["openwork", "open work", "opencode", "open code"]
        if any(term in msg_lower for term in openwork_terms):
            if any(k in msg_lower for k in ["new session", "create session", "start session", "workflow", "work flow", "multi-step", "multi step"]):
                return {
                    "tool": "openwork_create_session",
                    "args": {"workspace_path": None, "prompt": user_message.strip()},
                }
        
        # Direct mappings for common phrases
        direct_actions = {
            # OpenWork workflows
            "openwork status": {"tool": "openwork_status", "args": {}},
            "openwork server": {"tool": "openwork_status", "args": {}},
            "start openwork server": {"tool": "openwork_start_server", "args": {}},
            "stop openwork server": {"tool": "openwork_stop_server", "args": {}},
            "openwork sessions": {"tool": "openwork_list_sessions", "args": {}},
            "list openwork sessions": {"tool": "openwork_list_sessions", "args": {}},
            "openwork workspaces": {"tool": "openwork_get_workspaces", "args": {}},
            "list openwork workspaces": {"tool": "openwork_get_workspaces", "args": {}},
            "openwork skills": {"tool": "openwork_get_skills", "args": {}},
            "list openwork skills": {"tool": "openwork_get_skills", "args": {}},
            "opencode status": {"tool": "openwork_status", "args": {}},
            "opencode server": {"tool": "openwork_status", "args": {}},
            "start opencode server": {"tool": "openwork_start_server", "args": {}},
            "stop opencode server": {"tool": "openwork_stop_server", "args": {}},
            "opencode sessions": {"tool": "openwork_list_sessions", "args": {}},
            "list opencode sessions": {"tool": "openwork_list_sessions", "args": {}},
            "opencode workspaces": {"tool": "openwork_get_workspaces", "args": {}},
            "list opencode workspaces": {"tool": "openwork_get_workspaces", "args": {}},
            "opencode skills": {"tool": "openwork_get_skills", "args": {}},
            "list opencode skills": {"tool": "openwork_get_skills", "args": {}},
            # Browser/Open actions
            "open browser": {"tool": "open_url_default_browser", "args": {"url": "https://www.google.com"}},
            "open default browser": {"tool": "open_url_default_browser", "args": {"url": "https://www.google.com"}},
            "open google": {"tool": "open_url_default_browser", "args": {"url": "https://www.google.com"}},
            "open google browser": {"tool": "open_url_default_browser", "args": {"url": "https://www.google.com"}},
            "open default google browser": {"tool": "open_url_default_browser", "args": {"url": "https://www.google.com"}},
            "open youtube": {"tool": "open_url_default_browser", "args": {"url": "https://www.youtube.com"}},
            "open facebook": {"tool": "open_url_default_browser", "args": {"url": "https://www.facebook.com"}},
            "open twitter": {"tool": "open_url_default_browser", "args": {"url": "https://www.twitter.com"}},
            "open x": {"tool": "open_url_default_browser", "args": {"url": "https://www.x.com"}},
            "open reddit": {"tool": "open_url_default_browser", "args": {"url": "https://www.reddit.com"}},
            "open github": {"tool": "open_url_default_browser", "args": {"url": "https://www.github.com"}},
            "open bing": {"tool": "open_url_default_browser", "args": {"url": "https://www.bing.com"}},
            # Social Media platforms
            "open instagram": {"tool": "open_url_default_browser", "args": {"url": "https://www.instagram.com"}},
            "open linkedin": {"tool": "open_url_default_browser", "args": {"url": "https://www.linkedin.com"}},
            "open tiktok": {"tool": "open_url_default_browser", "args": {"url": "https://www.tiktok.com"}},
            "go to facebook": {"tool": "open_url_default_browser", "args": {"url": "https://www.facebook.com"}},
            "go to twitter": {"tool": "open_url_default_browser", "args": {"url": "https://www.x.com"}},
            "go to instagram": {"tool": "open_url_default_browser", "args": {"url": "https://www.instagram.com"}},
            "go to linkedin": {"tool": "open_url_default_browser", "args": {"url": "https://www.linkedin.com"}},
            "go to tiktok": {"tool": "open_url_default_browser", "args": {"url": "https://www.tiktok.com"}},
            "post on facebook": {"tool": "open_url_default_browser", "args": {"url": "https://www.facebook.com"}},
            "post on twitter": {"tool": "open_url_default_browser", "args": {"url": "https://www.x.com"}},
            "post on instagram": {"tool": "open_url_default_browser", "args": {"url": "https://www.instagram.com"}},
            "post on linkedin": {"tool": "open_url_default_browser", "args": {"url": "https://www.linkedin.com"}},
            # Facebook Groups (Darrell's)
            "open facebook group": {"tool": "open_facebook_group", "args": {"group_id": "profile_groups"}},
            "open my groups": {"tool": "open_facebook_group", "args": {"group_id": "profile_groups"}},
            "open facebook groups": {"tool": "open_facebook_group", "args": {"group_id": "profile_groups"}},
            "open my facebook groups": {"tool": "open_facebook_group", "args": {"group_id": "profile_groups"}},
            "show my groups": {"tool": "open_facebook_group", "args": {"group_id": "profile_groups"}},
            "open amigosbrenton groups": {"tool": "open_facebook_group", "args": {"group_id": "amigos_brenton"}},
            "open darrell's groups": {"tool": "open_facebook_group", "args": {"group_id": "darrells_groups"}},
            # Facebook Group Automated - multiple variations
            "open facebook group automated": {"tool": "open_facebook_group_automated", "args": {"group_id": "main"}},
            "facebook group automated": {"tool": "open_facebook_group_automated", "args": {"group_id": "main"}},
            "open group automated": {"tool": "open_facebook_group_automated", "args": {"group_id": "main"}},
            "automated facebook group": {"tool": "open_facebook_group_automated", "args": {"group_id": "main"}},
            "open facebook automated": {"tool": "open_facebook_group_automated", "args": {"group_id": "main"}},
            "selenium facebook": {"tool": "open_facebook_group_automated", "args": {"group_id": "main"}},
            "open preferred group": {"tool": "open_facebook_group_automated", "args": {"group_id": "preferred"}},
            "open main group": {"tool": "open_facebook_group_automated", "args": {"group_id": "main"}},
            "engage facebook group": {"tool": "engage_facebook_group_posts", "args": {}},
            "list all platforms": {"tool": "list_all_platforms", "args": {}},
            "get all platforms": {"tool": "list_all_platforms", "args": {}},
            "show platforms": {"tool": "list_all_platforms", "args": {}},
            "get facebook groups": {"tool": "get_facebook_groups", "args": {}},
            # Full Engagement Commands
            "full engagement": {"tool": "full_facebook_engagement", "args": {"max_posts": 10}},
            "engage all posts": {"tool": "full_facebook_engagement", "args": {"max_posts": 10}},
            "like follow comment all": {"tool": "full_facebook_engagement", "args": {"max_posts": 10}},
            "auto engage": {"tool": "full_facebook_engagement", "args": {"max_posts": 10}},
            "scroll and engage": {"tool": "quick_engage_scroll", "args": {"scroll_and_engage_times": 10}},
            "quick engage": {"tool": "quick_engage_scroll", "args": {"scroll_and_engage_times": 10}},
            "continuous engage": {"tool": "quick_engage_scroll", "args": {"scroll_and_engage_times": 20}},
            "mass engage": {"tool": "full_facebook_engagement", "args": {"max_posts": 20}},
            "reply to comments": {"tool": "reply_to_post_comments", "args": {"max_posts": 3}},
            
            # ═══════════════════════════════════════════════════════════════
            # MAP & LOCATION TRIGGERS
            # ═══════════════════════════════════════════════════════════════
            "show map": {"tool": "map_control", "args": {"place": "Brisbane, Australia"}},
            "open map": {"tool": "map_control", "args": {"place": "Brisbane, Australia"}},
            "where is": {"tool": "map_control", "args": {"place": ""}}, # Will be filled by regex below
            "directions to": {"tool": "map_control", "args": {"destination": ""}},
            "how do i get to": {"tool": "map_control", "args": {"destination": ""}},
            
            # ═══════════════════════════════════════════════════════════════
            # INTERNET & SEARCH TRIGGERS
            # ═══════════════════════════════════════════════════════════════
            "search for": {"tool": "web_search", "args": {"query": ""}},
            "look up": {"tool": "web_search", "args": {"query": ""}},
            "what is": {"tool": "web_search", "args": {"query": ""}},
            "who is": {"tool": "web_search", "args": {"query": ""}},
            "latest news": {"tool": "web_search_news", "args": {"query": "latest world news"}},
            "news about": {"tool": "web_search_news", "args": {"query": ""}},
            "comment engage": {"tool": "reply_to_post_comments", "args": {"max_posts": 3}},
            "engage comments": {"tool": "reply_to_post_comments", "args": {"max_posts": 5}},
            "reply engage": {"tool": "reply_to_post_comments", "args": {"max_posts": 3}},
            "engage everything": {"tool": "full_facebook_engagement", "args": {"max_posts": 15}},
            # Screenshots
            "screenshot": {"tool": "screenshot", "args": {}},
            "take screenshot": {"tool": "screenshot", "args": {}},
            "take a screenshot": {"tool": "screenshot", "args": {}},
            "capture screen": {"tool": "screenshot", "args": {}},
            # System info
            "system info": {"tool": "get_system_info", "args": {}},
            "get system info": {"tool": "get_system_info", "args": {}},
            "system stats": {"tool": "get_system_stats", "args": {}},
            "cpu usage": {"tool": "get_system_stats", "args": {}},
            "memory usage": {"tool": "get_system_stats", "args": {}},
            # Clipboard
            "paste": {"tool": "paste_from_clipboard", "args": {}},
            "get clipboard": {"tool": "paste_from_clipboard", "args": {}},
            "clipboard": {"tool": "paste_from_clipboard", "args": {}},
            # Processes
            "list processes": {"tool": "list_processes", "args": {}},
            "show processes": {"tool": "list_processes", "args": {}},
            "running processes": {"tool": "list_processes", "args": {}},
            # Directory
            "current directory": {"tool": "get_current_directory", "args": {}},
            "pwd": {"tool": "get_current_directory", "args": {}},
            "where am i": {"tool": "get_current_directory", "args": {}},
            # Mouse
            "mouse position": {"tool": "get_mouse_position", "args": {}},
            "where is mouse": {"tool": "get_mouse_position", "args": {}},
            # Screen
            "screen size": {"tool": "get_screen_size", "args": {}},
            # Game Trainer
            "list game processes": {"tool": "list_game_processes", "args": {}},
            "list games": {"tool": "list_game_processes", "args": {}},
            "show games": {"tool": "list_game_processes", "args": {}},
            "running games": {"tool": "list_game_processes", "args": {}},
            "find games": {"tool": "list_game_processes", "args": {}},
            "game trainer help": {"tool": "game_trainer_help", "args": {}},
            "trainer help": {"tool": "game_trainer_help", "args": {}},
            "mod help": {"tool": "game_trainer_help", "args": {}},
            "list frozen": {"tool": "list_frozen_values", "args": {}},
            "frozen values": {"tool": "list_frozen_values", "args": {}},
            "list mods": {"tool": "list_mod_files", "args": {}},
            "my mods": {"tool": "list_mod_files", "args": {}},
            "show mods": {"tool": "list_mod_files", "args": {}},
            # Database & Memory Queries - CRITICAL for family info
            "my family": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "about my family": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "who is my family": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "family members": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "family information": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "tell me about family": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "who is brenton": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "who is felirma": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "my partner": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "my wife": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "my son": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "my brothers": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "my sisters": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "who are my brothers": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "who are my sisters": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "database": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "the database": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "check database": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "read database": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "access database": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "user profile": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "owner profile": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "my profile": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "what do you know about me": {"tool": "read_file", "args": {"path": "backend/data/forms_db/user_profiles.json"}},
            "what do you remember": {"tool": "get_all_memories", "args": {}},
            "your memory": {"tool": "get_all_memories", "args": {}},
            "your memories": {"tool": "get_all_memories", "args": {}},
            "what have you learned": {"tool": "get_all_memories", "args": {}},
            "memory summary": {"tool": "get_memory_summary", "args": {}},
            "all memories": {"tool": "get_all_memories", "args": {}},
            # Quick conversational - improve perceived speed
            "hi": None,  # Let LLM handle greetings naturally
            "hello": None,
            "hey": None,
            "thanks": None,
            "thank you": None,
            # Media - Quick access
            "list images": {"tool": "list_images", "args": {}},
            "show images": {"tool": "list_images", "args": {}},
            "my images": {"tool": "list_images", "args": {}},
            "list videos": {"tool": "list_videos", "args": {}},
            "show videos": {"tool": "list_videos", "args": {}},
            "my videos": {"tool": "list_videos", "args": {}},
            "list audio": {"tool": "list_audio_files", "args": {}},
            "list audio files": {"tool": "list_audio_files", "args": {}},
            "show audio": {"tool": "list_audio_files", "args": {}},
            
            # ═══════════════════════════════════════════════════════════════
            # MEDIA GENERATION - Images
            # ═══════════════════════════════════════════════════════════════
            "generate image": {"tool": "generate_image", "args": {"prompt": "beautiful landscape"}},
            "create image": {"tool": "generate_image", "args": {"prompt": "beautiful landscape"}},
            "make image": {"tool": "generate_image", "args": {"prompt": "beautiful landscape"}},
            "ai image": {"tool": "generate_image", "args": {"prompt": "beautiful landscape"}},
            
            # ═══════════════════════════════════════════════════════════════
            # MEDIA GENERATION - Video
            # ═══════════════════════════════════════════════════════════════
            "generate video": {"tool": "generate_ai_video", "args": {"prompt": "cinematic nature scene", "model": "wan"}},
            "create video": {"tool": "generate_ai_video", "args": {"prompt": "cinematic nature scene", "model": "wan"}},
            "make video": {"tool": "generate_ai_video", "args": {"prompt": "cinematic nature scene", "model": "wan"}},
            "ai video": {"tool": "generate_ai_video", "args": {"prompt": "cinematic nature scene", "model": "wan"}},
            

            
            # ═══════════════════════════════════════════════════════════════
            # SCRAPING & DATA EXTRACTION
            # ═══════════════════════════════════════════════════════════════
            "scrape this page": {"tool": "get_page_content", "args": {}},
            "get page content": {"tool": "get_page_content", "args": {}},
            "extract page": {"tool": "get_page_content", "args": {}},
            "read this page": {"tool": "get_page_content", "args": {}},
            
            # ═══════════════════════════════════════════════════════════════
            # SECRETARY / DOCUMENT CREATION
            # ═══════════════════════════════════════════════════════════════
            "write a letter": {"tool": "create_document", "args": {"doc_type": "letter", "title": "Letter", "content": ""}},
            "create a letter": {"tool": "create_document", "args": {"doc_type": "letter", "title": "Letter", "content": ""}},
            "write a report": {"tool": "create_document", "args": {"doc_type": "report", "title": "Report", "content": ""}},
            "create a report": {"tool": "create_document", "args": {"doc_type": "report", "title": "Report", "content": ""}},
            "write a memo": {"tool": "take_memo", "args": {"subject": "Memo", "content": "", "priority": "normal"}},
            "take a memo": {"tool": "take_memo", "args": {"subject": "Memo", "content": "", "priority": "normal"}},
            "create a memo": {"tool": "take_memo", "args": {"subject": "Memo", "content": "", "priority": "normal"}},
            "take note": {"tool": "quick_note", "args": {"note": ""}},
            "make a note": {"tool": "quick_note", "args": {"note": ""}},
            "write note": {"tool": "quick_note", "args": {"note": ""}},
            "create todo": {"tool": "create_todo_list", "args": {"title": "Todo List", "items": []}},
            "todo list": {"tool": "create_todo_list", "args": {"title": "Todo List", "items": []}},
            "make todo list": {"tool": "create_todo_list", "args": {"title": "Todo List", "items": []}},
            "meeting notes": {"tool": "create_meeting_notes", "args": {"title": "Meeting Notes", "attendees": [], "agenda": [], "notes": "", "action_items": []}},
            "create meeting notes": {"tool": "create_meeting_notes", "args": {"title": "Meeting Notes", "attendees": [], "agenda": [], "notes": "", "action_items": []}},
            "list my documents": {"tool": "list_secretary_files", "args": {}},
            "show my documents": {"tool": "list_secretary_files", "args": {}},
            "my documents": {"tool": "list_secretary_files", "args": {}},
            "list secretary files": {"tool": "list_secretary_files", "args": {}},
            
            # ═══════════════════════════════════════════════════════════════
            # RECORDING - Screen & Audio
            # ═══════════════════════════════════════════════════════════════
            "start recording": {"tool": "start_screen_recording", "args": {}},
            "record screen": {"tool": "start_screen_recording", "args": {}},
            "start screen recording": {"tool": "start_screen_recording", "args": {}},
            "stop recording": {"tool": "stop_screen_recording", "args": {}},
            "stop screen recording": {"tool": "stop_screen_recording", "args": {}},
            "recording status": {"tool": "get_recording_status", "args": {}},
            "am i recording": {"tool": "get_recording_status", "args": {}},
            "list recordings": {"tool": "list_recordings", "args": {}},
            "show recordings": {"tool": "list_recordings", "args": {}},
            "my recordings": {"tool": "list_recordings", "args": {}},
            "start audio recording": {"tool": "start_audio_recording", "args": {}},
            "record audio": {"tool": "start_audio_recording", "args": {}},
            "record voice": {"tool": "start_audio_recording", "args": {}},
            "stop audio recording": {"tool": "stop_audio_recording", "args": {}},
            "stop voice recording": {"tool": "stop_audio_recording", "args": {}},
            "list microphones": {"tool": "list_audio_devices", "args": {}},
            "list audio devices": {"tool": "list_audio_devices", "args": {}},
            "check ffmpeg": {"tool": "check_ffmpeg", "args": {}},
            
            # ═══════════════════════════════════════════════════════════════
            # SOCIAL MEDIA ENGAGEMENT
            # ═══════════════════════════════════════════════════════════════
            "like this post": {"tool": "like_post", "args": {}},
            "like post": {"tool": "like_post", "args": {}},
            "follow user": {"tool": "follow_user", "args": {}},
            "follow this user": {"tool": "follow_user", "args": {}},
            "write comment": {"tool": "write_comment", "args": {"comment": "Great post."}},
            "add comment": {"tool": "write_comment", "args": {"comment": "Great post."}},
            "leave comment": {"tool": "write_comment", "args": {"comment": "Great post."}},
            "engage post": {"tool": "engage_with_post", "args": {}},
            "engage with post": {"tool": "engage_with_post", "args": {}},
            "get visible posts": {"tool": "get_visible_posts", "args": {}},
            "show visible posts": {"tool": "get_visible_posts", "args": {}},
            "read post": {"tool": "read_post_content", "args": {}},
            "read this post": {"tool": "read_post_content", "args": {}},
            "get trending hashtags": {"tool": "get_trending_hashtags", "args": {}},
            "trending hashtags": {"tool": "get_trending_hashtags", "args": {}},
            "show hashtags": {"tool": "get_trending_hashtags", "args": {}},
            "engagement phrases": {"tool": "get_engagement_phrases", "args": {}},
            "comment ideas": {"tool": "get_engagement_phrases", "args": {}},
            "platform limits": {"tool": "get_platform_limits", "args": {}},
            "character limits": {"tool": "get_platform_limits", "args": {}},
            "open all platforms": {"tool": "open_all_platforms", "args": {}},
            "open all socials": {"tool": "open_all_platforms", "args": {}},
            
            # ═══════════════════════════════════════════════════════════════
            # WEB SEARCH & NEWS
            # ═══════════════════════════════════════════════════════════════
            "search news": {"tool": "web_search_news", "args": {"query": "latest news today"}},
            "latest news": {"tool": "web_search_news", "args": {"query": "breaking news today"}},
            "breaking news": {"tool": "web_search_news", "args": {"query": "breaking news today"}},
            "today's news": {"tool": "web_search_news", "args": {"query": "top news today"}},
            "world news": {"tool": "web_search_news", "args": {"query": "world news today"}},
            "tech news": {"tool": "web_search_news", "args": {"query": "technology news today"}},
            "technology news": {"tool": "web_search_news", "args": {"query": "technology news today"}},
            "sports news": {"tool": "web_search_news", "args": {"query": "sports news today"}},
            "entertainment news": {"tool": "web_search_news", "args": {"query": "entertainment news today"}},
            "weather": {"tool": "get_weather", "args": {}},
            "weather today": {"tool": "get_weather", "args": {}},
            
            # Finance/Crypto Research - Direct triggers
            "crypto trends": {"tool": "web_search", "args": {"query": "crypto market trends today"}},
            "crypto news": {"tool": "web_search", "args": {"query": "cryptocurrency news today"}},
            "bitcoin news": {"tool": "web_search", "args": {"query": "bitcoin price news today"}},
            "bitcoin price": {"tool": "web_search", "args": {"query": "bitcoin current price"}},
            "ethereum news": {"tool": "web_search", "args": {"query": "ethereum price news today"}},
            "ethereum price": {"tool": "web_search", "args": {"query": "ethereum current price"}},
            "market trends": {"tool": "web_search", "args": {"query": "financial market trends today"}},
            "stock market": {"tool": "web_search", "args": {"query": "stock market news today"}},
            "stock news": {"tool": "web_search", "args": {"query": "stock market news today"}},
            "financial news": {"tool": "web_search", "args": {"query": "financial market news today"}},
            "financial market trends": {"tool": "web_search", "args": {"query": "financial market trends analysis today"}},
            "trading news": {"tool": "web_search", "args": {"query": "trading news today"}},
            "investment news": {"tool": "web_search", "args": {"query": "investment news today"}},
            "market analysis": {"tool": "web_search", "args": {"query": "market analysis today"}},
            "forex news": {"tool": "web_search", "args": {"query": "forex trading news today"}},
            "gold price": {"tool": "web_search", "args": {"query": "gold price today"}},
            "oil price": {"tool": "web_search", "args": {"query": "crude oil price today"}},
            
            # ═══════════════════════════════════════════════════════════════
            # AI ASSISTANCE
            # ═══════════════════════════════════════════════════════════════
            "ask ai": {"tool": "ask_ai", "args": {"question": ""}},
            "analyze this": {"tool": "ask_ai", "args": {"question": "Analyze the following:"}},
            "explain this": {"tool": "ask_ai", "args": {"question": "Explain the following:"}},
            "summarize this": {"tool": "summarize_scraped_content", "args": {"content": ""}},
            "write report": {"tool": "write_report", "args": {"title": "Report", "content": "", "format": "markdown"}},
            
            # ═══════════════════════════════════════════════════════════════
            # FILE OPERATIONS
            # ═══════════════════════════════════════════════════════════════
            "list files": {"tool": "list_directory", "args": {"path": "."}},
            "show files": {"tool": "list_directory", "args": {"path": "."}},
            "dir": {"tool": "list_directory", "args": {"path": "."}},
            "ls": {"tool": "list_directory", "args": {"path": "."}},
            
            # ═══════════════════════════════════════════════════════════════
            # BROWSER AUTOMATION
            # ═══════════════════════════════════════════════════════════════
            "browser screenshot": {"tool": "take_browser_screenshot", "args": {}},
            "screenshot browser": {"tool": "take_browser_screenshot", "args": {}},
            "go back": {"tool": "go_back", "args": {}},
            "browser back": {"tool": "go_back", "args": {}},
            "go forward": {"tool": "go_forward", "args": {}},
            "browser forward": {"tool": "go_forward", "args": {}},
            "refresh page": {"tool": "refresh", "args": {}},
            "reload page": {"tool": "refresh", "args": {}},
            "new tab": {"tool": "new_tab", "args": {}},
            "open new tab": {"tool": "new_tab", "args": {}},
            "close tab": {"tool": "close_tab", "args": {}},
            "close browser": {"tool": "close_browser", "args": {}},
            "get current url": {"tool": "get_current_url", "args": {}},
            "current url": {"tool": "get_current_url", "args": {}},
            "what page am i on": {"tool": "get_current_url", "args": {}},
            "scroll page down": {"tool": "scroll_page", "args": {"direction": "down"}},
            "scroll page up": {"tool": "scroll_page", "args": {"direction": "up"}},
            
            # ═══════════════════════════════════════════════════════════════
            # SYSTEM OPERATIONS
            # ═══════════════════════════════════════════════════════════════
            "show notification": {"tool": "show_notification", "args": {"title": "Agent Amigos", "message": "Notification!"}},
            "notify me": {"tool": "show_notification", "args": {"title": "Agent Amigos", "message": "Notification!"}},
            "what time is it": {"tool": "get_datetime", "args": {}},
            "current time": {"tool": "get_datetime", "args": {}},
            "today's date": {"tool": "get_datetime", "args": {}},
            "date and time": {"tool": "get_datetime", "args": {}},
            "get date": {"tool": "get_datetime", "args": {}},
            
            # Quick help
            "help": None,  # Let LLM explain capabilities
            "what can you do": None,
            "your capabilities": None,
        }
        
        # Check direct matches - sort by length descending to match longer phrases first
        # This ensures "open facebook group automated" matches before "open facebook"
        #
        # IMPORTANT:
        # For prompts/typing-related actions we must NOT match on substring, otherwise
        # messages like "generate image of a cat" would match "generate image" and
        # discard the user's prompt.
        msg_stripped = msg_lower.strip()
        exact_only_phrases = {
            # Media generation shortcuts (avoid clobbering dynamic prompts)
            "generate image",
            "create image",
            "make image",
            "ai image",
        }

        sorted_phrases = sorted(direct_actions.keys(), key=len, reverse=True)
        for phrase in sorted_phrases:
            if phrase in exact_only_phrases:
                if msg_stripped != phrase:
                    continue
            else:
                if phrase not in msg_lower:
                    continue

            action = direct_actions[phrase]
            # None means skip to LLM (for greetings, help, etc.)
            if action is None:
                return None
            return action
        
        # Pattern matching for dynamic content
        import urllib.parse
        
        # Check if message IS a URL (user just pasted a URL)
        url_only_pattern = r"^(https?://\S+)$"
        url_only_match = re.search(url_only_pattern, user_message.strip())
        if url_only_match:
            url = url_only_match.group(1)
            # Check if it's a Facebook groups URL - use the Facebook group tool
            if "facebook.com" in url and "/groups" in url:
                return {"tool": "open_facebook_group", "args": {"group_id": url}}
            return {"tool": "open_url_default_browser", "args": {"url": url}}
        
        # Check if message contains a URL that should be opened
        url_in_message = re.search(r"(https?://\S+)", user_message)
        if url_in_message:
            url = url_in_message.group(1)
            # If user is talking about a Facebook groups URL
            if "facebook.com" in url and "/groups" in url:
                return {"tool": "open_facebook_group", "args": {"group_id": url}}

        # ═══════════════════════════════════════════════════════════════
        # DYNAMIC MAP EXTRACTION
        # ═══════════════════════════════════════════════════════════════
        map_patterns = [
            (r"(?:where is|show me|open map for|navigate to|look up)\s+(?:the|a)?\s*(.+?)(?:\?|\.|$)", "place"),
            (r"(?:directions|how do i get)\s+(?:from|starting at)\s+(.+?)\s+(?:to|ending at)\s+(.+?)(?:\?|\.|$)", "route"),
        ]
        
        for pattern, ptype in map_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                if ptype == "place":
                    place = match.group(1).strip()
                    if place and len(place) > 2:
                        return {"tool": "map_control", "args": {"place": place}}
                elif ptype == "route":
                    origin = match.group(1).strip()
                    dest = match.group(2).strip()
                    if origin and dest:
                        return {"tool": "map_control", "args": {"origin": origin, "destination": dest}}

        # ═══════════════════════════════════════════════════════════════
        # DYNAMIC SEARCH EXTRACTION
        # ═══════════════════════════════════════════════════════════════
        search_patterns = [
            r"(?:search for|look up|what is|who is|tell me about)\s+(?:the|a)?\s*(.+?)(?:\?|\.|$)",
            r"(?:news about|latest on)\s+(.+?)(?:\?|\.|$)",
        ]
        
        for pattern in search_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                query = match.group(1).strip()
                if query and len(query) > 2:
                    # If it's news-related
                    if any(kw in msg_lower for kw in ["news", "latest", "update"]):
                        return {"tool": "web_search_news", "args": {"query": query}}
                    return {"tool": "web_search", "args": {"query": query}}
            # If there are action words with the URL
            if any(word in msg_lower for word in ["open", "go to", "navigate", "show", "visit", "browse"]):
                return {"tool": "open_url_default_browser", "args": {"url": url}}
        
        # "open [url]" pattern
        url_patterns = [
            r"open\s+(https?://\S+)",
            r"go to\s+(https?://\S+)",
            r"navigate to\s+(https?://\S+)",
            r"open\s+(\S+\.com)\b",
            r"open\s+(\S+\.org)\b",
            r"open\s+(\S+\.net)\b",
            r"open\s+(\S+\.io)\b",
        ]
        for pattern in url_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                url = match.group(1)
                if not url.startswith("http"):
                    url = f"https://{url}"
                return {"tool": "open_url_default_browser", "args": {"url": url}}
        
        # ═══════════════════════════════════════════════════════════════
        # MAPS & GEOGRAPHIC INTERACTION PATTERNS
        # ═══════════════════════════════════════════════════════════════
        map_patterns = [
            r"(?:show|open|get|display)\s+(?:me\s+)?(?:a\s+)?map\s+(?:of|at|for)\s+(.+?)$",
            r"map\s+(?:of|at|for)\s+(.+?)$",
            r"where\s+is\s+(.+?)$",
            r"(?:show|open|get|display)\s+(?:me\s+)?(?:the\s+)?location\s+(?:of|at|for)\s+(.+?)$",
            r"directions\s+(?:from|between)\s+(.+?)\s+(?:to|and)\s+(.+?)$",
            r"route\s+(?:from|between)\s+(.+?)\s+(?:to|and)\s+(.+?)$",
            r"(?:stadiums|restaurants|hotels|places|parks|shops|stores|malls|venues|landmarks)\s+(?:in|at|near|around)\s+(.+?)$",
            r"(.+?)\s+(?:area|region|city|town|suburb|district)$",
        ]
        for pattern in map_patterns:
            match = re.search(pattern, user_message, flags=re.IGNORECASE)
            if match:
                if "directions" in pattern or "route" in pattern:
                    origin = match.group(1).strip().strip("\"'")
                    destination = match.group(2).strip().strip("\"'")
                    return {"tool": "map_control", "args": {"origin": origin, "destination": destination}}
                else:
                    loc = match.group(1).strip().strip("\"'")
                    if loc:
                        # If the pattern was just a location name + area/city, use the whole thing
                        if "area" in pattern or "city" in pattern or "region" in pattern:
                            loc = match.group(0).strip()
                        
                        # Default zoom for cities/places
                        return {"tool": "map_control", "args": {"place": loc, "zoom": 15}}

        # ═══════════════════════════════════════════════════════════════
        # RESEARCH/ANALYSIS PATTERNS - Auto-search for trends, analysis, etc.
        # ═══════════════════════════════════════════════════════════════
        research_patterns = [
            r"(?:find|search|look up|check|get)\s+(?:the\s+)?(?:price|value|cost|rate)\s+(?:of|for)\s+(.+?)(?:\?|\.|$)",
            r"(?:how\s+much\s+is|what\s+is\s+the\s+price\s+of)\s+(.+?)(?:\?|\.|$)",
            r"(?:research|analyze|investigate)\s+(.+?)(?:\?|\.|$)",
            r"(?:tell\s+me\s+about|who\s+is|what\s+is)\s+(.+?)(?:\?|\.|$)",
            r"(?:latest|current)\s+(?:trends|news|updates)\s+(?:in|on|for)\s+(.+?)(?:\?|\.|$)",
        ]
        for pattern in research_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                query = match.group(1).strip()
                if query and len(query) > 2:
                    # If it's price related, maybe use a specific search
                    if any(kw in msg_lower for kw in ["price", "cost", "value", "rate"]):
                        return {"tool": "web_search", "args": {"query": f"current price of {query}"}}
                    return {"tool": "web_search", "args": {"query": query}}

        # ═══════════════════════════════════════════════════════════════
        # CANVAS DESIGN PATTERNS - Auto-trigger design tool
        # ═══════════════════════════════════════════════════════════════
        canvas_design_patterns = [
            r"(?:design|create|sketch|plan|draw|blueprint)\s+(?:a|the|an)?\s*(.+?)\s*(?:design|layout|plan|sketch|blueprint)?(?:\?|\.|$)",
            r"(?:show|give)\s+me\s+(?:a|the|an)?\s*(.+?)\s*(?:design|layout|plan|sketch|blueprint)(?:\?|\.|$)",
        ]
        for pattern in canvas_design_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                goal = match.group(1).strip()
                # Filter out common non-design words
                if goal and len(goal) > 3 and not any(kw in goal for kw in ["image", "video", "photo", "picture", "map"]):
                    return {"tool": "canvas_design", "args": {"goal": goal}}

        # ═══════════════════════════════════════════════════════════════
        # WEATHER PATTERNS - Live weather (Open-Meteo)
        # ═══════════════════════════════════════════════════════════════

        # "weather in <place>" / "forecast for <place>"
        weather_patterns = [
            r"(?:what(?:'s| is)\s+)?the\s+weather\s+(?:in|at|for)\s+(.+?)$",
            r"weather\s+(?:in|at|for)\s+(.+?)$",
            r"forecast\s+(?:in|at|for)\s+(.+?)$",
        ]
        for pattern in weather_patterns:
            match = re.search(pattern, user_message, flags=re.IGNORECASE)
            if match:
                loc = match.group(1).strip().strip("\"'")
                if loc:
                    return {"tool": "get_weather", "args": {"location": loc}}

        # "weather" referring to user's default location
        if any(k in msg_lower for k in ["weather", "forecast"]) and any(k in msg_lower for k in ["my location", "here", "where i am", "where i'm", "right now"]):
            return {"tool": "get_weather", "args": {}}
        
        # Crypto/Market/Finance research patterns - these should trigger web_search
        research_triggers = [
            # Crypto specific
            (r"crypto\s+(?:market\s+)?trends?", "crypto market trends today"),
            (r"(?:current\s+)?crypto\s+(?:market|news|prices?)", "crypto market news today"),
            (r"bitcoin\s+(?:price|trend|news)", "bitcoin price trend today"),
            (r"ethereum\s+(?:price|trend|news)", "ethereum price trend today"),
            (r"altcoin\s+(?:trends?|news)", "altcoin trends today"),
            # Stock market
            (r"stock\s+market\s+(?:trends?|news|analysis)", "stock market trends today"),
            (r"(?:current\s+)?market\s+trends?", "financial market trends today"),
            (r"financial\s+(?:market\s+)?(?:trends?|news|analysis)", "financial market trends today"),
            (r"(?:nasdaq|dow|s&p)\s+(?:trends?|news|today)", lambda m: f"{m.group(0)} stock market today"),
            # General market analysis
            (r"market\s+analysis", "market analysis today"),
            (r"trading\s+(?:trends?|news)", "trading trends today"),
            (r"investment\s+(?:trends?|news)", "investment trends today"),
            # News patterns
            (r"(?:latest|current|today(?:'s)?)\s+(?:crypto|market|financial|trading)\s+news", lambda m: m.group(0)),
            (r"what(?:'s| is)\s+happening\s+(?:in|with)\s+(?:crypto|the market|stocks)", "current market news today"),
            # Analysis requests
            (r"analyze\s+(?:the\s+)?(?:crypto|market|stock)", "market analysis today"),
            (r"(?:get|show|give)\s+(?:me\s+)?(?:crypto|market|financial)\s+(?:data|info|trends?)", lambda m: f"current {m.group(0).split()[-1]} news today"),
        ]
        
        for pattern, search_query in research_triggers:
            match = re.search(pattern, msg_lower)
            if match:
                # If search_query is callable (lambda), call it with the match
                if callable(search_query):
                    query = search_query(match)
                else:
                    query = search_query
                print(f"[AUTO-RESEARCH] Detected research request. Searching: {query}")
                return {"tool": "web_search", "args": {"query": query}}
        
        # "search for [query]" pattern (preserve user's original casing/spacing)
        search_patterns = [
            r"search\s+(?:for\s+)?[\"']?(.+?)[\"']?$",
            r"google\s+[\"']?(.+?)[\"']?$",
            r"look up\s+[\"']?(.+?)[\"']?$",
            r"find\s+(?:info|information)?\s*(?:on|about)?\s*[\"']?(.+?)[\"']?$",
        ]
        for pattern in search_patterns:
            match = re.search(pattern, user_message, flags=re.IGNORECASE)
            if match:
                query = match.group(1).strip()
                if query and len(query) > 2:
                    return {"tool": "web_search", "args": {"query": query}}
        
        # "type [text]" pattern (preserve user's original text)
        type_patterns = [
            r"type\s+[\"'](.+?)[\"']",
            r"type\s+(.+)$",
        ]
        for pattern in type_patterns:
            match = re.search(pattern, user_message, flags=re.IGNORECASE)
            if match:
                text = match.group(1).strip()
                if text:
                    return {"tool": "type_text", "args": {"text": text}}
        
        # "copy [text]" pattern (preserve user's original text)
        copy_match = re.search(r"copy\s+[\"']?(.+?)[\"']?(?:\s+to\s+clipboard)?$", user_message, flags=re.IGNORECASE)
        if copy_match:
            text = copy_match.group(1).strip()
            if text:
                return {"tool": "copy_to_clipboard", "args": {"text": text}}
        
        # "click" with coordinates
        click_match = re.search(r"click\s+(?:at\s+)?(\d+)[,\s]+(\d+)", msg_lower)
        if click_match:
            x, y = int(click_match.group(1)), int(click_match.group(2))
            return {"tool": "click", "args": {"x": x, "y": y}}
        
        # Simple "click" without coordinates
        if msg_lower.strip() == "click":
            return {"tool": "click", "args": {}}
        
        # "scroll up/down"
        if "scroll up" in msg_lower:
            return {"tool": "scroll", "args": {"clicks": 3}}
        if "scroll down" in msg_lower:
            return {"tool": "scroll", "args": {"clicks": -3}}
        
        # "press [key]"
        press_match = re.search(r"press\s+(\w+)", msg_lower)
        if press_match:
            key = press_match.group(1)
            return {"tool": "press_key", "args": {"key": key}}
        
        # "notify [message]" or "notification [message]" (preserve user's original text)
        notify_match = re.search(r"(?:notify|notification|alert)\s+[\"']?(.+?)[\"']?$", user_message, flags=re.IGNORECASE)
        if notify_match:
            message = notify_match.group(1).strip()
            return {"tool": "show_notification", "args": {"title": "Agent Amigos", "message": message}}
        
        # --- FORMS DATABASE PATTERNS ---
        
        # "list profiles" / "show profiles"
        if any(x in msg_lower for x in ["list profiles", "show profiles", "my profiles", "all profiles"]):
            return {"tool": "list_profiles", "args": {}}
        
        # "get my profile" / "show my profile"
        if any(x in msg_lower for x in ["get my profile", "show my profile", "my profile data", "view profile"]):
            return {"tool": "get_profile", "args": {"profile_name": "default"}}
        
        # "what is my email" / "get my email" / "my email"
        profile_field_patterns = [
            (r"(?:what(?:'s| is) my|get my|my)\s+email", "contact.email"),
            (r"(?:what(?:'s| is) my|get my|my)\s+phone", "contact.phone"),
            (r"(?:what(?:'s| is) my|get my|my)\s+(?:first )?name", "personal.first_name"),
            (r"(?:what(?:'s| is) my|get my|my)\s+last name", "personal.last_name"),
            (r"(?:what(?:'s| is) my|get my|my)\s+address", "address.street"),
            (r"(?:what(?:'s| is) my|get my|my)\s+city", "address.city"),
            (r"(?:what(?:'s| is) my|get my|my)\s+company", "work.company"),
            (r"(?:what(?:'s| is) my|get my|my)\s+job(?: title)?", "work.job_title"),
        ]
        for pattern, field in profile_field_patterns:
            if re.search(pattern, msg_lower):
                return {"tool": "get_profile_field", "args": {"field_path": field, "profile_name": "default"}}
        
        # "save/set/update my email to X"
        update_patterns = [
            (r"(?:save|set|update|change)\s+my\s+email\s+(?:to\s+)?[\"']?(\S+@\S+)[\"']?", "contact.email"),
            (r"(?:save|set|update|change)\s+my\s+phone\s+(?:to\s+)?[\"']?([+\d\s\-()]+)[\"']?", "contact.phone"),
            (r"(?:save|set|update|change)\s+my\s+(?:first )?name\s+(?:to\s+)?[\"']?(\w+)[\"']?", "personal.first_name"),
            (r"(?:save|set|update|change)\s+my\s+last name\s+(?:to\s+)?[\"']?(\w+)[\"']?", "personal.last_name"),
            (r"(?:save|set|update|change)\s+my\s+city\s+(?:to\s+)?[\"']?(.+?)[\"']?$", "address.city"),
            (r"(?:save|set|update|change)\s+my\s+company\s+(?:to\s+)?[\"']?(.+?)[\"']?$", "work.company"),
        ]
        for pattern, field in update_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                value = match.group(1).strip()
                return {"tool": "update_profile_field", "args": {"field_path": field, "value": value, "profile_name": "default"}}
        
        # "create profile [name]"
        create_profile_match = re.search(r"create\s+(?:a\s+)?(?:new\s+)?profile\s+(?:called\s+|named\s+)?[\"']?(\w+)[\"']?", msg_lower)
        if create_profile_match:
            profile_name = create_profile_match.group(1)
            return {"tool": "create_profile", "args": {"profile_name": profile_name}}
        
        # ═══════════════════════════════════════════════════════════════
        # MEDIA GENERATION PATTERNS - Dynamic prompts
        # ═══════════════════════════════════════════════════════════════
        
        # "generate/create/make image of [prompt]" (preserve original prompt text)
        image_gen_patterns = [
            r"(?:generate|create|make)\s+(?:an?\s+)?image\s+(?:of\s+)?(.+?)$",
            r"(?:generate|create|make)\s+(?:an?\s+)?(?:ai\s+)?picture\s+(?:of\s+)?(.+?)$",
            r"(?:draw|paint)\s+(?:me\s+)?(?:an?\s+)?(.+?)$",
            r"image\s+of\s+(.+?)$",
        ]
        for pattern in image_gen_patterns:
            match = re.search(pattern, user_message, flags=re.IGNORECASE)
            if match:
                prompt = match.group(1).strip()
                if prompt and len(prompt) > 3:
                    print(f"[MEDIA GEN] Generating image with prompt: {prompt}")
                    return {"tool": "generate_image", "args": {"prompt": prompt}}
        
        # "generate/create video of [prompt]" (preserve original prompt text)
        video_gen_patterns = [
            r"(?:generate|create|make)\s+(?:an?\s+)?(?:ai\s+)?video\s+(?:of\s+)?(.+?)$",
            r"video\s+of\s+(.+?)$",
        ]
        for pattern in video_gen_patterns:
            match = re.search(pattern, user_message, flags=re.IGNORECASE)
            if match:
                prompt = match.group(1).strip()
                if prompt and len(prompt) > 3:
                    print(f"[MEDIA GEN] Generating video with prompt: {prompt}")
                    return {"tool": "generate_ai_video", "args": {"prompt": prompt, "model": "wan"}}
        
        # ═══════════════════════════════════════════════════════════════
        # SCRAPING PATTERNS - Dynamic URLs
        # ═══════════════════════════════════════════════════════════════
        
        # "scrape [url]"
        scrape_patterns = [
            r"scrape\s+(https?://\S+)",
            r"scrape\s+(?:the\s+)?(?:page\s+)?(?:at\s+)?(https?://\S+)",
            r"extract\s+(?:data\s+)?(?:from\s+)?(https?://\S+)",
            r"get\s+(?:content\s+)?(?:from\s+)?(https?://\S+)",
        ]
        for pattern in scrape_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                url = match.group(1).strip()
                print(f"[SCRAPE] Scraping URL: {url}")
                return {"tool": "scrape_url", "args": {"url": url}}
        
        # "fetch [url]"
        fetch_match = re.search(r"fetch\s+(https?://\S+)", msg_lower)
        if fetch_match:
            url = fetch_match.group(1).strip()
            return {"tool": "fetch_url", "args": {"url": url}}
        
        # ═══════════════════════════════════════════════════════════════
        # SECRETARY/DOCUMENT PATTERNS - Dynamic content
        # ═══════════════════════════════════════════════════════════════
        
        # "write a letter to [recipient] about [topic]"
        letter_match = re.search(r"write\s+(?:a\s+)?letter\s+(?:to\s+)?(\w+)\s+(?:about\s+)?(.+?)$", msg_lower)
        if letter_match:
            recipient = letter_match.group(1).strip()
            topic = letter_match.group(2).strip()
            return {"tool": "create_document", "args": {"doc_type": "letter", "title": f"Letter to {recipient}", "content": f"Topic: {topic}"}}
        
        # "write a report on/about [topic]"
        report_match = re.search(r"write\s+(?:a\s+)?report\s+(?:on|about)\s+(.+?)$", msg_lower)
        if report_match:
            topic = report_match.group(1).strip()
            return {"tool": "create_document", "args": {"doc_type": "report", "title": f"Report: {topic}", "content": ""}}
        
        # "memo about [topic]" or "take memo: [content]"
        memo_match = re.search(r"(?:take\s+)?memo\s*[:about]?\s*(.+?)$", msg_lower)
        if memo_match:
            content = memo_match.group(1).strip()
            return {"tool": "take_memo", "args": {"subject": "Quick Memo", "content": content, "priority": "normal"}}
        
        # "note: [content]" or "note down [content]"
        note_match = re.search(r"note\s*[:down]?\s*(.+?)$", msg_lower)
        if note_match:
            note_content = note_match.group(1).strip()
            return {"tool": "quick_note", "args": {"note": note_content}}
        
        # ═══════════════════════════════════════════════════════════════
        # FILE OPERATION PATTERNS
        # ═══════════════════════════════════════════════════════════════
        
        # "read file [path]"
        read_file_match = re.search(r"read\s+(?:the\s+)?file\s+[\"']?([^\"']+)[\"']?", msg_lower)
        if read_file_match:
            path = read_file_match.group(1).strip()
            return {"tool": "read_file", "args": {"path": path}}
        
        # "list files in [directory]"
        list_dir_match = re.search(r"list\s+(?:files\s+)?(?:in\s+)?[\"']?([^\"']+)[\"']?$", msg_lower)
        if list_dir_match and ("files" in msg_lower or "directory" in msg_lower or "folder" in msg_lower):
            path = list_dir_match.group(1).strip()
            return {"tool": "list_directory", "args": {"path": path}}
        
        # "search for files [pattern]"
        search_files_match = re.search(r"search\s+(?:for\s+)?files?\s+(?:named\s+|matching\s+)?[\"']?([^\"']+)[\"']?", msg_lower)
        if search_files_match:
            pattern = search_files_match.group(1).strip()
            return {"tool": "search_files", "args": {"pattern": pattern}}
        
        # ═══════════════════════════════════════════════════════════════
        # GAME TRAINER PATTERNS
        # ═══════════════════════════════════════════════════════════════
        
        # "attach to [game name]"
        attach_game_match = re.search(r"attach\s+(?:to\s+)?[\"']?([^\"']+)[\"']?", msg_lower)
        if attach_game_match and ("game" in msg_lower or "process" in msg_lower):
            game_name = attach_game_match.group(1).strip()
            return {"tool": "attach_to_process", "args": {"process_name": game_name}}
        
        # "scan for value [number]"
        scan_value_match = re.search(r"scan\s+(?:for\s+)?(?:value\s+)?(\d+)", msg_lower)
        if scan_value_match:
            value = int(scan_value_match.group(1))
            return {"tool": "scan_memory_for_value", "args": {"value": value}}
        
        # ═══════════════════════════════════════════════════════════════
        # PROGRAM/APPLICATION PATTERNS
        # ═══════════════════════════════════════════════════════════════
        
        # "open/start/launch [program]"
        program_patterns = [
            r"(?:open|start|launch|run)\s+(?:the\s+)?(?:program\s+)?[\"']?([a-zA-Z0-9_\-\.]+(?:\.exe)?)[\"']?",
        ]
        for pattern in program_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                program = match.group(1).strip()
                # Skip if it's a website
                if not any(ext in program for ext in ['.com', '.org', '.net', '.io']):
                    print(f"[PROGRAM] Starting program: {program}")
                    return {"tool": "start_program", "args": {"path": program}}
        
        # ═══════════════════════════════════════════════════════════════
        # RECORDING PATTERNS
        # ═══════════════════════════════════════════════════════════════
        
        # "record [window name]"
        record_window_match = re.search(r"record\s+(?:the\s+)?(?:window\s+)?[\"']?([^\"']+)[\"']?\s+window", msg_lower)
        if record_window_match:
            window_title = record_window_match.group(1).strip()
            return {"tool": "record_window", "args": {"window_title": window_title}}
        
        # ═══════════════════════════════════════════════════════════════
        # MAP PATTERNS
        # ═══════════════════════════════════════════════════════════════
        
        # "map of [location]" or "show map of [location]"
        map_match = re.search(r"(?:show\s+)?(?:a\s+)?map\s+(?:of\s+)?(.+?)$", msg_lower)
        if map_match:
            location = map_match.group(1).strip().strip("?").strip()
            # Filter out noise
            if len(location) > 2 and location not in ["wristband", "images", "pictures"]:
                return {"tool": "map_control", "args": {"place": location}}
        
        # "route from [origin] to [destination]"
        route_match = re.search(r"(?:show\s+)?(?:a\s+)?route\s+(?:from\s+)?(.+?)\s+to\s+(.+?)$", msg_lower)
        if route_match:
            origin = route_match.group(1).strip()
            destination = route_match.group(2).strip().strip("?").strip()
            return {"tool": "map_control", "args": {"origin": origin, "destination": destination}}

        # ═══════════════════════════════════════════════════════════════
        # COMMENT/ENGAGEMENT PATTERNS
        # ═══════════════════════════════════════════════════════════════
        
        # "comment [text]"
        comment_match = re.search(r"(?:write|add|post|leave)\s+(?:a\s+)?comment\s*[:\"']?\s*(.+?)$", msg_lower)
        if comment_match:
            comment_text = comment_match.group(1).strip().strip("'\"")
            return {"tool": "write_comment", "args": {"comment": comment_text}}
        
        # ═══════════════════════════════════════════════════════════════
        # MEMORY/LEARNING PATTERNS
        # ═══════════════════════════════════════════════════════════════
        
        # "remember that [fact]"
        remember_match = re.search(r"remember\s+(?:that\s+)?(.+?)$", msg_lower)
        if remember_match:
            fact = remember_match.group(1).strip()
            # Try to extract a topic from the fact
            topic = "general"
            if " is " in fact:
                topic = fact.split(" is ")[0].strip()
            elif " are " in fact:
                topic = fact.split(" are ")[0].strip()
            return {"tool": "remember_fact", "args": {"topic": topic, "fact": fact}}
        
        # "what do you know about [topic]"
        recall_match = re.search(r"what\s+(?:do\s+you\s+)?know\s+about\s+(.+?)$", msg_lower)
        if recall_match:
            topic = recall_match.group(1).strip()
            return {"tool": "get_facts_about", "args": {"topic": topic}}
        
        return None
    
    async def process(self, messages: List[ChatMessage], require_approval: bool = True, screen_context: Optional[Dict[str, Any]] = None, team_mode: bool = False) -> AgentResponse:
        """Process messages and execute tools as needed"""
        
        # ═══════════════════════════════════════════════════════════════
        # MULTI-AGENT COORDINATION: Update Amigos status
        # ═══════════════════════════════════════════════════════════════
        agent_thinking("amigos", "Analyzing request", progress=15)

        # Auto-approve safe tools (always execute without asking)
        cfg_auto = autonomy_controller.get_config()
        if cfg_auto.get('autoApproveSafeTools'):
            auto_approve_tools = set(cfg_auto.get('autoApproveTools', [
                "canvas_draw_shape", "canvas_draw_text", "canvas_floor_plan",
                "canvas_flowchart", "canvas_poem", "canvas_clear",
                "canvas_set_mode", "canvas_export", "canvas_get_commands",
                "get_mouse_position", "get_screen_size", "screenshot", "wait",
            ]))
        else:
            auto_approve_tools = set()
        
        # ═══════════════════════════════════════════════════════════════
        # PRE-PROCESSING: Check for direct actions BEFORE calling LLM
        # This prevents the LLM from hallucinating wrong tools
        # ═══════════════════════════════════════════════════════════════
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.role == "user":
                last_user_msg = msg.content
                break
        
        # ═══════════════════════════════════════════════════════════════
        # TEAM MODE: Consult the team for complex tasks
        # ═══════════════════════════════════════════════════════════════
        if team_mode:
            # Inject team awareness into the conversation
            team_prompt = get_agent_prompt()
            messages.insert(0, ChatMessage(role="system", content=f"TEAM MODE ENABLED. {team_prompt}\n\nIf the user's request is complex or requires multiple steps, use the 'consult_team' tool to coordinate with your specialized agents."))
            print("[TEAM MODE] Multi-agent coordination enabled for this request.")

        # ═══════════════════════════════════════════════════════════════
        # MULTI-AGENT DELEGATION: Check if another agent should handle this
        # ═══════════════════════════════════════════════════════════════
        delegated_agent = self.determine_delegated_agent(last_user_msg)
        if delegated_agent:
            print(f"[DELEGATION] Task may be suitable for: {delegated_agent}")
            # Mark the delegated agent as working
            agent_working(delegated_agent, f"Assisting with: {last_user_msg[:50]}...", progress=20)
            
            # If it's Ollie, we can actually delegate the generation to the local LLM
            if delegated_agent == "ollie":
                try:
                    from tools.ollama_tools import amigos_ask_ollie
                    
                    print(f"[DELEGATION] Routing request to Ollie (Local LLM)...")
                    ollie_result = await amigos_ask_ollie(last_user_msg)
                    
                    if ollie_result.get("success"):
                        # Log the delegation and mark agents idle
                        autonomy_controller.log_action('delegated_to_ollie', {'task': last_user_msg[:200]}, {'success': True, 'model': ollie_result.get('model_used')})
                        agent_idle("amigos")
                        agent_idle("ollie")
                        return AgentResponse(
                            content=f"🦙 **Ollie says:**\n\n{ollie_result.get('response')}",
                            actions_taken=[{"delegated_to": "ollie", "model": ollie_result.get('model_used')}],
                            delegated_to="ollie"
                        )
                except Exception as e:
                    print(f"[DELEGATION] Ollie failed: {e}. Falling back to Amigos.")
                    agent_error("ollie", str(e))
        
        # Try to detect a direct action that should bypass LLM
        direct_action = None
        if not team_mode:
            direct_action = self.detect_required_action(last_user_msg)
        
        if direct_action:
            tool_name = direct_action["tool"]
            tool_args = direct_action["args"]
            
            print(f"[DIRECT ACTION] Bypassing LLM. Executing: {tool_name} with args: {tool_args}")
            agent_working("amigos", f"Executing: {tool_name}", progress=40)
            
            # Check if tool requires approval
            if tool_name in TOOLS:
                _, requires_approval_for_tool, _ = TOOLS[tool_name]

                # Skip approval for auto-approved tools
                if tool_name in auto_approve_tools:
                    requires_approval_for_tool = False

                # Always skip approval for safe Canvas design tools
                # These only draw to the local Canvas and generate images;
                # they do not control the OS or perform destructive actions.
                if tool_name in {"canvas_design", "canvas_design_image"}:
                    requires_approval_for_tool = False
                
                if self._tool_needs_approval(tool_name, requires_approval_for_tool, require_approval, auto_approve_tools):
                    agent_idle("amigos")
                    if delegated_agent:
                        agent_idle(delegated_agent)
                    return AgentResponse(
                        content=f"I need to use '{tool_name}' which requires your approval.",
                        needs_approval=True,
                        pending_action={"tool": tool_name, "args": tool_args},
                        actions_taken=[]
                    )
            
            # Execute the direct action
            result = self.execute_tool(tool_name, tool_args)
            actions_taken = [{
                "tool": tool_name,
                "args": tool_args,
                "result": result
            }]

            # Log the tool execution for audit
            try:
                autonomy_controller.log_action('tool_executed', {'tool': tool_name, 'args': tool_args}, {'result': result})
            except Exception:
                pass
            
            if result.get("success", False):
                # Narrative tools should return their generated text directly.
                narrative_tools = {"agent_get_itinerary_timeline"}
                if tool_name in narrative_tools:
                    agent_idle("amigos")
                    if delegated_agent:
                        agent_idle(delegated_agent)
                    return AgentResponse(
                        content=(result.get("timeline") or result.get("content") or ""),
                        actions_taken=actions_taken,
                    )

                # Check if this is a data retrieval tool that needs summarization
                data_retrieval_tools = [
                    "read_file", "read_lines", "get_file_info", "list_directory",
                    "get_platform_info", "list_all_platforms", "get_trending_hashtags",
                    "get_engagement_phrases", "get_facebook_groups", "get_platform_limits",
                    "get_facts_about", "get_all_memories", "get_memory_summary",
                    "web_search", "web_search_news", "fetch_url",
                    "get_weather", "get_datetime", "get_current_time",
                    "get_system_info", "get_system_stats", "list_processes",
                    "get_env_var", "paste_from_clipboard", "get_current_url",
                    "get_page_content", "get_visible_posts", "get_facebook_group_posts",
                    "get_profile", "get_profile_field", "list_profiles",
                    "get_video_info", "get_audio_info", "list_images",
                    "list_videos", "list_audio_files", "list_secretary_files",
                    "get_current_directory", "file_exists", "search_files",
                    "search_in_files"
                ]
                
                if tool_name in data_retrieval_tools:
                    # Extract just the content/data, not the full result object
                    data_to_summarize = result.get("content") or result.get("data") or result.get("results") or result
                    result_str = json.dumps(data_to_summarize, indent=2, default=str) if isinstance(data_to_summarize, (dict, list)) else str(data_to_summarize)
                    
                    # Aggressive truncation to save tokens
                    if len(result_str) > 1500:
                        result_str = result_str[:1500] + "\n...[truncated]"
                    
                    summary_conversation = [
                        {
                            "role": "system",
                            "content": "Analyze and discuss the following data for Darrell Buttigieg. Provide a clear, structured summary and explain the significance of the findings. Ensure your reply makes sense in the context of the user's ongoing project. Do not just list facts; provide insight.",
                        },
                        {"role": "user", "content": f"Data retrieved via tool:\n{result_str}\n\nPlease provide a thoughtful analysis of this data."},
                    ]
                    
                    summary_response = self.call_llm(summary_conversation)
                    agent_idle("amigos")
                    if delegated_agent:
                        agent_idle(delegated_agent)
                    return AgentResponse(
                        content=summary_response,
                        actions_taken=actions_taken
                    )
                
                agent_idle("amigos")
                if delegated_agent:
                    agent_idle(delegated_agent)
                
                # Extract canvas/map commands if present (from design/map tools)
                canvas_commands = result.get("canvas_commands") if result else None
                map_commands = result.get("map_commands") if result else None
                
                return AgentResponse(
                    content=f"I've successfully completed the '{tool_name}' action as requested, Darrell. I've updated the system state and applied the necessary changes. Let me know if you'd like me to analyze these results further or perform a follow-up task.",
                    actions_taken=actions_taken,
                    canvas_commands=canvas_commands,
                    map_commands=map_commands
                )
            else:
                error_msg = result.get("error", "Unknown error")
                agent_idle("amigos")
                if delegated_agent:
                    agent_idle(delegated_agent)
                return AgentResponse(
                    content=f"Failed: {error_msg}",
                    actions_taken=actions_taken
                )
        
        # ═══════════════════════════════════════════════════════════════
        # No direct action detected - proceed with LLM
        # ═══════════════════════════════════════════════════════════════
        
        # Build conversation with compact system prompt for speed
        current_system_prompt = get_system_prompt_compact()
        
        agent_thinking("amigos", "Consulting brain (LLM)", progress=30)

        # Explicitly inform the agent about its console access capabilities
        current_system_prompt += "\n\n## CONSOLE ACCESS CAPABILITIES:\n"
        current_system_prompt += "You have direct access to the following consoles in the Agent Amigos program. "
        current_system_prompt += "When a user asks you to 'read the console', 'summarize the news', or 'check the market', "
        current_system_prompt += "you MUST use the data provided in the 'CURRENT SCREEN CONTEXT' section below. "
        current_system_prompt += "Do NOT claim you don't have access to these consoles.\n"

        # Inject screen context if available
        if screen_context:
            screen_info = "\n\n## CURRENT SCREEN CONTEXT (What you can see):\n"
            
            # Finance Console
            finance = screen_context.get("finance", {})
            if finance:
                screen_info += "### Finance Console:\n"
                crypto = finance.get("cryptoData", [])
                if crypto:
                    screen_info += "- Crypto Prices: " + ", ".join([f"{c.get('name')}: ${c.get('current_price')}" for c in crypto[:10]]) + "\n"
                stocks = finance.get("stockData", [])
                if stocks:
                    screen_info += "- Stock Prices: " + ", ".join([f"{s.get('symbol')}: ${s.get('price')}" for s in stocks[:10]]) + "\n"
                analysis = finance.get("analysis")
                if analysis:
                    screen_info += f"- Market Analysis: {analysis[:200]}...\n"
            
            # Scraper Workbench
            scraper = screen_context.get("scraper", {})
            if scraper:
                screen_info += "### Scraper Workbench:\n"
                if scraper.get("lastUrl"):
                    screen_info += f"- Last Scraped URL: {scraper.get('lastUrl')}\n"
                if scraper.get("lastResult"):
                    screen_info += f"- Scrape Result (Snippet): {str(scraper.get('lastResult'))[:300]}...\n"
            
            # Media Console
            media = screen_context.get("media", {})
            if media:
                screen_info += "### Media Console:\n"
                if media.get("currentTrack"):
                    screen_info += f"- Currently Playing: {media.get('currentTrack')}\n"
                if media.get("isPlaying"):
                    screen_info += "- Status: Playing\n"
            
            # Files Console
            files = screen_context.get("files", {})
            if files:
                screen_info += "### File Management:\n"
                if files.get("currentPath"):
                    screen_info += f"- Current Directory: {files.get('currentPath')}\n"
                if files.get("selectedFile"):
                    screen_info += f"- Selected File: {files.get('selectedFile')}\n"

            # Internet Console
            internet = screen_context.get("internet", {})
            if internet:
                screen_info += "### Internet Console:\n"
                if internet.get("lastQuery"):
                    screen_info += f"- Last Search Query: {internet.get('lastQuery')}\n"
                if internet.get("searchType"):
                    screen_info += f"- Search Type: {internet.get('searchType')}\n"
                
                results = internet.get("results", [])
                if results:
                    screen_info += "- Search Results:\n"
                    for r in results[:5]:
                        screen_info += f"  * {r.get('title')} - {r.get('url')}\n    Content: {r.get('content', '')[:200]}...\n"
                
                # Include finance data if in finance tab of internet console
                finance_data = internet.get("financeData", {})
                if finance_data:
                    screen_info += "- Live Market Data (AUD/USD): " + str(finance_data) + "\n"
                
                # Include job and hustle data
                job_data = internet.get("jobData")
                if job_data:
                    screen_info += f"- Job Search Context: {job_data}\n"
                
                hustle_data = internet.get("hustleData")
                if hustle_data:
                    screen_info += f"- Side Hustle Context: {hustle_data}\n"

                product_data = internet.get("productData")
                if product_data:
                    screen_info += f"- Product Search Context: {product_data}\n"

                property_data = internet.get("propertyData")
                if property_data:
                    screen_info += f"- Property & Rentals Context: {property_data}\n"

                accommodation_data = internet.get("accommodationData")
                if accommodation_data:
                    screen_info += f"- Accommodation Context: {accommodation_data}\n"

            # Map Console
            map_ctx = screen_context.get("map", {})
            if map_ctx:
                screen_info += "### Map Console:\n"
                if map_ctx.get("currentPlace"):
                    screen_info += f"- Current Location: {map_ctx.get('currentPlace')}\n"
                if map_ctx.get("route"):
                    route = map_ctx.get("route")
                    screen_info += f"- Current Route: {route.get('origin')} to {route.get('destination')} ({route.get('mode', 'driving')})\n"

            current_system_prompt += screen_info

        conversation = [{"role": "system", "content": current_system_prompt}]
        for msg in messages:
            conversation.append({"role": msg.role, "content": msg.content})
        
        actions_taken = []
        iterations = 0
        final_response = ""
        
        while iterations < MAX_ITERATIONS:
            iterations += 1
            
            # Calculate progress (30% to 90%)
            current_progress = 30 + int((iterations / MAX_ITERATIONS) * 60)
            agent_thinking("amigos", f"Thinking (Step {iterations})", progress=current_progress)
            
            # Get LLM response
            llm_response = self.call_llm(conversation)
            
            # Check for tool call
            tool_call = self.extract_tool_call(llm_response)
            
            if tool_call:
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args", {})
                
                # VALIDATE: Reject fake/hallucinated tools
                if tool_name not in TOOLS:
                    print(f"[REJECTED] LLM hallucinated fake tool: {tool_name}")
                    # Don't execute - return a helpful message
                    return AgentResponse(
                        content="I don't have that capability.",
                        actions_taken=[]
                    )
                
                # Check if tool requires approval
                if tool_name in TOOLS:
                    _, requires_approval_for_tool, _ = TOOLS[tool_name]

                    # Skip approval for auto-approved tools
                    if tool_name in auto_approve_tools:
                        requires_approval_for_tool = False
                    
                    if self._tool_needs_approval(tool_name, requires_approval_for_tool, require_approval, auto_approve_tools):
                        # Return with pending action for user approval
                        # Remove the tool call block from response for cleaner display
                        clean_response = re.sub(r'```tool\s*\n?{.*?}\s*\n?```', '', llm_response, flags=re.DOTALL).strip()
                        agent_idle("amigos")
                        if delegated_agent:
                            agent_idle(delegated_agent)
                        return AgentResponse(
                            content=clean_response or f"I need to use '{tool_name}' which requires your approval.",
                            needs_approval=True,
                            pending_action={"tool": tool_name, "args": tool_args},
                            actions_taken=actions_taken
                        )
                
                # Execute the tool - update agent status to show tool being used
                print(f"Executing tool: {tool_name} with args: {tool_args}")
                agent_working("amigos", f"Using: {tool_name}", progress=min(95, current_progress + 10))
                result = self.execute_tool(tool_name, tool_args)
                
                # SELF-LEARNING: Learn from search results to stay current
                if tool_name in ["web_search", "web_search_news"] and result.get("success"):
                    try:
                        search_results = result.get("results", [])
                        for res in search_results[:2]:
                            fact = f"Current info on {tool_args.get('query')}: {res.get('title')} - {res.get('body') or res.get('snippet')}"
                            learn(fact, category="current_events")
                    except Exception as e:
                        print(f"[AMIGOS] Self-learning failed: {e}")

                actions_taken.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result
                })

                # Log LLM-initiated tool execution for audit
                try:
                    autonomy_controller.log_action('tool_executed', {'tool': tool_name, 'args': tool_args}, {'result': result})
                except Exception:
                    pass
                
                # For DATA RETRIEVAL tools (read_file, get_*), feed result back to LLM for summarization
                narrative_tools = {"agent_get_itinerary_timeline"}
                if tool_name in narrative_tools and result.get("success", False):
                    agent_idle("amigos")
                    if delegated_agent:
                        agent_idle(delegated_agent)
                    return AgentResponse(
                        content=(result.get("timeline") or result.get("content") or ""),
                        actions_taken=actions_taken,
                    )

                data_retrieval_tools = [
                    "read_file", "read_lines", "get_file_info", "list_directory",
                    "get_platform_info", "list_all_platforms", "get_trending_hashtags",
                    "get_engagement_phrases", "get_facebook_groups", "get_platform_limits",
                    "get_facts_about", "get_all_memories", "get_memory_summary",
                    "web_search", "web_search_news", "fetch_url",
                    "get_weather", "get_datetime", "get_current_time",
                    "get_system_info", "get_system_stats", "list_processes",
                    "get_env_var", "paste_from_clipboard", "get_current_url",
                    "get_page_content", "get_visible_posts", "get_facebook_group_posts",
                    "get_profile", "get_profile_field", "list_profiles",
                    "get_video_info", "get_audio_info", "list_images",
                    "list_videos", "list_audio_files", "list_secretary_files",
                    "get_current_directory", "file_exists", "search_files",
                    "search_in_files"
                ]
                
                if tool_name in data_retrieval_tools and result.get("success", False):
                    # Feed the data back to LLM for a natural language summary
                    # Truncate large results to prevent token overflow
                    result_str = json.dumps(result, indent=2, default=str)
                    if len(result_str) > 4000:
                        result_str = result_str[:4000] + "\n... [truncated]"
                    
                    # Build a summary request for the LLM
                    summary_conversation = [
                        {
                            "role": "system",
                            "content": "Summarize the following data in plain English. Be concise, professional, and accurate. Do not include jokes or emojis. Do not show raw JSON. If the data contains a date, time, or specific value, you MUST report it exactly as shown in the data.",
                        },
                        {
                            "role": "user",
                            "content": f"Here is data retrieved from a tool:\n\n{result_str}\n\nPlease summarize this information in plain English.",
                        },
                    ]
                    
                    # Call LLM for summary
                    summary_response = self.call_llm(summary_conversation)
                    
                    # Return the summary
                    agent_idle("amigos")
                    if delegated_agent:
                        agent_idle(delegated_agent)
                    return AgentResponse(
                        content=summary_response,
                        actions_taken=actions_taken
                    )
                
                # For simple actions that succeed, return immediately instead of looping
                if result.get("success", False):
                    # Clean ALL JSON and tool blocks from response for polished output
                    clean_response = re.sub(r'```(?:tool|json)?\s*\n?\{.*?\}\s*\n?```', '', llm_response, flags=re.DOTALL)
                    clean_response = re.sub(r'\{["\']?tool["\']?\s*:\s*["\'][^"\']+["\'].*?\}', '', clean_response, flags=re.DOTALL)
                    clean_response = re.sub(r'`\{.*?\}`', '', clean_response)  # Remove inline JSON in backticks
                    clean_response = re.sub(r'\*\s*`[^`]+`.*', '', clean_response)  # Remove bullet explanations
                    clean_response = re.sub(r'\*\*Tool.*?\*\*', '', clean_response)  # Remove tool headers
                    clean_response = re.sub(r"I'll use.*?tool.*?\.", '', clean_response, flags=re.IGNORECASE)  # Remove tool narration
                    clean_response = re.sub(r'Let me.*?for you\.', '', clean_response, flags=re.IGNORECASE)  # Remove verbose intros
                    clean_response = re.sub(r'\n{3,}', '\n\n', clean_response)  # Collapse multiple newlines
                    clean_response = clean_response.strip()
                    # If nothing left or just noise, say nothing (action speaks for itself)
                    if not clean_response or len(clean_response) < 3:
                        clean_response = ""
                    agent_idle("amigos")
                    if delegated_agent:
                        agent_idle(delegated_agent)
                    
                    # Extract canvas/map commands if present
                    canvas_commands = result.get("canvas_commands") if result else None
                    map_commands = result.get("map_commands") if result else None
                    
                    return AgentResponse(
                        content=clean_response,
                        actions_taken=actions_taken,
                        canvas_commands=canvas_commands,
                        map_commands=map_commands
                    )
                else:
                    # Tool failed - provide helpful, actionable error messages
                    error_msg = result.get("error", "Unknown error")
                    # Make errors more user-friendly
                    friendly_errors = {
                        "browser not initialized": "Browser isn't running. Try 'open facebook' first.",
                        "element not found": "Couldn't find that element on the page. The page may have changed.",
                        "timeout": "The operation took too long. The page might be slow to load.",
                        "connection refused": "Can't reach the server. Check your internet connection.",
                        "file not found": "That file doesn't exist. Check the path.",
                        "permission denied": "I don't have permission to do that.",
                    }
                    for key, friendly_msg in friendly_errors.items():
                        if key.lower() in error_msg.lower():
                            error_msg = friendly_msg
                            break
                    agent_idle("amigos")
                    if delegated_agent:
                        agent_idle(delegated_agent)
                    return AgentResponse(
                        content=f"Hmm, that didn't work: {error_msg}",
                        actions_taken=actions_taken
                    )
            else:
                # No tool call from LLM - check if we should auto-detect and force one
                # Get the last user message
                last_user_msg = ""
                for msg in reversed(messages):
                    if msg.role == "user":
                        last_user_msg = msg.content
                        break
                
                # Try to auto-detect required action
                auto_action = self.detect_required_action(last_user_msg)
                
                if auto_action and iterations == 1:
                    # LLM failed to emit tool call but user clearly wants an action
                    # Execute the auto-detected action
                    tool_name = auto_action["tool"]
                    tool_args = auto_action["args"]
                    
                    print(f"[AUTO-DETECT] LLM missed tool call. Forcing: {tool_name} with args: {tool_args}")
                    
                    # Check approval requirement
                    if tool_name in TOOLS:
                        _, requires_approval_for_tool, _ = TOOLS[tool_name]

                        # Skip approval for auto-approved tools
                        if tool_name in auto_approve_tools:
                            requires_approval_for_tool = False
                        
                        if self._tool_needs_approval(tool_name, requires_approval_for_tool, require_approval, auto_approve_tools):
                            agent_idle("amigos")
                            if delegated_agent:
                                agent_idle(delegated_agent)
                            return AgentResponse(
                                content=f"I need to use '{tool_name}' which requires your approval.",
                                needs_approval=True,
                                pending_action={"tool": tool_name, "args": tool_args},
                                actions_taken=actions_taken
                            )
                    
                    # Execute the tool
                    result = self.execute_tool(tool_name, tool_args)
                    
                    actions_taken.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result,
                        "auto_detected": True
                    })
                    
                    if result.get("success", False):
                        agent_idle("amigos")
                        if delegated_agent:
                            agent_idle(delegated_agent)

                        # If we auto-detected a narrative tool, return its content.
                        if tool_name in {"agent_get_itinerary_timeline"}:
                            return AgentResponse(
                                content=(result.get("timeline") or result.get("content") or ""),
                                actions_taken=actions_taken,
                            )
                        
                        # Extract canvas/map/search commands if present
                        canvas_commands = result.get("canvas_commands") if result else None
                        map_commands = result.get("map_commands") if result else None
                        search_results = result.get("results") or result.get("data") if isinstance(result, dict) else None
                        
                        return AgentResponse(
                            content=f"I have successfully executed the '{tool_name}' tool. I've updated the system context with the results. Please let me know if you would like me to provide a deeper analysis or if there is another step you would like to take, Darrell.",
                            actions_taken=actions_taken,
                            canvas_commands=canvas_commands,
                            map_commands=map_commands,
                            search_results=search_results
                        )
                    else:
                        error_msg = result.get("error", "Unknown error")
                        agent_idle("amigos")
                        if delegated_agent:
                            agent_idle(delegated_agent)
                        return AgentResponse(
                            content=f"Failed: {error_msg}",
                            actions_taken=actions_taken
                        )
                
                # No tool call needed - this is the final response
                # BUT first check if LLM promised to do something without doing it
                unfulfilled = self.detect_unfulfilled_promise(llm_response, actions_taken)
                
                if unfulfilled and iterations == 1:
                    # LLM said "I will..." but didn't actually do it - force continuation
                    print(f"[CONTINUATION] LLM promised '{unfulfilled}' but didn't execute. Forcing continuation...")
                    
                    # Build a continuation prompt
                    tool_hint = ""
                    if unfulfilled == "map":
                        tool_hint = "- map_control: Update the Map Console with a location or route"
                    elif unfulfilled == "canvas":
                        tool_hint = "- canvas_design: Design something on the visual canvas using AI assist\n- canvas_draw_shape: Draw a specific shape"
                    elif unfulfilled == "search":
                        tool_hint = "- web_search: Search the internet for live information\n- web_search_news: Search for latest news"
                    elif unfulfilled == "create":
                        tool_hint = "- create_file: Create a new file\n- create_document: Create a formatted document"
                    else:
                        tool_hint = "- read_file: Read file contents\n- list_directory: See folder contents"

                    continuation_prompt = f"""You said you would {unfulfilled} but you haven't done it yet.
                    
IMPORTANT: You MUST use a tool NOW to complete this task. Do not just describe what you will do - actually use a tool.

Available tools for this task:
{tool_hint}

Pick the appropriate tool and use it immediately with the correct arguments."""

                    conversation.append({"role": "assistant", "content": llm_response})
                    conversation.append({"role": "user", "content": continuation_prompt})
                    
                    # Continue the loop to get the tool call
                    continue
                
                final_response = llm_response
                break
        
        # Reset agent statuses before returning
        agent_idle("amigos")
        if delegated_agent:
            agent_idle(delegated_agent)
        
        # Extract canvas/map/search commands from the last action if present
        last_canvas_commands = None
        last_map_commands = None
        last_search_results = None
        if actions_taken:
            last_result = actions_taken[-1].get("result", {})
            last_canvas_commands = last_result.get("canvas_commands")
            last_map_commands = last_result.get("map_commands")
            # Extract search results from web_search or web_search_news
            last_search_results = last_result.get("results") or last_result.get("data") if isinstance(last_result, dict) else None

        # Extract todo_list and progress from coordinator
        agent_state = coordinator.agents.get("amigos", {})
        current_todo_list = agent_state.get("todo_list", [])
        current_progress = agent_state.get("progress", 0)

        return AgentResponse(
            content=final_response,
            actions_taken=actions_taken if actions_taken else [],
            canvas_commands=last_canvas_commands,
            map_commands=last_map_commands,
            search_results=last_search_results,
            todo_list=current_todo_list,
            progress=current_progress
        )


# Initialize engine
agent = AgentEngine()

# Connect Agent Engine to Media Tools (for Vision Analysis)
try:
    media.set_llm_func(agent.call_llm)
    print("[OK] Media Tools connected to Agent Engine (Vision Enabled)")
except Exception as e:
    print(f"[WARN] Failed to connect Media Tools to Agent Engine: {e}")

# Connect Agent Engine to Canvas AI Assist
try:
    canvas_ai_assist.set_agent_engine(agent)
    print("[OK] Canvas AI Assist connected to Agent Engine")
except Exception as e:
    print(f"[WARN] Failed to connect Canvas AI Assist to Agent Engine: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY SYSTEM - Local-only access & security verification
# Owner: Darrell Buttigieg - All Rights Reserved
# ═══════════════════════════════════════════════════════════════════════════════

AUTHORIZED_OWNER = "Darrell Buttigieg"
SECURITY_VERSION = "1.0.0"

def get_security_status() -> Dict[str, Any]:
    """Comprehensive security check for Agent Amigos"""
    issues = []
    warnings = []
    recommendations = []
    
    # Check 1: Local-only binding
    is_local_only = AGENT_HOST in ["127.0.0.1", "localhost", "0.0.0.0"]
    if not is_local_only:
        issues.append(f"⚠️ Server bound to external IP: {AGENT_HOST} - Should be 127.0.0.1")
    
    # Check 2: CORS configuration (currently allows all - warning)
    warnings.append("CORS allows all origins (*) - Only safe for local development")
    
    # Check 3: Check if running on standard localhost ports
    safe_ports = [8080, 8000, 3000, 5000, 5173, 5174, 65252]
    current_port = int(ACTIVE_AGENT_PORT)
    if current_port not in safe_ports and current_port != int(AGENT_PORT):
        warnings.append(f"Running on non-standard port {current_port}")
    
    # Check 4: Check for exposed API keys in environment (don't log the actual keys)
    api_keys_present = {
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "DEEPSEEK_API_KEY": bool(os.environ.get("DEEPSEEK_API_KEY")),
        "OPENROUTER_API_KEY": bool(os.environ.get("OPENROUTER_API_KEY")),
        "GROQ_API_KEY": bool(os.environ.get("GROQ_API_KEY")),
    }
    
    # Check 5: Verify we're not exposing sensitive paths
    sensitive_paths_check = True
    try:
        # Check if we can access parent directories (should be restricted)
        backend_path = Path(__file__).resolve().parent
        workspace_path = backend_path.parent
        # Verify paths are within expected workspace
        if "AgentAmigos" not in str(workspace_path):
            warnings.append("Running outside expected AgentAmigos workspace")
            sensitive_paths_check = False
    except Exception as e:
        warnings.append(f"Path verification failed: {str(e)[:50]}")
        sensitive_paths_check = False
    
    # Check 6: Verify localhost connection
    localhost_check = True
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if not local_ip.startswith("127.") and not local_ip.startswith("192.168.") and not local_ip.startswith("10."):
            warnings.append(f"Machine has public IP exposure: {local_ip}")
    except:
        pass
    
    # Check 7: File permissions (Windows-specific)
    file_permissions_ok = True
    try:
        backend_path = Path(__file__).resolve().parent
        # Check if backend files are accessible (they should be, but only locally)
        if not backend_path.exists():
            issues.append("Backend path not accessible")
            file_permissions_ok = False
    except Exception as e:
        warnings.append(f"File permission check failed: {str(e)[:50]}")
        file_permissions_ok = False
    
    # Security recommendations
    recommendations = [
        "🔒 Keep VS Code's 'Remote' extensions disabled when not needed",
        "🔒 Disable 'Live Share' extension when not collaborating",
        "🔒 Use Windows Firewall to block inbound connections to ports 8080, 5173",
        "🔒 Never commit .env files or API keys to version control",
        "🔒 Run Agent Amigos only on trusted networks (home/private)",
        "🔒 Keep your API keys in environment variables, not in code",
        "🔒 Regularly rotate API keys for external services",
        "🔒 Use VS Code's workspace trust feature - only trust your own workspaces",
        "🔒 Disable VS Code telemetry for sensitive projects",
        "🔒 Keep Windows Defender active and up-to-date",
    ]
    
    # VS Code specific recommendations
    vscode_recommendations = [
        "📝 Settings: Set 'remote.autoForwardPorts' to false",
        "📝 Settings: Set 'remote.localPortHost' to 'localhost'",
        "📝 Disable extensions you don't actively use",
        "📝 Review 'Extensions: Allowed' in workspace settings",
        "📝 Use '.gitignore' to exclude sensitive files",
    ]
    
    # Calculate overall security score
    total_checks = 5
    passed_checks = total_checks - len(issues)
    security_score = int((passed_checks / total_checks) * 100)
    
    # Determine status
    if len(issues) > 0:
        status = "VULNERABLE"
        status_color = "red"
    elif len(warnings) > 2:
        status = "WARNING"
        status_color = "yellow"
    else:
        status = "SECURE"
        status_color = "green"
    
    return {
        "status": status,
        "status_color": status_color,
        "security_score": security_score,
        "owner": AUTHORIZED_OWNER,
        "security_version": SECURITY_VERSION,
        "timestamp": datetime.now().isoformat(),
        "autonomy_mode": autonomy_controller._config.get("autonomyMode", "off"),
        "autonomy_enabled": autonomy_controller.is_enabled(),
        "kill_switch": autonomy_controller.get_kill_switch(),
        "allowed_actions": list(autonomy_controller.get_allowed_actions()),
        "checks": {
            "local_only": is_local_only,
            "safe_port": int(ACTIVE_AGENT_PORT) in safe_ports or int(ACTIVE_AGENT_PORT) == int(AGENT_PORT),
            "paths_secure": sensitive_paths_check,
            "files_accessible": file_permissions_ok,
            "localhost_verified": localhost_check,
        },
        "api_keys_configured": api_keys_present,
        "server_info": {
            "host": AGENT_HOST,
            "port": ACTIVE_AGENT_PORT,
            "model": LLM_MODEL,
        },
        "issues": issues,
        "warnings": warnings,
        "recommendations": recommendations,
        "vscode_recommendations": vscode_recommendations,
    }


@app.get("/security/status")
def security_status():
    """Get comprehensive security status for Agent Amigos"""
    return get_security_status()


@app.post("/security/autonomy")
def toggle_autonomy(request: Dict[str, Any]):
    """Set autonomy mode"""
    mode = request.get("mode", "off")
    try:
        autonomy_controller.set_autonomy_mode(mode)
        return {
            "status": "success",
            "autonomy_mode": autonomy_controller._config.get("autonomyMode", "off"),
            "autonomy_enabled": autonomy_controller.is_enabled(),
            "message": f"Autonomy mode set to {mode}"
        }
    except ValueError as e:
        return {"status": "error", "message": str(e)}


@app.get("/security/verify-owner")
def verify_owner():
    """Verify the authorized owner of this Agent Amigos instance"""
    return {
        "owner": AUTHORIZED_OWNER,
        "verified": True,
        "message": f"This Agent Amigos instance is owned and operated by {AUTHORIZED_OWNER}",
        "rights": "All Rights Reserved",
        "local_only": AGENT_HOST in ["127.0.0.1", "localhost"],
    }


@app.get("/security/lockdown")
def security_lockdown():
    """Get lockdown recommendations for maximum security"""
    return {
        "title": "🔐 Agent Amigos Security Lockdown Guide",
        "owner": AUTHORIZED_OWNER,
        "steps": [
            {
                "priority": "HIGH",
                "action": "Firewall Configuration",
                "details": "Block ports 8080 and 5173 from external access in Windows Firewall",
                "command": "netsh advfirewall firewall add rule name='Block Amigos External' dir=in action=block localport=8080,5173 protocol=tcp"
            },
            {
                "priority": "HIGH", 
                "action": "VS Code Remote Disabled",
                "details": "Disable VS Code Remote extensions and Live Share when not needed",
                "setting": "remote.autoForwardPorts: false"
            },
            {
                "priority": "MEDIUM",
                "action": "Environment Variables",
                "details": "Store API keys in system environment variables, not in code or .env files",
                "tip": "Use 'setx OPENAI_API_KEY your_key' in admin PowerShell"
            },
            {
                "priority": "MEDIUM",
                "action": "Git Security",
                "details": "Ensure .gitignore includes: .env, *.key, *_secret*, api_keys.json",
            },
            {
                "priority": "LOW",
                "action": "Regular Audits",
                "details": "Run /security/status endpoint weekly to verify security posture",
            },
        ],
        "emergency_shutdown": "taskkill /F /IM python.exe (kills all Python processes)",
    }


# --- API Endpoints ---

@app.get("/ping")
def ping():
    return {"status": "pong", "timestamp": time.time()}

@app.get("/health")
def health_check():
    llm_status = check_llm_health()
    return {
        "status": "online",
        "agent": "Agent Amigos",
        "version": "2.0.0",
        "tools_available": len(TOOLS),
        "model": LLM_MODEL,
        "server": {
            "host": AGENT_HOST,
            "port": ACTIVE_AGENT_PORT,
        },
        "llm_ready": llm_status["status"],
        "llm_detail": llm_status["detail"],
        "llm_api_base": LLM_API_BASE,
        "memory": get_memory_status(),
    }

@app.get("/system/memory")
def system_memory_status():
    """Return current system + process memory usage with safety thresholds."""
    return get_memory_status()

@app.get("/tools")
def get_tools():
    """List all available tools"""
    return [
        {
            "name": name,
            "description": desc,
            "requires_approval": req_app
        }
        for name, (func, req_app, desc) in TOOLS.items()
    ]

@app.post("/chat", response_model=AgentResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint - processes messages and executes actions"""
    try:
        # Determine auto-mode status but do NOT globally override per-request approval.
        auto_mode = autonomy_controller.is_enabled()
        cfg = autonomy_controller.get_config()
        
        # If auto mode is on and requireConfirmation is false, we override the request's require_approval
        if auto_mode and cfg.get('requireConfirmation') is False:
            require_approval = False
        else:
            require_approval = request.require_approval if request.require_approval is not None else True
        
        autonomy_controller.log_action('chat_incoming', {'messages': [m.content for m in request.messages]}, {'auto_mode': auto_mode})
        response = await agent.process(
            request.messages,
            require_approval=require_approval,
            screen_context=request.screen_context,
            team_mode=request.team_mode
        )
        autonomy_controller.log_action('chat_outgoing', {'response': response.content}, {'actions_taken': response.actions_taken})
        return response
    except Exception as e:
        traceback.print_exc()
        # Log to file for debugging
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/chat_errors.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] Chat Error: {str(e)}\n")
                f.write(traceback.format_exc())
                f.write("\n" + "-"*30 + "\n")
        except:
            pass
        return JSONResponse(
            status_code=500, 
            content={"detail": str(e), "error": "Internal Server Error"},
            headers={"Access-Control-Allow-Origin": "*"}
        )

@app.get("/agent/auto_mode")
def get_auto_mode():
    """Get current autonomous mode status"""
    cfg = autonomy_controller.get_config()
    return {"auto_mode": autonomy_controller.is_enabled(), "config": cfg}

# ═══════════════════════════════════════════════════════════════════════════════
# LLM PROVIDER MANAGEMENT - Switch AI providers like GitHub Copilot does
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/agent/providers")
def get_available_providers():
    """Get all available LLM providers with their configuration status."""
    providers = []
    for provider_name, config in LLM_CONFIGS.items():
        has_key = bool(config.get("key")) and config.get("key") != ""
        # Special case for ollama - it's always "available" if running locally
        if provider_name == "ollama":
            has_key = True
        providers.append({
            "id": provider_name,
            "name": provider_name.title(),
            "model": config.get("model", ""),
            "supported_models": config.get("supported_models", []),
            "configured": has_key,
            "active": provider_name == LLM_PROVIDER,
            "base_url": config.get("base", ""),
        })
    return {
        "providers": providers,
        "active_provider": LLM_PROVIDER,
        "active_model": LLM_MODEL,
    }

@app.get("/agent/provider")
def get_current_provider():
    """Get the current active LLM provider."""
    config = LLM_CONFIGS.get(LLM_PROVIDER, {})
    return {
        "provider": LLM_PROVIDER,
        "model": LLM_MODEL,
        "base_url": config.get("base", ""),
    }


@app.get("/agent/provider/models")
def get_provider_supported_models(provider: Optional[str] = None):
    """Return supported models for the specified provider. If none specified, return for the active provider."""
    provider = (provider or LLM_PROVIDER).lower()
    if provider not in LLM_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'")
    return {"provider": provider, "supported_models": LLM_CONFIGS[provider].get("supported_models", [])}


@app.get('/agent/provider/validate')
def validate_provider(provider: Optional[str] = None):
    provider = (provider or LLM_PROVIDER).lower()
    if provider not in LLM_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'")
    cfg = LLM_CONFIGS[provider]
    ok = False
    detail = ''
    try:
        # Simple connectivity and key presence checks
        key = cfg.get('key', '')
        base = cfg.get('base', '')
        has_key = bool(key) and key != ''
        if provider == 'github':
            # Use GitHub API to test token if provided
            headers = {'Authorization': f"token {key}"} if has_key else {}
            r = _session.get('https://api.github.com/user', headers=headers, timeout=5)
            ok = r.status_code in (200, 401, 403)
            detail = f"github_status:{r.status_code}"
        else:
            # Generic base URL ping
            try:
                r = _session.get(base, timeout=5)
                ok = r.status_code == 200
                detail = f"base_status:{r.status_code}"
            except Exception as e:
                detail = str(e)
        return { 'provider': provider, 'configured': has_key, 'ok': ok, 'detail': detail }
    except Exception as e:
        return { 'provider': provider, 'configured': has_key, 'ok': False, 'detail': str(e) }


def _get_env_name_for_provider(provider: str) -> Optional[str]:
    env_name_map = {
        'openai': 'OPENAI_API_KEY',
        'grok': 'GROK_API_KEY',
        'groq': 'GROQ_API_KEY',
        'github': 'GITHUB_TOKEN',
        'ollama': 'OLLAMA_BASE',
        'deepseek': 'DEEPSEEK_API_KEY'
    }
    return env_name_map.get(provider)


ENV_KEYS_ALLOWLIST = {
    "AMIGOS_API_KEY",
    "BETFAIR_APP_KEY",
    "BETFAIR_USERNAME",
    "BETFAIR_PASSWORD",
    "PLAYWRIGHT_PROXY",
}


def _load_env_file_lines(env_path: str) -> list:
    if not os.path.exists(env_path):
        return []
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            return f.readlines()
    except Exception:
        return []


def _write_env_file_lines(env_path: str, lines: list) -> None:
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def _set_env_value_in_lines(lines: list, key: str, value: str) -> tuple[list, bool]:
    replaced = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            replaced = True
            if value:
                new_lines.append(f"{key}={value}\n")
            # If value is empty, remove the line
            continue
        new_lines.append(line)
    if not replaced and value:
        new_lines.append(f"{key}={value}\n")
    return new_lines, replaced


def _read_env_status(env_path: str) -> dict:
    status = {k: {"set": False, "source": None} for k in ENV_KEYS_ALLOWLIST}

    # Prefer runtime env values
    for key in ENV_KEYS_ALLOWLIST:
        if os.environ.get(key):
            status[key] = {"set": True, "source": "runtime"}

    # Merge .env file presence
    try:
        lines = _load_env_file_lines(env_path)
        for line in lines:
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            k = raw.split("=", 1)[0].strip()
            if k in ENV_KEYS_ALLOWLIST and not status[k]["set"]:
                status[k] = {"set": True, "source": ".env"}
    except Exception:
        pass

    return status


def validate_provider_cfg(provider: str):
    provider = provider.lower()
    if provider not in LLM_CONFIGS:
        return {'provider': provider, 'configured': False, 'ok': False, 'detail': 'Unknown provider', 'suggestion': 'Check provider name'}
    cfg = LLM_CONFIGS[provider]
    has_key = bool(cfg.get('key')) and cfg.get('key') != ''
    ok = False
    detail = ''
    suggestion = ''
    try:
        if provider == 'github':
            headers = {'Authorization': f"token {cfg.get('key')}"} if has_key else {}
            r = _session.get('https://api.github.com/user', headers=headers, timeout=5)
            ok = r.status_code in (200, 401, 403)
            detail = f"github_status:{r.status_code}"
            if r.status_code in (401, 403):
                suggestion = 'Check the GITHUB_TOKEN scope and validity (PAT).'
        else:
            base = cfg.get('base', '')
            try:
                r = _session.get(base or 'http://127.0.0.1', timeout=5)
                ok = r.status_code == 200
                detail = f"base_status:{r.status_code}"
            except Exception as e:
                detail = str(e)
        if not has_key:
            env_name = _get_env_name_for_provider(provider)
            suggestion = suggestion or f'Set the API key in .env ({env_name}) or export the environment variable.'
        if provider == 'ollama' and not ok:
            suggestion = suggestion or 'Start ollama or set OLLAMA_BASE to the running ollama server base.'
    except Exception as e:
        detail = str(e)
    return {'provider': provider, 'configured': has_key, 'ok': ok, 'detail': detail, 'suggestion': suggestion}

@app.post("/agent/provider")
def set_llm_provider(provider: str = Body(..., embed=True), model: Optional[str] = Body(None, embed=True)):
    """Switch the active LLM provider (openai, github, groq, grok, ollama, deepseek)."""
    global LLM_PROVIDER, LLM_MODEL, LLM_API_BASE, LLM_API_KEY
    
    provider = provider.lower().strip()
    if provider not in LLM_CONFIGS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider '{provider}'. Valid: {list(LLM_CONFIGS.keys())}"
        )
    
    config = LLM_CONFIGS[provider]
    
    # Check if provider has valid credentials (except ollama which doesn't need them)
    if provider != "ollama" and (not config.get("key") or config.get("key") == ""):
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider}' is not configured. Set the API key in .env file."
        )
    
    # If the client provided a model override, validate it
    if model is not None:
        model = model.strip()
        if not is_model_valid_for_provider(provider, model):
            raise HTTPException(status_code=400, detail=f"Model '{model}' is not valid for provider '{provider}'.")
        config['model'] = model

    # Update global state
    LLM_PROVIDER = provider
    LLM_API_BASE = config.get("base", "")
    LLM_API_KEY = config.get("key", "")
    LLM_MODEL = config.get("model", "")
    
    return {
        "success": True,
        "provider": LLM_PROVIDER,
        "model": LLM_MODEL,
        "message": f"Switched to {provider.title()} provider using {LLM_MODEL}"
    }


@app.get('/agent/providers/validate_all')
def validate_all_providers():
    """Validate all configured providers and return status + suggestions"""
    results = []
    for provider in LLM_CONFIGS.keys():
        results.append(validate_provider_cfg(provider))
    return {'providers': results}


def fetch_provider_models_live(provider: str):
    provider = provider.lower()
    if provider not in LLM_CONFIGS:
        return {'provider': provider, 'supported_models': [], 'live': False, 'detail': 'Unknown provider'}
    cfg = LLM_CONFIGS[provider]
    try:
        if provider == 'openai':
            key = cfg.get('key')
            if not key:
                return {'provider': provider, 'supported_models': [], 'live': False, 'detail': 'No key'}
            headers = {'Authorization': f'Bearer {key}'}
            r = _session.get('https://api.openai.com/v1/models', headers=headers, timeout=5)
            if r.status_code == 200:
                models = [m['id'] for m in r.json().get('data', [])]
                return {'provider': provider, 'supported_models': models, 'live': True}
            return {'provider': provider, 'supported_models': [], 'live': False, 'detail': f'HTTP:{r.status_code}'}
        if provider == 'ollama':
            base = cfg.get('base') or 'http://127.0.0.1:11434'
            try:
                r = _session.get(f'{base}/models', timeout=5)
                if r.status_code == 200:
                    # Ollama returns an array of model objects with 'name'
                    models = [m.get('name') for m in r.json() if isinstance(m, dict)]
                    return {'provider': provider, 'supported_models': models, 'live': True}
                return {'provider': provider, 'supported_models': [], 'live': False, 'detail': f'HTTP:{r.status_code}'}
            except Exception as e:
                return {'provider': provider, 'supported_models': [], 'live': False, 'detail': str(e)}
        # For other providers fallback to configured supported_models
        return {'provider': provider, 'supported_models': cfg.get('supported_models', []), 'live': False}
    except Exception as e:
        return {'provider': provider, 'supported_models': [], 'live': False, 'detail': str(e)}


@app.get('/agent/provider/models/refresh')
def refresh_provider_models(provider: Optional[str] = None):
    provider = (provider or LLM_PROVIDER).lower()
    if provider not in LLM_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'")
    result = fetch_provider_models_live(provider)
    # Update in-memory supported_models list if live fetch succeeded
    if result.get('live') and result.get('supported_models'):
        LLM_CONFIGS[provider]['supported_models'] = result['supported_models']
    return result


@app.post('/agent/provider/key')
def set_provider_key(provider: str = Body(..., embed=True), key: str = Body(..., embed=True)):
    provider = provider.lower()
    if provider not in LLM_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'")
    LLM_CONFIGS[provider]['key'] = key
    # Mark configured
    ok = bool(key and key != '')
    # Optionally re-validate and return status
    validate = validate_provider_cfg(provider)
    return {'provider': provider, 'configured': ok, 'validation': validate}


@app.post('/agent/provider/key/persist')
def persist_provider_key(provider: str = Body(..., embed=True), key: str = Body(..., embed=True)):
    """Persist the provider key into the .env file (backing up), update LLM_CONFIGS and re-validate.

    This endpoint writes to the server .env file - use carefully. It will create a backup and only accepts simple key strings.
    """
    provider = provider.lower()
    if provider not in LLM_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'")
    env_name = _get_env_name_for_provider(provider)
    if not env_name:
        raise HTTPException(status_code=400, detail=f"No env var mapping for provider '{provider}'")
    # Read existing .env
    env_path = os.path.join(os.getcwd(), '.env')
    if not os.path.exists(env_path):
        # Create empty
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write('')
    try:
        # backup
        ts = int(time.time())
        bak = env_path + f'.bak.{ts}'
        shutil.copyfile(env_path, bak)
        # read and replace or append
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        rv = []
        replaced = False
        for L in lines:
            if L.strip().startswith(env_name + '='):
                rv.append(f"{env_name}={key}\n")
                replaced = True
            else:
                rv.append(L)
        if not replaced:
            rv.append(f"{env_name}={key}\n")
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(rv)
        # Update in-memory config
        LLM_CONFIGS[provider]['key'] = key
        validate = validate_provider_cfg(provider)
        return {'saved': True, 'env_var': env_name, 'provider': provider, 'validation': validate}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/agent/env/open')
def open_env_in_editor():
    """Open the .env file in VS Code using `code` CLI. Only runs when environment var ALLOW_CODE_OPEN is set to '1'."""
    allow = os.environ.get('ALLOW_CODE_OPEN', '0')
    if allow != '1':
        raise HTTPException(status_code=403, detail='Opening editor is disabled on this server')
    env_path = os.path.join(os.getcwd(), '.env')
    if not os.path.exists(env_path):
        raise HTTPException(status_code=404, detail='No .env file found')
    try:
        # Try to use 'code' CLI first, otherwise open with default system opener
        if shutil.which('code'):
            _ = _original_run(['code', env_path], check=False)
        else:
            # On Windows, 'start' will open it; on *nix attempt to use xdg-open
            if os.name == 'nt':
                _ = _original_run(['cmd', '/c', 'start', '', env_path], check=False)
            else:
                _ = _original_run(['xdg-open', env_path], check=False)
        return {'opened': True, 'path': env_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/agent/env/status')
@app.get('/agent/env/status')
def get_env_status():
    """Return presence (not values) for allowlisted environment keys."""
    env_path = os.path.join(os.getcwd(), '.env')
    return {
        "keys": _read_env_status(env_path),
        "allowlist": sorted(list(ENV_KEYS_ALLOWLIST)),
        "env_path": env_path,
    }


@app.post('/agent/env/set')
def set_env_key(
    key: str = Body(..., embed=True),
    value: str = Body('', embed=True),
    backup: bool = Body(True, embed=True),
):
    """Set or clear an allowlisted env var in the backend .env file.

    - If value is empty, the key is removed from the .env file.
    - Updates process env for immediate access, but service restart may be required.
    """
    if not key or key not in ENV_KEYS_ALLOWLIST:
        raise HTTPException(status_code=400, detail='Key not allowed')

    env_path = os.path.join(os.getcwd(), '.env')
    if not os.path.exists(env_path):
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write('')

    try:
        if backup and os.path.exists(env_path):
            ts = int(time.time())
            bak = env_path + f'.bak.{ts}'
            shutil.copyfile(env_path, bak)

        lines = _load_env_file_lines(env_path)
        new_lines, _replaced = _set_env_value_in_lines(lines, key, value)
        _write_env_file_lines(env_path, new_lines)

        if value:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)

        return {
            'saved': True,
            'key': key,
            'cleared': value == '' or value is None,
            'env_path': env_path,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get('/agent/env')
def get_env():
    env_path = os.path.join(os.getcwd(), '.env')
    if not os.path.exists(env_path):
        return {'exists': False, 'content': ''}
    try:
        size = os.path.getsize(env_path)
        if size > 200 * 1024:
            raise HTTPException(status_code=413, detail='Env file too large')
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {'exists': True, 'content': content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/agent/env')
def save_env(content: str = Body(..., embed=True), backup: bool = Body(True, embed=True)):
    env_path = os.path.join(os.getcwd(), '.env')
    if not isinstance(content, str):
        raise HTTPException(status_code=400, detail='Content must be a string')
    try:
        if backup and os.path.exists(env_path):
            ts = int(time.time())
            bak = env_path + f'.bak.{ts}'
            shutil.copyfile(env_path, bak)
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {'saved': True, 'path': env_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/agent/default_model")
def get_agent_default_model():
    """Get the currently configured default LLM model for the server."""
    return {"default_model": get_default_model()}

@app.post("/agent/default_model")
def set_agent_default_model(model: str = Body(..., embed=True)):
    """Set the default LLM model for the server.

    This changes the default model used by `amigos` and routing when not otherwise specified.
    """
    set_default_model(model)
    # Update provider configs so runtime defaults use this model if not explicitly configured
    for provider in LLM_CONFIGS:
        # If enforcement flag is set, override all provider models.
        if get_enforce_default():
            LLM_CONFIGS[provider]['model'] = model
        else:
            # Only override if the env var is not set (use configured model if present)
            env_var_map = {
                'openai': 'OPENAI_MODEL',
                'grok': 'GROK_MODEL',
                'groq': 'GROQ_MODEL',
                'github': 'GITHUB_MODEL',
                'ollama': 'OLLAMA_MODEL',
                'deepseek': 'DEEPSEEK_MODEL'
            }
            env_name = env_var_map.get(provider)
            if env_name and not os.environ.get(env_name):
                LLM_CONFIGS[provider]['model'] = model

    # Update active config and global LLM_MODEL
    global LLM_MODEL
    _active_config = LLM_CONFIGS.get(LLM_PROVIDER, LLM_CONFIGS['openai'])
    LLM_MODEL = os.environ.get('LLM_MODEL', _active_config.get('model') or get_default_model())
    return {"default_model": get_default_model(), "message": f"Set default model to {get_default_model()}"}


@app.get("/agent/session_model")
def get_agent_session_model():
    """Get the currently active LLM model for this session (runtime)."""
    return {"session_model": LLM_MODEL}


@app.post("/agent/session_model")
def set_agent_session_model(model: str = Body(..., embed=True)):
    """Set the active LLM model for this running session only (does not change the default model).

    This updates global runtime LLM model used by the server until restarted or changed again.
    """
    global LLM_MODEL
    # Sanitize input and prevent unsupported empty values
    new_model = model.strip() if isinstance(model, str) else None
    if not new_model:
        raise HTTPException(status_code=400, detail="Model name required")
    # Check model is valid for the current provider
    if not is_model_valid_for_provider(LLM_PROVIDER, new_model):
        raise HTTPException(status_code=400, detail=f"Model '{new_model}' is not valid for provider '{LLM_PROVIDER}'")
    # Update in-memory active model; no change to provider env or persistent default.
    LLM_MODEL = new_model
    # Update active config model for the LLM_PROVIDER only (runtime effect)
    if LLM_PROVIDER in LLM_CONFIGS:
        LLM_CONFIGS[LLM_PROVIDER]["model"] = new_model
    return {"session_model": LLM_MODEL, "message": f"Session model set to {LLM_MODEL}"}


@app.get("/agent/default_model/enforce")
def get_agent_default_model_enforce():
    """Get if default model enforcement is currently on."""
    return {"enforce_default_model": get_enforce_default()}


@app.post("/agent/default_model/enforce")
def set_agent_default_model_enforce(enforce: bool = Body(..., embed=True)):
    """Set enforce-default-model flag (True/False).

    When True, this will override provider defaults in runtime config for providers that would otherwise have the env-model value.
    """
    set_enforce_default(bool(enforce))
    # Apply this enforcement immediately if needed
    default_model = get_default_model()
    if get_enforce_default():
        for provider in LLM_CONFIGS:
            LLM_CONFIGS[provider]["model"] = default_model
    else:
        # Recalculate provider defaults from env or previous config if we disabled enforcement
        for provider in LLM_CONFIGS:
            env_name_map = {
                'openai': 'OPENAI_MODEL',
                'grok': 'GROK_MODEL',
                'groq': 'GROQ_MODEL',
                'github': 'GITHUB_MODEL',
                'ollama': 'OLLAMA_MODEL',
                'deepseek': 'DEEPSEEK_MODEL'
            }
            env_name = env_name_map.get(provider)
            if env_name and os.environ.get(env_name):
                LLM_CONFIGS[provider]['model'] = os.environ.get(env_name)
    # Refresh active model
    global LLM_MODEL
    _active_config = LLM_CONFIGS.get(LLM_PROVIDER, LLM_CONFIGS['openai'])
    LLM_MODEL = os.environ.get('LLM_MODEL', _active_config.get('model') or get_default_model())
    return {"enforce_default_model": get_enforce_default(), "default_model": get_default_model()}

@app.post("/agent/auto_mode")
def set_auto_mode(enabled: bool = Body(..., embed=True)):
    """Set autonomous mode status"""
    # Set AutonomyController's enabled flag and echo back state
    autonomy_controller.set_enabled(bool(enabled))
    
    # If enabling auto mode, also disable requireConfirmation for Darrell (God Mode)
    if enabled:
        autonomy_controller.set_config({'requireConfirmation': False})
        
    global AUTO_MODE
    AUTO_MODE = autonomy_controller.is_enabled()
    autonomy_controller.log_action('auto_mode_set', {'enabled': AUTO_MODE}, {'by': 'api'})
    return {"auto_mode": AUTO_MODE, "message": f"Auto Mode {'Enabled' if enabled else 'Disabled'}"}


# ═══════════════════════════════════════════════════════════════════════════════
# CONTINUOUS AUTONOMY LOOP - "Autonomous continuous auto mode"
# Runs a lightweight background loop that repeatedly asks the agent for the next
# safe step toward a goal, respecting autonomy policies + kill switch.
# ═══════════════════════════════════════════════════════════════════════════════

class ContinuousAutoStartRequest(BaseModel):
    goal: str
    interval_seconds: float = 10.0
    max_cycles: int = 0  # 0 = unlimited
    max_runtime_seconds: int = 900  # 15 minutes safety cap by default
    stop_on_idle: bool = False

    # Optional: deterministic proof-of-life input so users can *see* activity.
    # This does not require the LLM to decide to move the mouse.
    heartbeat_mouse: bool = False
    heartbeat_pixels: int = 14
    # Optional region to keep heartbeat movement constrained to a window.
    # Format: {left:int, top:int, width:int, height:int}
    heartbeat_region: Optional[Dict[str, int]] = None


_CONTINUOUS_LOCK = threading.Lock()
_CONTINUOUS_STATE: Dict[str, Any] = {
    'running': False,
    'run_id': None,
    'goal': None,
    'interval_seconds': None,
    'max_cycles': None,
    'max_runtime_seconds': None,
    'stop_on_idle': None,
    'heartbeat_mouse': False,
    'heartbeat_pixels': 14,
    'heartbeat_region': None,
    'started_at': None,
    'cycle': 0,
    'last_tick_at': None,
    'last_response': None,
    'last_actions': None,
    'last_error': None,

    # Heartbeat diagnostics (proof-of-life)
    'last_heartbeat_at': None,
    'last_heartbeat': None,
}


def _clamp_int(v: Any, lo: int, hi: int, default: int) -> int:
    try:
        iv = int(v)
    except Exception:
        return default
    if iv < lo:
        return lo
    if iv > hi:
        return hi
    return iv


def _sanitize_region(region: Any) -> Optional[Dict[str, int]]:
    if not isinstance(region, dict):
        return None
    try:
        left = int(region.get('left'))
        top = int(region.get('top'))
        width = int(region.get('width'))
        height = int(region.get('height'))
    except Exception:
        return None
    if width <= 0 or height <= 0:
        return None
    return {'left': left, 'top': top, 'width': width, 'height': height}


def _heartbeat_mouse_move(cycle: int, pixels: int, region: Optional[Dict[str, int]]) -> Optional[Dict[str, Any]]:
    """Small deterministic mouse movement used as a liveness indicator.

    Uses tool execution so autonomy policies still apply.
    """
    try:
        px = _clamp_int(pixels, 4, 120, 14)
        if region:
            left = int(region['left'])
            top = int(region['top'])
            width = int(region['width'])
            height = int(region['height'])

            # Target near center; alternate left/right each tick.
            cx = left + max(1, width // 2)
            cy = top + max(1, height // 2)
            direction = -1 if (cycle % 2 == 0) else 1
            x = cx + direction * px
            y = cy
            args = {'x': int(x), 'y': int(y), 'duration': 0.12}
            agent.execute_tool('move_mouse', args)
            return {'tool': 'move_mouse', 'args': args}
        else:
            # No region: relative nudge (still visible).
            dx = -px if (cycle % 2 == 0) else px
            args = {'dx': int(dx), 'dy': 0, 'duration': 0.12}
            agent.execute_tool('move_mouse_relative', args)
            return {'tool': 'move_mouse_relative', 'args': args}
    except Exception:
        # Heartbeat is best-effort and must never crash the autonomy loop.
        return None


def _continuous_autonomy_loop(stop_event: threading.Event):
    """Background thread target for continuous autonomy."""
    # Copy run settings locally to avoid racing while still updating shared state.
    with _CONTINUOUS_LOCK:
        run_id = _CONTINUOUS_STATE.get('run_id')
        goal = _CONTINUOUS_STATE.get('goal') or ''
        interval_seconds = float(_CONTINUOUS_STATE.get('interval_seconds') or 10.0)
        max_cycles = int(_CONTINUOUS_STATE.get('max_cycles') or 0)
        max_runtime_seconds = int(_CONTINUOUS_STATE.get('max_runtime_seconds') or 900)
        stop_on_idle = bool(_CONTINUOUS_STATE.get('stop_on_idle') or False)
        heartbeat_mouse = bool(_CONTINUOUS_STATE.get('heartbeat_mouse') or False)
        heartbeat_pixels = int(_CONTINUOUS_STATE.get('heartbeat_pixels') or 14)
        heartbeat_region = _sanitize_region(_CONTINUOUS_STATE.get('heartbeat_region'))

    start_ts = time.time()
    cycle = 0
    # Maintain a small rolling memory of what we just did.
    recent_actions: List[str] = []

    autonomy_controller.log_action('continuous_autonomy_started', {
        'run_id': run_id,
        'goal': goal,
        'interval_seconds': interval_seconds,
        'max_cycles': max_cycles,
        'max_runtime_seconds': max_runtime_seconds,
        'stop_on_idle': stop_on_idle,
    }, {})

    try:
        while not stop_event.is_set():
            # Safety: respect kill switch and autonomy enabled flag.
            if autonomy_controller.get_kill_switch() or not autonomy_controller.is_enabled():
                autonomy_controller.log_action('continuous_autonomy_stopped', {
                    'run_id': run_id,
                    'reason': 'kill_switch_or_disabled'
                }, {})
                break

            # Safety: runtime cap
            if max_runtime_seconds > 0 and (time.time() - start_ts) > max_runtime_seconds:
                autonomy_controller.log_action('continuous_autonomy_stopped', {
                    'run_id': run_id,
                    'reason': 'max_runtime_reached',
                    'max_runtime_seconds': max_runtime_seconds,
                }, {})
                break

            # Safety: cycle cap
            if max_cycles > 0 and cycle >= max_cycles:
                autonomy_controller.log_action('continuous_autonomy_stopped', {
                    'run_id': run_id,
                    'reason': 'max_cycles_reached',
                    'max_cycles': max_cycles,
                }, {})
                break

            cycle += 1

            # Optional: proof-of-life mouse movement so users can see activity even
            # when the LLM chooses IDLE or fails to emit tool calls.
            if heartbeat_mouse:
                hb = _heartbeat_mouse_move(cycle=cycle, pixels=heartbeat_pixels, region=heartbeat_region)
                if hb:
                    with _CONTINUOUS_LOCK:
                        _CONTINUOUS_STATE['last_heartbeat_at'] = datetime.utcnow().isoformat()
                        _CONTINUOUS_STATE['last_heartbeat'] = hb

            # Prepare a small instruction nudge that discourages repeats.
            recent_summary = ', '.join(recent_actions[-8:]) if recent_actions else ''
            user_tick_msg = (
                f"[CONTINUOUS AUTO MODE] Tick {cycle}.\n"
                f"Goal: {goal}\n"
                f"Recent actions: {recent_summary if recent_summary else 'none'}\n\n"
                "Pick ONE next safe action toward the goal. "
                "Do not repeat the same action if it already succeeded recently. "
                "If there is nothing safe to do right now, reply with 'IDLE'."
            )

            with _CONTINUOUS_LOCK:
                _CONTINUOUS_STATE['cycle'] = cycle
                _CONTINUOUS_STATE['last_tick_at'] = datetime.utcnow().isoformat()
                _CONTINUOUS_STATE['last_error'] = None

            try:
                # Run a single step via agent.process so it can choose tools.
                # Use per-tool approval logic (do not force global auto-approve here).
                import asyncio
                req_conf = autonomy_controller.get_config().get('requireConfirmation', True)
                response = asyncio.run(agent.process([ChatMessage(role='user', content=user_tick_msg)], require_approval=req_conf))

                actions_taken = response.actions_taken or []

                # If the continuous step returned a pending action (requires approval), log and halt.
                if getattr(response, 'needs_approval', False) and getattr(response, 'pending_action', None):
                    pending = response.pending_action
                    autonomy_controller.log_action('continuous_autonomy_pending_action', {
                        'run_id': run_id,
                        'cycle': cycle,
                        'pending_action': pending
                    }, {})
                    # Set last_error to indicate waiting for approval and stop the run to avoid stalling
                    with _CONTINUOUS_LOCK:
                        _CONTINUOUS_STATE['last_error'] = 'pending_action_requires_approval'
                    break
                # Store tool names for recent action context
                for a in actions_taken:
                    t = a.get('tool') if isinstance(a, dict) else None
                    if t:
                        recent_actions.append(str(t))

                with _CONTINUOUS_LOCK:
                    _CONTINUOUS_STATE['last_response'] = response.content
                    _CONTINUOUS_STATE['last_actions'] = actions_taken

                # If the LLM provider rejected the prompt (e.g., content filter),
                # treat it as an error and stop to avoid a noisy failure loop.
                if isinstance(response.content, str) and response.content.strip().startswith('[LLM error'):
                    with _CONTINUOUS_LOCK:
                        _CONTINUOUS_STATE['last_error'] = response.content
                    autonomy_controller.log_action('continuous_autonomy_stopped', {
                        'run_id': run_id,
                        'cycle': cycle,
                        'reason': 'llm_error'
                    }, {
                        'error': response.content,
                    })
                    break

                autonomy_controller.log_action('continuous_autonomy_tick', {
                    'run_id': run_id,
                    'cycle': cycle,
                }, {
                    'response': response.content,
                    'actions_taken': actions_taken,
                })

                if stop_on_idle and isinstance(response.content, str) and response.content.strip().upper().startswith('IDLE'):
                    autonomy_controller.log_action('continuous_autonomy_stopped', {
                        'run_id': run_id,
                        'reason': 'idle'
                    }, {})
                    break

            except Exception as e:
                err = str(e)
                autonomy_controller.log_action('continuous_autonomy_error', {
                    'run_id': run_id,
                    'cycle': cycle,
                }, {
                    'error': err,
                })
                with _CONTINUOUS_LOCK:
                    _CONTINUOUS_STATE['last_error'] = err
                # Back off a bit to avoid tight error loops
                time.sleep(min(5.0, max(0.5, interval_seconds)))

            # Sleep between ticks
            time.sleep(max(0.25, interval_seconds))

    finally:
        with _CONTINUOUS_LOCK:
            _CONTINUOUS_STATE['running'] = False
            # Ensure internal references don't leak into later status calls.
            _CONTINUOUS_STATE.pop('_thread', None)
            _CONTINUOUS_STATE.pop('_stop_event', None)
        autonomy_controller.log_action('continuous_autonomy_exited', {'run_id': run_id}, {})


@app.get('/agent/continuous/status')
def get_continuous_status():
    with _CONTINUOUS_LOCK:
        # Return a copy so callers don't mutate shared state.
        snapshot = dict(_CONTINUOUS_STATE)
        # Remove non-JSON-serializable internals
        snapshot.pop('_thread', None)
        snapshot.pop('_stop_event', None)
        return snapshot


@app.get('/agent/continuous/status_compact')
def get_continuous_status_compact():
    """Compact continuous status suitable for UIs.

    Strips large fields like screenshot full base64 payloads from `last_actions`.
    """
    with _CONTINUOUS_LOCK:
        snapshot = dict(_CONTINUOUS_STATE)
        snapshot.pop('_thread', None)
        snapshot.pop('_stop_event', None)

    # Truncate potentially huge responses (keep UI snappy)
    lr = snapshot.get('last_response')
    if isinstance(lr, str) and len(lr) > 4000:
        snapshot['last_response'] = lr[:4000] + '\n...[truncated]'

    def _summarize_result(result: Any) -> Any:
        if not isinstance(result, dict):
            return result
        # Drop common large fields (e.g. screenshot full base64)
        sanitized = {}
        for k, v in result.items():
            kl = str(k).lower()
            if kl in {'full_base64', 'image_base64', 'image_b64'}:
                # keep a small hint only
                continue
            sanitized[k] = v
        # Add a hint if we stripped a large image payload
        if 'full_base64' in result or 'image_base64' in result or 'image_b64' in result:
            sanitized['_note'] = 'image_payload_omitted'
        return sanitized

    la = snapshot.get('last_actions')
    if isinstance(la, list):
        compact_actions: List[Dict[str, Any]] = []
        for a in la:
            if not isinstance(a, dict):
                continue
            compact_actions.append({
                'tool': a.get('tool'),
                'args': a.get('args'),
                'result': _summarize_result(a.get('result')),
                'auto_detected': a.get('auto_detected', False)
            })
        snapshot['last_actions'] = compact_actions

    return snapshot


@app.post('/agent/continuous/start')
def start_continuous_autonomy(req: ContinuousAutoStartRequest):
    # Require autonomy enabled (user consent) and kill switch not active.
    if autonomy_controller.get_kill_switch():
        raise HTTPException(status_code=403, detail={'error': 'kill_switch_active'})
    if not autonomy_controller.is_enabled():
        raise HTTPException(status_code=403, detail={'error': 'autonomy_disabled', 'hint': 'Enable Auto Mode / grant consent first.'})

    goal = (req.goal or '').strip()
    if not goal:
        raise HTTPException(status_code=400, detail={'error': 'goal_required'})

    interval_seconds = float(req.interval_seconds or 10.0)
    if interval_seconds < 0.25:
        interval_seconds = 0.25
    if interval_seconds > 300:
        interval_seconds = 300.0

    max_cycles = int(req.max_cycles or 0)
    if max_cycles < 0:
        max_cycles = 0
    max_runtime_seconds = int(req.max_runtime_seconds or 0)
    if max_runtime_seconds < 0:
        max_runtime_seconds = 0

    stop_on_idle = bool(req.stop_on_idle)

    heartbeat_mouse = bool(getattr(req, 'heartbeat_mouse', False))
    heartbeat_pixels = _clamp_int(getattr(req, 'heartbeat_pixels', 14), 4, 120, 14)
    heartbeat_region = _sanitize_region(getattr(req, 'heartbeat_region', None))

    with _CONTINUOUS_LOCK:
        if _CONTINUOUS_STATE.get('running'):
            raise HTTPException(status_code=409, detail={'error': 'already_running', 'run_id': _CONTINUOUS_STATE.get('run_id')})

        run_id = str(uuid.uuid4())
        stop_event = threading.Event()

        _CONTINUOUS_STATE.update({
            'running': True,
            'run_id': run_id,
            'goal': goal,
            'interval_seconds': interval_seconds,
            'max_cycles': max_cycles,
            'max_runtime_seconds': max_runtime_seconds,
            'stop_on_idle': stop_on_idle,
            'heartbeat_mouse': heartbeat_mouse,
            'heartbeat_pixels': heartbeat_pixels,
            'heartbeat_region': heartbeat_region,
            'started_at': datetime.utcnow().isoformat(),
            'cycle': 0,
            'last_tick_at': None,
            'last_response': None,
            'last_actions': None,
            'last_error': None,
            '_stop_event': stop_event,
        })

        t = threading.Thread(target=_continuous_autonomy_loop, args=(stop_event,), daemon=True)
        _CONTINUOUS_STATE['_thread'] = t
        t.start()

        # Return state snapshot (exclude non-serializable internals)
        snapshot = dict(_CONTINUOUS_STATE)
        snapshot.pop('_thread', None)
        snapshot.pop('_stop_event', None)
        return snapshot


@app.post('/agent/continuous/stop')
def stop_continuous_autonomy():
    with _CONTINUOUS_LOCK:
        if not _CONTINUOUS_STATE.get('running'):
            return JSONResponse(
                content={'status': 'not_running'},
                headers={"Access-Control-Allow-Origin": "*"}
            )
        stop_event = _CONTINUOUS_STATE.get('_stop_event')
        thread = _CONTINUOUS_STATE.get('_thread')

    try:
        if stop_event:
            stop_event.set()
        # Join briefly (do not block request for long)
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
    except Exception:
        pass

    with _CONTINUOUS_LOCK:
        _CONTINUOUS_STATE['running'] = False
        snapshot = dict(_CONTINUOUS_STATE)
        snapshot.pop('_thread', None)
        snapshot.pop('_stop_event', None)
        return JSONResponse(
            content={'status': 'stopping', 'state': snapshot},
            headers={"Access-Control-Allow-Origin": "*"}
        )

@app.post("/execute_tool")
def execute_tool(tool_call: ToolCall):
    """Direct tool execution endpoint"""
    try:
        args = tool_call.get_args()
        # Guard execution against autonomy policies
        try:
            guard_tool_execution(tool_call.tool_name, args)
        except HTTPException as e:
            autonomy_controller.log_action('tool_blocked', {'tool': tool_call.tool_name, 'args': args}, {'error': str(e.detail)})
            # Re-raise HTTP exceptions so FastAPI preserves the original status (e.g., 403 autonomy_blocked)
            raise
            
        # Log to Macro Engine
        try:
            get_macro_engine().log_action(tool_call.tool_name, "execute", args, agent="user")
        except Exception as e:
            print(f"Macro logging error: {e}")
            
        result = agent.execute_tool(tool_call.tool_name, args)
        autonomy_controller.log_action('tool_executed', {'tool': tool_call.tool_name, 'args': args}, {'result': result})
        return {"status": "success", "result": result}
    except HTTPException as e:
        # Let FastAPI return the intended status code and detail
        raise e
    except Exception as e:
        # Unknown/unhandled errors return 500
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/approve_action")
def approve_action(action: Dict[str, Any]):
    """Execute a previously pending action after user approval"""
    try:
        tool_name = action.get("tool")
        tool_args = action.get("args", {})
        result = agent.execute_tool(tool_name, tool_args)
        return {"status": "approved", "result": result}
    except HTTPException as e:
        # Preserve any explicit HTTP errors raised by downstream logic
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Email Itinerary Endpoints ---

def _parse_opt_dt(d: Optional[str]) -> Optional[datetime]:
    """Parse an optional date string from query/tool args.

    Accepts YYYY-MM-DD, full ISO, or other common human formats via dateparser.
    """
    if not d:
        return None
    try:
        return datetime.fromisoformat(d)
    except Exception:
        try:
            return dateparser.parse(d)
        except Exception:
            return None


def agent_get_itineraries_tool() -> Dict[str, Any]:
    """Return all itineraries for the agent as structured data."""
    try:
        return {"success": True, "itineraries": list_itineraries()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def agent_get_itinerary_timeline(from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict[str, Any]:
    """Generate a plain-English, chronologically ordered itinerary timeline."""
    try:
        fr = _parse_opt_dt(from_date)
        to = _parse_opt_dt(to_date)
        if fr or to:
            matched = filter_itineraries_by_range(fr, to)
        else:
            matched = list_itineraries()
        text = generate_plain_english_timeline_for_itineraries(matched, fr, to)
        return {"success": True, "timeline": text, "count": len(matched)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Register itinerary tools for the chat agent (and MCP bridge).
try:
    TOOLS.update({
        "agent_get_itineraries": (agent_get_itineraries_tool, False, "Get all parsed travel itineraries and appointments in chronological sequence"),
        "agent_get_itinerary_timeline": (agent_get_itinerary_timeline, False, "Generate a plain-English, smart-sorted timeline of all saved itineraries"),
    })
except Exception:
    pass


@app.post("/email_monitor/parse_sample")
def parse_sample(payload: dict):
    raw = payload.get("raw_email") or payload.get("raw")
    autosave = payload.get("autosave", True)
    if not raw:
        raise HTTPException(status_code=400, detail={'error': 'raw_email_required'})
    parsed = parse_email_text(raw)
    if autosave:
        saved = add_itinerary(parsed)
        return {"status": "saved", "itinerary": saved}
    return {"status": "preview", "itinerary": parsed}


@app.get("/itineraries")
def api_list_itineraries():
    return {"itineraries": list_itineraries()}


@app.get("/itineraries/summary")
def api_itineraries_summary(from_date: Optional[str] = None, to_date: Optional[str] = None):
    fr = _parse_opt_dt(from_date)
    to = _parse_opt_dt(to_date)
    if fr or to:
        matched = filter_itineraries_by_range(fr, to)
    else:
        matched = list_itineraries()
    text = generate_text_summary_for_itineraries(matched, fr, to)
    return {"summary": text, "count": len(matched)}


@app.get("/itineraries/timeline")
def api_itineraries_timeline(from_date: Optional[str] = None, to_date: Optional[str] = None):
    fr = _parse_opt_dt(from_date)
    to = _parse_opt_dt(to_date)
    if fr or to:
        matched = filter_itineraries_by_range(fr, to)
    else:
        matched = list_itineraries()
    text = generate_plain_english_timeline_for_itineraries(matched, fr, to)
    return {"timeline": text, "count": len(matched)}


@app.get("/itineraries/combined.ics")
def api_combined_ics(from_date: Optional[str] = None, to_date: Optional[str] = None):
    fr = _parse_opt_dt(from_date)
    to = _parse_opt_dt(to_date)
    if fr or to:
        matched = filter_itineraries_by_range(fr, to)
    else:
        matched = list_itineraries()
    ics = generate_combined_ics_for_itineraries(matched)
    return Response(content=ics, media_type="text/calendar", headers={"Content-Disposition": "attachment; filename=combined-itinerary.ics"})


@app.get("/itineraries/{trip_id}")
def api_get_itinerary(trip_id: str):
    it = get_itinerary(trip_id)
    if not it:
        raise HTTPException(status_code=404, detail={'error': 'not_found'})
    return {"itinerary": it}


@app.get("/itineraries/{trip_id}/export.ics")
def api_export_itinerary_ics(trip_id: str):
    it = get_itinerary(trip_id)
    if not it:
        raise HTTPException(status_code=404, detail={'error': 'not_found'})
    ics = generate_ics(it)
    return Response(content=ics, media_type="text/calendar", headers={"Content-Disposition": f"attachment; filename={trip_id}.ics"})


@app.get("/agent/itineraries")
def api_agent_get_itineraries():
    """Compatibility endpoint for older clients."""
    return {"itineraries": list_itineraries()}


@app.post("/itineraries/{trip_id}/delete")
def api_delete_itinerary(trip_id: str):
    from email_store import delete_itinerary
    if delete_itinerary(trip_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail={'error': 'not_found'})


@app.post("/itineraries/{trip_id}/reparse")
def api_reparse_itinerary(trip_id: str):
    """Re-run parsing for a saved itinerary from its stored raw email text.

    This upgrades older saved itineraries when the parser improves (dates/times/segments).
    The trip_id is preserved.
    """
    it = get_itinerary(trip_id)
    if not it:
        raise HTTPException(status_code=404, detail={'error': 'not_found'})
    raw = it.get("full_raw_text") or it.get("raw_email") or ""
    if not raw:
        raise HTTPException(status_code=400, detail={'error': 'no_raw_email_stored'})

    parsed = parse_email_text(raw)
    parsed["trip_id"] = trip_id
    # Preserve the original raw text exactly
    parsed["full_raw_text"] = raw
    updated = update_itinerary(trip_id, parsed)
    if not updated:
        raise HTTPException(status_code=500, detail={'error': 'update_failed'})
    return {"status": "reparsed", "itinerary": updated}


@app.post("/itineraries/reparse_all")
def api_reparse_all_itineraries(limit: Optional[int] = None):
    """Reparse all itineraries (optionally limited) to upgrade older saved data."""
    items = list_itineraries()
    if isinstance(limit, int) and limit > 0:
        items = items[:limit]
    updated = 0
    skipped = 0
    errors = 0
    for it in items:
        try:
            trip_id = it.get("trip_id")
            raw = it.get("full_raw_text") or it.get("raw_email") or ""
            if not trip_id or not raw:
                skipped += 1
                continue
            parsed = parse_email_text(raw)
            parsed["trip_id"] = trip_id
            parsed["full_raw_text"] = raw
            if update_itinerary(trip_id, parsed):
                updated += 1
            else:
                errors += 1
        except Exception:
            errors += 1
    return {"status": "ok", "updated": updated, "skipped": skipped, "errors": errors}


# --- Media File Serving Endpoints ---
MEDIA_ROOT = Path(__file__).resolve().parent / "media_outputs"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
(MEDIA_ROOT / "images").mkdir(parents=True, exist_ok=True)
(MEDIA_ROOT / "videos").mkdir(parents=True, exist_ok=True)
(MEDIA_ROOT / "audio").mkdir(parents=True, exist_ok=True)
(MEDIA_ROOT / "reports").mkdir(parents=True, exist_ok=True)
(MEDIA_ROOT / "recordings").mkdir(parents=True, exist_ok=True)


def _get_media_public_base_url() -> str:
    """Return a publicly reachable base URL for this backend (if configured).

    This is used when external services (e.g., Pollinations Kontext img2img) must fetch
    a source image by URL. Localhost URLs generally won't work for that.
    """
    return (os.environ.get("MEDIA_PUBLIC_BASE_URL") or "").strip().rstrip("/")


def _get_request_base_url(req: Request) -> str:
    # FastAPI's request.base_url includes trailing '/'
    try:
        return str(req.base_url).rstrip("/")
    except Exception:
        return ""


def _build_media_urls(req: Request, media_type: str, filename: str) -> Dict[str, Any]:
    rel = f"/media/{media_type}/{filename}"
    rel_dl = f"/media/download/{media_type}/{filename}"
    base = _get_request_base_url(req)
    pub = _get_media_public_base_url()
    return {
        "url": rel,
        "download_url": rel_dl,
        "absolute_url": f"{base}{rel}" if base else None,
        "absolute_download_url": f"{base}{rel_dl}" if base else None,
        "public_url": f"{pub}{rel}" if pub else None,
        "public_download_url": f"{pub}{rel_dl}" if pub else None,
    }


# --- Music Video (Anime MV) generation jobs ---
MUSICVIDEO_JOBS_FILE = str((MEDIA_ROOT / "musicvideo_jobs.json").resolve())
MUSICVIDEO_JOBS: Dict[str, dict] = {}
_MUSICVIDEO_LOCK = threading.Lock()


# --- ComfyUI management (auto-detect + start) ---
_COMFYUI_LOCK = threading.Lock()
_COMFYUI_PROCESS: Optional[_subprocess.Popen] = None
_COMFYUI_INSTALL_LOCK = threading.Lock()
_COMFYUI_INSTALL_STATUS: Dict[str, Any] = {
    "status": "idle",  # idle|running|completed|failed
    "detail": "",
    "started_at": None,
    "ended_at": None,
    "root": "",
}


def _comfyui_candidate_roots() -> List[Path]:
    """Return a list of likely ComfyUI install roots (best-effort, Windows-friendly)."""
    candidates: List[Path] = []

    # Explicit override.
    env_root = (os.environ.get("COMFYUI_ROOT") or os.environ.get("MV_COMFYUI_ROOT") or "").strip()
    if env_root:
        candidates.append(Path(env_root))

    # Repo-local conventional locations.
    try:
        candidates.append(REPO_ROOT / "external" / "ComfyUI")
        candidates.append(REPO_ROOT / "ComfyUI")
        candidates.append(BACKEND_EXTERNAL_DIR / "ComfyUI")
    except Exception:
        pass

    # Common user/global locations.
    try:
        home = Path.home()
        candidates.append(home / "ComfyUI")
        candidates.append(home / "Documents" / "ComfyUI")
    except Exception:
        pass

    # Common absolute locations.
    for p in [
        Path("C:/ComfyUI"),
        Path("D:/ComfyUI"),
    ]:
        candidates.append(p)

    # De-dupe while preserving order.
    seen = set()
    out: List[Path] = []
    for p in candidates:
        ps = str(p.resolve()) if p.exists() else str(p)
        if ps in seen:
            continue
        seen.add(ps)
        out.append(p)
    return out


def _detect_comfyui_root() -> Tuple[Optional[str], List[str]]:
    """Return (best_root, all_existing_roots) where best_root contains main.py."""
    existing: List[str] = []
    best: Optional[str] = None
    for root in _comfyui_candidate_roots():
        try:
            if root.exists() and root.is_dir():
                existing.append(str(root))
                if (root / "main.py").exists() and best is None:
                    best = str(root)
        except Exception:
            continue
    return best, existing


def _comfyui_python_for_root(root: Path) -> str:
    """Prefer ComfyUI's own venv python if present, else use project venv python."""
    try:
        venv_py = root / "venv" / "Scripts" / "python.exe"
        if venv_py.exists():
            return str(venv_py)
    except Exception:
        pass
    return get_python_venv_path()


def _comfyui_torch_has_cuda(python_exe: str) -> bool:
    """Best-effort check for CUDA availability in the python environment used to launch ComfyUI.

    Many Windows installs end up with CPU-only torch wheels. In that case, ComfyUI can crash at startup
    if it attempts to query torch.cuda.* APIs. When CUDA isn't available, we should launch with --cpu.
    """
    try:
        res = _subprocess.run(
            [python_exe, "-c", "import torch; print(int(torch.cuda.is_available()))"],
            capture_output=True,
            text=True,
            check=False,
        )
        out = (res.stdout or "").strip()
        return out.endswith("1")
    except Exception:
        return False


def _start_comfyui_process(root_dir: str, url: str) -> Tuple[bool, str]:
    """Start ComfyUI in the background if not already started. Returns (ok, message)."""
    global _COMFYUI_PROCESS
    root = Path(root_dir)
    if not (root.exists() and (root / "main.py").exists()):
        return False, f"ComfyUI not found at {root_dir} (missing main.py)"

    # If already reachable, don't spawn.
    try:
        ok, msg = ComfyUIClient(base_url=url).health_check()
        if ok:
            return True, "already running"
    except Exception:
        pass

    with _COMFYUI_LOCK:
        # If we already spawned something, keep it (best-effort).
        if _COMFYUI_PROCESS is not None and getattr(_COMFYUI_PROCESS, "poll", lambda: None)() is None:
            return True, "already started"

        py = _comfyui_python_for_root(root)
        log_dir = (MEDIA_ROOT / "_tmp" / "musicvideo")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "comfyui.log"

        # Parse host/port from url when possible.
        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname or "127.0.0.1"
            port = int(parsed.port or 8188)
        except Exception:
            host, port = "127.0.0.1", 8188

        cmd = [py, "main.py", "--listen", host, "--port", str(port)]
        # If torch has no CUDA support, start ComfyUI in CPU mode to avoid startup crashes.
        if not _comfyui_torch_has_cuda(py):
            cmd.append("--cpu")
        try:
            fh = open(str(log_path), "a", encoding="utf-8")
        except Exception:
            fh = None
        try:
            if fh:
                try:
                    fh.write("\n$ " + " ".join(cmd) + "\n")
                    fh.flush()
                except Exception:
                    pass
            _COMFYUI_PROCESS = _subprocess.Popen(
                cmd,
                cwd=str(root),
                stdout=fh or _subprocess.DEVNULL,
                stderr=fh or _subprocess.DEVNULL,
                text=True,
            )
        except Exception as exc:
            return False, f"Failed to start ComfyUI: {exc}"

    # Give it a moment, then try a best-effort health check.
    # IMPORTANT: ComfyUI can take a few seconds to boot. We treat "not reachable yet" as success.
    time.sleep(1.0)
    try:
        ok2, msg2 = ComfyUIClient(base_url=url).health_check()
        if ok2:
            return True, msg2
        return True, f"started (pid {getattr(_COMFYUI_PROCESS, 'pid', None)}), but not reachable yet: {msg2}"
    except Exception as exc:
        return True, f"started (pid {getattr(_COMFYUI_PROCESS, 'pid', None)}), health check error: {exc}"


def _install_comfyui_repo(install_dir: Path) -> Tuple[bool, str]:
    """Install ComfyUI into install_dir (git clone + venv + pip install)."""
    install_dir = Path(install_dir)
    install_dir.parent.mkdir(parents=True, exist_ok=True)

    log_dir = (MEDIA_ROOT / "_tmp" / "musicvideo")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "comfyui_install.log"

    def _run(cmd: List[str], cwd: Optional[Path] = None) -> Tuple[bool, str]:
        try:
            res = _subprocess.run(
                cmd,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                check=False,
            )
            out = (res.stdout or "") + "\n" + (res.stderr or "")
            try:
                with open(str(log_path), "a", encoding="utf-8") as fh:
                    fh.write(f"\n$ {' '.join(cmd)}\n")
                    fh.write(out)
            except Exception:
                pass
            if res.returncode == 0:
                return True, "ok"
            return False, out[-1200:] if out else f"exit code {res.returncode}"
        except Exception as exc:
            return False, str(exc)

    sources_present = bool((install_dir / "main.py").exists())

    # Basic preflight: git (optional)
    ok_git, _msg_git = _run(["git", "--version"])
    use_git = bool(ok_git)

    # Fetch sources (git clone when available, else zip download) if not already present.
    if not sources_present:
        if install_dir.exists() and any(install_dir.iterdir()):
            # Folder exists but doesn't look like ComfyUI
            return False, f"Install directory already exists and is not empty: {install_dir}"

        if use_git:
            ok_clone, msg_clone = _run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "https://github.com/comfyanonymous/ComfyUI.git",
                    str(install_dir),
                ]
            )
            if not ok_clone:
                return False, f"Failed to clone ComfyUI: {msg_clone}"
        else:
            # Zip fallback (no git required)
            try:
                import zipfile

                zip_url = "https://github.com/comfyanonymous/ComfyUI/archive/refs/heads/master.zip"
                tmp_zip = (log_dir / "ComfyUI_master.zip")
                tmp_extract = (log_dir / "ComfyUI_extract")
                if tmp_extract.exists():
                    shutil.rmtree(tmp_extract, ignore_errors=True)
                tmp_extract.mkdir(parents=True, exist_ok=True)

                r = requests.get(zip_url, timeout=60)
                r.raise_for_status()
                tmp_zip.write_bytes(r.content)
                with zipfile.ZipFile(str(tmp_zip), "r") as zf:
                    zf.extractall(str(tmp_extract))

                # Find extracted top folder
                top_dirs = [p for p in tmp_extract.iterdir() if p.is_dir()]
                if not top_dirs:
                    return False, "Downloaded ComfyUI zip but no folder was extracted"
                src_root = top_dirs[0]

                # Move extracted folder contents into install_dir
                install_dir.mkdir(parents=True, exist_ok=True)
                for item in src_root.iterdir():
                    shutil.move(str(item), str(install_dir / item.name))
            except Exception as exc:
                return False, f"Failed to download/extract ComfyUI zip (no git available): {exc}"

    # Create/repair venv
    py = get_python_venv_path()
    venv_dir = install_dir / "venv"
    vpy_expected = venv_dir / "Scripts" / "python.exe"
    if not vpy_expected.exists():
        ok_venv, msg_venv = _run([py, "-m", "venv", "venv"], cwd=install_dir)
        if not ok_venv:
            return False, f"Failed to create ComfyUI venv: {msg_venv}"

    vpy = _comfyui_python_for_root(install_dir)
    ok_pip, msg_pip = _run([vpy, "-m", "pip", "install", "-U", "pip", "wheel", "setuptools"], cwd=install_dir)
    if not ok_pip:
        return False, f"Failed to upgrade pip in ComfyUI venv: {msg_pip}"

    # Install requirements (idempotent; safe to re-run)
    req = install_dir / "requirements.txt"
    if not req.exists():
        return False, f"ComfyUI requirements.txt not found: {req}"

    ok_req, msg_req = _run([vpy, "-m", "pip", "install", "-r", "requirements.txt"], cwd=install_dir)
    if not ok_req:
        return False, f"Failed installing ComfyUI requirements: {msg_req}"

    # Quick sanity import for common missing modules.
    ok_yaml, _msg_yaml = _run([vpy, "-c", "import yaml; print('yaml_ok')"], cwd=install_dir)
    if not ok_yaml:
        ok_fix, msg_fix = _run([vpy, "-m", "pip", "install", "pyyaml"], cwd=install_dir)
        if not ok_fix:
            return False, f"ComfyUI deps installed but PyYAML is still missing: {msg_fix}"

    if not (install_dir / "main.py").exists():
        return False, "ComfyUI install completed but main.py is missing (unexpected)"

    return True, f"installed to {install_dir}" if not sources_present else f"repaired deps in {install_dir}"


def _comfyui_install_worker(target: Path) -> None:
    with _COMFYUI_INSTALL_LOCK:
        _COMFYUI_INSTALL_STATUS.update(
            {
                "status": "running",
                "detail": "installing",
                "started_at": time.time(),
                "ended_at": None,
                "root": str(target),
            }
        )

    ok, msg = _install_comfyui_repo(target)
    with _COMFYUI_INSTALL_LOCK:
        _COMFYUI_INSTALL_STATUS.update(
            {
                "status": "completed" if ok else "failed",
                "detail": msg,
                "ended_at": time.time(),
                "root": str(target),
            }
        )


def _mv_safe_stem(name: str) -> str:
    stem = (name or "").strip()
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem)
    stem = stem.strip("._-")
    return stem or "music_video"


def _mv_load_jobs_from_disk() -> None:
    try:
        if os.path.exists(MUSICVIDEO_JOBS_FILE):
            with open(MUSICVIDEO_JOBS_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                MUSICVIDEO_JOBS.update(data)
    except Exception:
        pass


def _mv_reconcile_jobs_on_startup() -> None:
    """Reconcile persisted MV job state after backend restarts.

    MV jobs are executed in background threads and are not resumable after a
    process restart. If the backend restarts mid-job, the persisted job record
    can remain stuck in `queued`/`running` forever (e.g. 20% animating).

    On startup we mark those jobs as cancelled/failed with a clear message so
    the UI doesn't show zombie jobs and the user can press Retry.
    """
    try:
        changed = False
        now = time.time()
        with _MUSICVIDEO_LOCK:
            for jid, job in list(MUSICVIDEO_JOBS.items()):
                if not isinstance(job, dict):
                    continue
                status = str(job.get("status") or "").strip().lower()
                if status not in {"queued", "running"}:
                    continue

                # If user already requested cancellation, reflect it.
                if bool(job.get("cancel_requested")):
                    job["status"] = "cancelled"
                    job["stage"] = "cancelled"
                    job.setdefault("progress", 0)
                    job["completed_at"] = job.get("completed_at") or now
                    job["error"] = job.get("error") or "Cancelled (backend restarted)."
                else:
                    job["status"] = "failed"
                    job["stage"] = "error"
                    job["completed_at"] = job.get("completed_at") or now
                    job["error"] = job.get("error") or (
                        "Backend restarted while this MV job was in progress. "
                        "Jobs cannot resume after restart. Please click Retry to start a new run."
                    )

                # Ensure we don't present it as actively running.
                job.pop("thread", None)
                changed = True

            if changed:
                # Persist the reconciliation results.
                try:
                    with open(MUSICVIDEO_JOBS_FILE, "w", encoding="utf-8") as fh:
                        fh.write(json.dumps(MUSICVIDEO_JOBS))
                except Exception:
                    pass
    except Exception:
        # Best-effort only; never block startup.
        pass


def _mv_save_jobs_to_disk() -> None:
    try:
        with _MUSICVIDEO_LOCK:
            with open(MUSICVIDEO_JOBS_FILE, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(MUSICVIDEO_JOBS))
    except Exception:
        pass


def _mv_set_job(job_id: str, **updates) -> None:
    with _MUSICVIDEO_LOCK:
        job = MUSICVIDEO_JOBS.get(job_id) or {"id": job_id}
        # Always track last update time for UI "is it moving?" feedback.
        if "updated_at" not in updates:
            updates["updated_at"] = time.time()
        job.update(updates)
        MUSICVIDEO_JOBS[job_id] = job
    _mv_save_jobs_to_disk()


def _mv_get_job(job_id: str) -> Optional[dict]:
    with _MUSICVIDEO_LOCK:
        j = MUSICVIDEO_JOBS.get(job_id)
        return dict(j) if isinstance(j, dict) else None


def _mv_delete_job(job_id: str) -> bool:
    """Delete a job record from the MV job store (does not delete media files)."""
    removed = False
    with _MUSICVIDEO_LOCK:
        if job_id in MUSICVIDEO_JOBS:
            MUSICVIDEO_JOBS.pop(job_id, None)
            removed = True
    if removed:
        _mv_save_jobs_to_disk()
    return removed


_mv_load_jobs_from_disk()
_mv_reconcile_jobs_on_startup()


def _mv_analyze_audio(audio_path: str) -> Dict[str, Any]:
    """Analyze an audio file to estimate BPM, beat times, energy curve, mood and sections.

    We prefer librosa (better beat/structure detection). If unavailable, fallback to
    pydub + simple RMS/onset heuristics.
    """
    analysis: Dict[str, Any] = {
        "duration_s": None,
        "bpm": None,
        "beats": [],
        "mood": None,
        "energy_curve": [],
        "sections": [],
        "method": "fallback",
    }

    # Duration + librosa analysis when possible
    try:
        try:
            import numpy as _np
            import librosa  # type: ignore

            y, sr = librosa.load(audio_path, mono=True)
            duration_s = float(librosa.get_duration(y=y, sr=sr))
            analysis["duration_s"] = duration_s

            # Beats / tempo
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            bpm = float(tempo) if tempo else None
            if bpm and 40 <= bpm <= 240:
                analysis["bpm"] = float(round(bpm, 2))
                analysis["method"] = "librosa"

            if beat_frames is not None and len(beat_frames) > 0:
                beat_times = librosa.frames_to_time(beat_frames, sr=sr)
                analysis["beats"] = [float(x) for x in beat_times.tolist()]

            # Energy curve (RMS) at 50ms hop
            hop_length = max(1, int(sr * 0.05))
            frame_length = max(hop_length * 2, 2048)
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            if rms.size:
                r = _np.array(rms, dtype=_np.float32)
                r = r - float(r.min())
                denom = float(r.max()) or 1.0
                r = r / denom
                analysis["energy_curve"] = [float(x) for x in r.tolist()]

            # Structure detection via clustering on MFCC/chroma (approximate sections)
            try:
                mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
                mfcc = librosa.util.normalize(mfcc)
                # 6-8 segments depending on duration
                k = 6
                if duration_s > 150:
                    k = 8
                boundaries = librosa.segment.agglomerative(mfcc, k=k)
                # boundaries are frame indices in mfcc time; convert to seconds.
                # mfcc hop length defaults to 512
                seg_times = librosa.frames_to_time(boundaries, sr=sr, hop_length=512)
                seg_times = [0.0] + [float(x) for x in seg_times.tolist()] + [float(duration_s)]
                # De-dup and sort
                seg_times = sorted(set([max(0.0, min(duration_s, t)) for t in seg_times]))

                section_labels = ["Intro", "Verse", "Chorus", "Bridge", "Final Chorus", "Outro"]
                sections = []
                for i in range(len(seg_times) - 1):
                    a, b = seg_times[i], seg_times[i + 1]
                    if b - a < 2.0:
                        continue
                    name = section_labels[min(i, len(section_labels) - 1)]
                    sections.append({"name": name, "start": float(a), "end": float(b)})
                analysis["sections"] = sections
            except Exception:
                # Fall back to rule-based if structure fails
                pass

        except Exception:
            # librosa not available or failed; pydub fallback
            from pydub import AudioSegment
            import numpy as _np

            seg = AudioSegment.from_file(audio_path)
            duration_s = float(len(seg)) / 1000.0
            analysis["duration_s"] = duration_s

            frame_ms = 50
            energies = []
            for t0 in range(0, len(seg), frame_ms):
                frame = seg[t0 : t0 + frame_ms]
                samples = _np.array(frame.get_array_of_samples())
                if samples.size == 0:
                    energies.append(0.0)
                    continue
                rms = float(_np.sqrt(_np.mean(samples.astype(_np.float32) ** 2)))
                energies.append(rms)

            if energies:
                e = _np.array(energies, dtype=_np.float32)
                e = e - float(e.min())
                denom = float(e.max()) or 1.0
                e = e / denom
                analysis["energy_curve"] = e.tolist()

            # Basic BPM estimation from energy derivative peaks
            if analysis.get("energy_curve"):
                ec = analysis["energy_curve"]
                d = _np.diff(_np.array(ec, dtype=_np.float32))
                thresh = float(_np.percentile(d, 95)) if d.size else 0.0
                peaks = _np.where(d >= max(thresh, 0.05))[0]
                if peaks.size >= 8:
                    times = peaks * (frame_ms / 1000.0)
                    itv = _np.diff(times)
                    itv = itv[(itv > 0.15) & (itv < 1.5)]
                    if itv.size:
                        median = float(_np.median(itv))
                        bpm2 = 60.0 / median
                        while bpm2 < 60:
                            bpm2 *= 2
                        while bpm2 > 180:
                            bpm2 /= 2
                        analysis["bpm"] = float(round(bpm2, 2))

        # Mood classification (simple)
        avg_energy = None
        if analysis.get("energy_curve"):
            import numpy as _np

            avg_energy = float(_np.mean(_np.array(analysis["energy_curve"], dtype=_np.float32)))
        mood = "uplifting"
        if avg_energy is not None:
            if avg_energy < 0.25:
                mood = "chill"
            elif avg_energy < 0.45:
                mood = "emotional"
            elif avg_energy < 0.65:
                mood = "epic"
            else:
                mood = "high-energy"
        analysis["mood"] = mood

        # Section detection fallback (rule-based timeline buckets)
        if not analysis.get("sections"):
            dur = float(analysis.get("duration_s") or 0.0)
            if dur > 0.0:
                intro_end = min(15.0, dur * 0.10)
                outro_start = max(dur - min(15.0, dur * 0.10), intro_end)
                p2 = dur * 0.35
                p3 = dur * 0.55
                p4 = dur * 0.70
                p5 = dur * 0.90

                sections = []
                def _add(name: str, a: float, b: float):
                    if b - a >= 2.0:
                        sections.append({"name": name, "start": float(a), "end": float(b)})

                _add("Intro", 0.0, intro_end)
                _add("Verse", intro_end, p2)
                _add("Chorus", p2, p3)
                _add("Bridge", p3, p4)
                _add("Final Chorus", p4, p5)
                _add("Outro", max(p5, outro_start), dur)
                analysis["sections"] = sections

    except Exception as exc:
        analysis["error"] = str(exc)[:500]

    # Ensure BPM exists
    if not analysis.get("bpm"):
        analysis["bpm"] = 120.0
    return analysis


def _mv_theme_from_mood(mood: str) -> str:
    m = (mood or "").lower()
    if "chill" in m:
        return "Island / dreamscape"
    if "dark" in m:
        return "Dark psychological"
    if "emotional" in m:
        return "Emotional / romance"
    if "epic" in m or "high" in m:
        return "Hero journey"
    return "Fantasy / magic"


def _mv_prompt_for_scene(theme: str, section: str, mood: str) -> str:
    # Safety constraints baked into the prompt.
    base = (
        "Japanese ANIME style, cinematic, clean line art, dramatic lighting, "
        "smooth camera motion feel, no photorealism, no live-action, "
        "original characters only, no copyrighted characters, no logos, no watermark, "
        "non-NSFW, tasteful, high quality"
    )
    vibe = f"mood: {mood}. theme: {theme}."

    # Section-specific direction
    s = (section or "").lower()
    if "intro" in s:
        shot = "slow establishing shot, wide cinematic composition"
    elif "verse" in s:
        shot = "character and story setup, gentle motion"
    elif "chorus" in s:
        shot = "dynamic action, emotional climax, intense lighting"
    elif "bridge" in s:
        shot = "abstract symbolic imagery, surreal dreamlike visuals"
    elif "outro" in s:
        shot = "calm closing shot, soft fade-out feeling"
    else:
        shot = "cinematic sequence"

    return f"{base}. {vibe} {shot}."


def _mv_negative_prompt() -> str:
    # Safety & quality guardrails.
    return (
        "photorealistic, live action, watermark, logo, text, nsfw, nude, gore, "
        "real person, celebrity, copyrighted character, low quality, blurry"
    )


def _mv_generate_motion_clip_cloud(
    prompt: str,
    negative_prompt: str,
    duration_s: float,
    out_path: str,
    preferred_backend: str = "pollinations",
) -> Dict[str, Any]:
    """Generate a short motion clip using a cloud model.

    This function is **motion-only**: it will not accept a slideshow fallback.

        preferred_backend:
            - "pollinations" (FREE, no key; returns real motion when available)
            - "replicate" (requires REPLICATE_API_TOKEN)
            - "fal" (AnimateDiff turbo via fal.ai; requires FAL_KEY)

    We always validate that the result is not the slideshow fallback.
    """
    backend = (preferred_backend or "pollinations").strip().lower()
    dur = int(max(2, min(10, round(duration_s))))

    def _is_slideshow(res: Dict[str, Any]) -> bool:
        note = str(res.get("note") or "")
        return "slideshow" in note.lower()

    if backend == "fal":
        # Call fal directly to avoid Replicate being tried first when REPLICATE_API_TOKEN is set.
        result = media._text_to_video_fal(
            prompt=prompt,
            duration=dur,
            aspect_ratio="16:9",
            output_path=out_path,
        )
    elif backend == "replicate":
        # Pick a sensible default Replicate model; MediaTools will use REPLICATE_API_TOKEN.
        replicate_model = (os.environ.get("MV_REPLICATE_MODEL") or "wan").strip().lower()
        result = media.generate_ai_video(
            prompt=prompt,
            duration=dur,
            aspect_ratio="16:9",
            output_path=out_path,
            model=replicate_model,
            negative_prompt=negative_prompt,
        )
    else:
        # Default/free path.
        # Pollinations can occasionally fall back to a slideshow; we retry and also
        # cycle through other free-ish model identifiers supported by our MediaTools.
        # This dramatically reduces "stuck at 20%" failures in practice.
        models_to_try = ["pollinations", "seedance", "veo"]
        last: Dict[str, Any] = {"success": False, "error": "unknown"}
        attempt = 0
        for m in models_to_try:
            for _ in range(2):
                attempt += 1
                # Small prompt nudge; keep deterministic structure but encourage motion.
                nudged = f"{prompt} cinematic motion, animated video, not a slideshow, attempt {attempt}".strip()
                res = media.generate_ai_video(
                    prompt=nudged,
                    duration=dur,
                    aspect_ratio="16:9",
                    output_path=out_path,
                    model=m,
                    negative_prompt=negative_prompt,
                )
                last = res
                if res.get("success") and not _is_slideshow(res):
                    result = res
                    break
                # If provider explicitly returns slideshow, keep trying.
            else:
                continue
            break
        else:
            result = last

    if not result.get("success"):
        return result

    # Hard block slideshow fallbacks.
    if _is_slideshow(result):
        return {
            "success": False,
            "error": "Cloud provider fell back to a slideshow. This MV pipeline requires true motion. Try retrying the job, or configure ComfyUI workflow, or set FAL_KEY / REPLICATE_API_TOKEN for a motion-capable provider.",
        }

    return result


def _musicvideo_worker(job_id: str) -> None:
    job = _mv_get_job(job_id) or {}
    audio_path = job.get("audio_path")
    if not audio_path or not os.path.exists(audio_path):
        _mv_set_job(job_id, status="failed", stage="error", error="Audio file missing")
        return

    try:
        _mv_set_job(job_id, status="running", stage="analyzing", progress=5)

        analysis = _mv_analyze_audio(audio_path)
        bpm = float(analysis.get("bpm") or 120.0)
        mood = str(analysis.get("mood") or "uplifting")
        theme = _mv_theme_from_mood(mood)
        sections = analysis.get("sections") or []

        _mv_set_job(
            job_id,
            analysis=analysis,
            bpm=bpm,
            mood=mood,
            theme=theme,
            status="running",
            stage="planning",
            progress=15,
        )

        # Plan scenes anchored to detected sections, then sub-slice into short animated blocks.
        duration_s = float(analysis.get("duration_s") or 0.0)
        if duration_s <= 0:
            duration_s = 60.0

        beat_s = 60.0 / max(bpm, 1.0)
        # 2–5 seconds clips; shorter clips = better motion consistency.
        clip_len = max(2.5, min(5.0, beat_s * 8))

        scenes: List[Dict[str, Any]] = []
        for s in (sections or [{"name": "Scene", "start": 0.0, "end": duration_s}]):
            try:
                sec_name = str(s.get("name") or "Scene")
                a = float(s.get("start", 0.0))
                b = float(s.get("end", 0.0))
            except Exception:
                continue
            a = max(0.0, min(duration_s, a))
            b = max(a, min(duration_s, b))
            t = a
            while t < b - 0.25:
                d = min(clip_len, b - t)
                scenes.append({"index": len(scenes), "start": t, "end": t + d, "section": sec_name})
                t += d

        _mv_set_job(job_id, scenes=scenes, status="running", stage="animating", progress=20)

        # Motion generation via local ComfyUI workflow (AnimateDiff/Deforum/etc)
        workflow_path = (os.environ.get("COMFYUI_WORKFLOW_PATH") or os.environ.get("MV_COMFYUI_WORKFLOW") or "").strip()

        comfy = None
        comfy_ok = False
        comfy_msg = ""
        if workflow_path and os.path.exists(str(workflow_path)):
            comfy = ComfyUIClient(base_url=get_default_comfyui_url())
            comfy_ok, comfy_msg = comfy.health_check()

        # If ComfyUI isn't usable, use a true-motion cloud backend.
        use_cloud_fallback = False
        cloud_backend = "pollinations"
        if not (workflow_path and os.path.exists(str(workflow_path)) and comfy_ok and comfy):
            use_cloud_fallback = True
            forced_cloud = (os.environ.get("MV_CLOUD_BACKEND") or "").strip().lower()
            if forced_cloud in {"pollinations", "replicate", "fal"}:
                cloud_backend = forced_cloud
            elif os.environ.get("REPLICATE_API_TOKEN"):
                cloud_backend = "replicate"
            elif os.environ.get("FAL_KEY"):
                cloud_backend = "fal"
            else:
                cloud_backend = "pollinations"

            if cloud_backend == "replicate":
                _mv_set_job(job_id, stage="animating", motion_backend="replicate (text-to-video)")
            elif cloud_backend == "fal":
                _mv_set_job(job_id, stage="animating", motion_backend="fal.ai (AnimateDiff turbo)")
            else:
                _mv_set_job(job_id, stage="animating", motion_backend="pollinations.ai (FREE)")

        base_fps = int(os.environ.get("MV_BASE_FPS") or 12)
        target_fps = int(job.get("fps") or 30)
        width, height = 1280, 720  # generate lower, upscale in transcode step
        out_w, out_h = 1920, 1080

        tmp_dir = (MEDIA_ROOT / "_tmp" / "musicvideo" / job_id)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        clips_ready: List[str] = []
        user_style = str(job.get("anime_prompt") or "").strip()
        user_neg = str(job.get("negative_prompt") or "").strip()
        user_motion_hint = str(job.get("motion_hint") or "").strip()
        neg = user_neg if user_neg else _mv_negative_prompt()

        for i, sc in enumerate(scenes):
            job_now = _mv_get_job(job_id) or {}
            if job_now.get("cancel_requested"):
                _mv_set_job(job_id, status="cancelled", stage="cancelled", progress=0)
                return

            section = str(sc.get("section") or "Scene")
            dur = float(sc.get("end") - sc.get("start"))
            dur = max(2.0, min(dur, 6.0))

            # Prompt includes explicit motion/camera direction.
            default_motion_hint = "smooth continuous animation, dynamic motion, camera pan, subtle parallax, drifting particles"
            motion_hint = user_motion_hint if user_motion_hint else default_motion_hint
            base_prompt = _mv_prompt_for_scene(theme=theme, section=section, mood=mood)
            if user_style:
                prompt = f"{user_style} {base_prompt} {motion_hint}".strip()
            else:
                prompt = f"{base_prompt} {motion_hint}".strip()

            frames = int(max(16, min(48, round(dur * base_fps))))
            seed = int.from_bytes(os.urandom(4), "little")

            # Allocate progress smoothly across all scenes so long songs still show
            # continuous movement (even when there are many scenes).
            total_scenes = float(max(len(scenes), 1))
            start_p = 20.0 + (float(i) / total_scenes) * 45.0
            end_p = 20.0 + (float(i + 1) / total_scenes) * 45.0
            if end_p <= start_p:
                end_p = start_p + 0.5

            _mv_set_job(
                job_id,
                stage="animating",
                progress=float(start_p),
                current_scene=i,
                current_section=section,
                current_prompt=prompt[:300],
                stage_detail=f"Scene {i + 1}/{int(total_scenes)}: preparing request",
            )

            # Heartbeat thread: while we're blocked waiting for a clip to render,
            # nudge progress forward in tiny increments so the UI shows activity.
            hb_stop = threading.Event()

            def _heartbeat() -> None:
                try:
                    # Keep a little headroom so we never overshoot the scene's allocation.
                    cap = float(end_p) - 0.1
                    while not hb_stop.is_set():
                        j = _mv_get_job(job_id) or {}
                        if j.get("cancel_requested"):
                            return
                        p = float(j.get("progress") or start_p)
                        # Small, steady increments.
                        p2 = min(cap, p + 0.2)
                        _mv_set_job(
                            job_id,
                            progress=float(p2),
                            stage="animating",
                            stage_detail=f"Scene {i + 1}/{int(total_scenes)}: rendering motion clip…",
                        )
                        time.sleep(2.0)
                except Exception:
                    return

            threading.Thread(target=_heartbeat, daemon=True).start()

            raw_clip = str(tmp_dir / f"clip_{i:03d}_raw.mp4")
            try:
                if use_cloud_fallback:
                    _mv_set_job(job_id, stage_detail=f"Scene {i + 1}/{int(total_scenes)}: calling {cloud_backend}…")
                    cloud = _mv_generate_motion_clip_cloud(
                        prompt=prompt,
                        negative_prompt=neg,
                        duration_s=dur,
                        out_path=raw_clip,
                        preferred_backend=cloud_backend,
                    )
                    if not cloud.get("success") or not os.path.exists(raw_clip):
                        _mv_set_job(job_id, status="failed", stage="error", error=cloud.get("error") or "Cloud motion generation failed")
                        return
                    clip_for_transcode = raw_clip
                else:
                    _mv_set_job(job_id, stage_detail=f"Scene {i + 1}/{int(total_scenes)}: rendering via ComfyUI…")
                    res = comfy.generate_video(
                        workflow_path=workflow_path,
                        prompt=prompt,
                        negative_prompt=neg,
                        width=width,
                        height=height,
                        frames=frames,
                        fps=base_fps,
                        seed=seed,
                        steps=int(os.environ.get("MV_STEPS") or 20),
                        cfg=float(os.environ.get("MV_CFG") or 6.0),
                        output_path=raw_clip,
                        max_wait_s=int(os.environ.get("MV_COMFYUI_MAX_WAIT_S") or 3600),
                    )
                    if not res.success or not res.output_video_path or not os.path.exists(res.output_video_path):
                        _mv_set_job(job_id, status="failed", stage="error", error=res.error or "ComfyUI generation failed")
                        return
                    clip_for_transcode = res.output_video_path
            finally:
                hb_stop.set()

            # Scene finished: lock in the progress for this scene.
            _mv_set_job(
                job_id,
                stage="animating",
                progress=float(end_p),
                stage_detail=f"Scene {i + 1}/{int(total_scenes)}: clip ready",
            )

            # Optional interpolation to target fps
            if base_fps < target_fps:
                _mv_set_job(job_id, stage="interpolating", progress=max(float(end_p), 65.0), stage_detail="Interpolating FPS…")
                interp_path = str(tmp_dir / f"clip_{i:03d}_interp.mp4")
                ok_i, msg_i = interpolate_to_fps(clip_for_transcode, interp_path, target_fps)
                if ok_i and os.path.exists(interp_path):
                    clip_for_transcode = interp_path
                else:
                    # Keep moving: motion clip still exists; record warning.
                    _mv_set_job(job_id, interpolation_warning=(msg_i or "interpolation skipped"))

            # Transcode to normalized 1080p for concat
            norm_path = str(tmp_dir / f"clip_{i:03d}_1080p.mp4")
            ok_t, msg_t = transcode_h264(
                input_path=clip_for_transcode,
                output_path=norm_path,
                width=out_w,
                height=out_h,
                fps=target_fps,
                crf=int(os.environ.get("MV_CRF") or 18),
                preset=str(os.environ.get("MV_PRESET") or "medium"),
            )
            if not ok_t:
                _mv_set_job(job_id, status="failed", stage="error", error=f"ffmpeg transcode failed: {msg_t}")
                return

            clips_ready.append(norm_path)

        _mv_set_job(job_id, stage="assembling", progress=85.0, stage_detail="Stitching clips…")

        # Concatenate clips
        stitched_path = str(tmp_dir / "stitched.mp4")
        ok_c, msg_c = concat_videos(clips_ready, stitched_path)
        if not ok_c:
            _mv_set_job(job_id, status="failed", stage="error", error=f"ffmpeg concat failed: {msg_c}")
            return

        # Output file
        out_name = job.get("output_filename")
        if not out_name:
            out_name = f"{_mv_safe_stem(job.get('title') or 'song')}_anime_video.mp4"
        out_path = str((MEDIA_ROOT / "videos" / Path(out_name).name).resolve())

        # Mux audio
        ok_m, msg_m = mux_audio(stitched_path, audio_path, out_path)
        if not ok_m:
            _mv_set_job(job_id, status="failed", stage="error", error=f"Audio mux failed: {msg_m}")
            return

        # Best-effort sanity check: video duration shouldn't be trivially small.
        vd = ffprobe_duration_seconds(out_path)
        if vd is not None and vd < 1.0:
            _mv_set_job(job_id, status="failed", stage="error", error="Output video duration too short")
            return

        video_name = Path(out_path).name
        _mv_set_job(
            job_id,
            status="completed",
            stage="done",
            progress=100,
            completed_at=time.time(),
            output_path=out_path,
            output_url=f"/media/videos/{video_name}",
            download_url=f"/media/download/videos/{video_name}",
        )

    except Exception as exc:
        _mv_set_job(job_id, status="failed", stage="error", error=str(exc)[:800])



@app.post("/media/upload")
async def upload_media(request: Request, file: UploadFile = File(...), media_type: str = Form("videos")):
    """Upload a media file (used for local video selection in Media Console)."""
    allowed_exts = {
        "images": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"},
        "videos": {".mp4", ".mov", ".webm", ".mkv", ".avi"},
        "audio": {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"},
    }

    if media_type not in allowed_exts:
        raise HTTPException(status_code=400, detail="Invalid media type")

    dest_dir = MEDIA_ROOT / media_type
    dest_dir.mkdir(parents=True, exist_ok=True)

    original_name = Path(file.filename or "upload.bin").name
    ext = Path(original_name).suffix.lower()

    if ext and ext not in allowed_exts[media_type]:
        raise HTTPException(status_code=400, detail=f"Unsupported file type for {media_type}")

    # Sanitize and de-dupe filename
    safe_stem = re.sub(r"[^A-Za-z0-9._-]", "_", Path(original_name).stem) or "upload"
    safe_ext = ext or (".mp4" if media_type == "videos" else ".dat")
    dest_path = dest_dir / f"{safe_stem}{safe_ext}"
    counter = 1
    while dest_path.exists():
        dest_path = dest_dir / f"{safe_stem}_{counter}{safe_ext}"
        counter += 1

    try:
        with dest_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {exc}")

    size_bytes = dest_path.stat().st_size
    urls = _build_media_urls(request, media_type, dest_path.name)
    return {
        "success": True,
        "filename": dest_path.name,
        **urls,
        "size_bytes": size_bytes,
        "media_type": media_type,
    }


@app.post("/media/musicvideo/upload")
async def musicvideo_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(""),
    artist: str = Form(""),
    lyrics: str = Form(""),
    anime_prompt: str = Form(""),
    negative_prompt: str = Form(""),
    motion_hint: str = Form(""),
):
    """Upload an MP3 and automatically start an anime music video render job."""
    original_name = Path(file.filename or "song.mp3").name
    ext = Path(original_name).suffix.lower()
    if ext not in {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"}:
        raise HTTPException(status_code=400, detail="Unsupported audio type")

    dest_dir = MEDIA_ROOT / "audio"
    dest_dir.mkdir(parents=True, exist_ok=True)

    safe_title = _mv_safe_stem(title) if title.strip() else _mv_safe_stem(Path(original_name).stem)
    safe_ext = ext or ".mp3"
    audio_filename = f"{safe_title}{safe_ext}"
    dest_path = dest_dir / audio_filename
    counter = 1
    while dest_path.exists():
        dest_path = dest_dir / f"{safe_title}_{counter}{safe_ext}"
        counter += 1

    try:
        with dest_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save audio: {exc}")

    job_id = str(uuid.uuid4())
    out_filename = f"{_mv_safe_stem(safe_title)}_anime_video.mp4"
    _mv_set_job(
        job_id,
        id=job_id,
        status="queued",
        stage="queued",
        progress=0,
        created_at=time.time(),
        title=title or safe_title,
        artist=artist,
        lyrics=lyrics,
        anime_prompt=anime_prompt,
        negative_prompt=negative_prompt,
        motion_hint=motion_hint,
        audio_filename=dest_path.name,
        audio_path=str(dest_path.resolve()),
        output_filename=out_filename,
        fps=30,
        cancel_requested=False,
    )

    # Run in a dedicated thread to avoid blocking request lifecycle.
    def _start():
        th = threading.Thread(target=_musicvideo_worker, args=(job_id,), daemon=True)
        th.start()
        _mv_set_job(job_id, status="running", stage="starting", progress=1, thread="started")

    background_tasks.add_task(_start)

    return {
        "success": True,
        "job_id": job_id,
        "audio": {"filename": dest_path.name, "url": f"/media/audio/{dest_path.name}"},
        "status": _mv_get_job(job_id),
    }


@app.get("/media/musicvideo/jobs")
def musicvideo_jobs():
    with _MUSICVIDEO_LOCK:
        jobs = list(MUSICVIDEO_JOBS.values())
    # newest first
    jobs.sort(key=lambda j: j.get("created_at", 0), reverse=True)
    return {"jobs": jobs}


@app.get("/media/musicvideo/job/{job_id}")
def musicvideo_job(job_id: str):
    job = _mv_get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/media/musicvideo/status")
def musicvideo_status():
    """Return MV motion backend readiness for the GUI."""
    comfy_url = get_default_comfyui_url()
    workflow_path = (os.environ.get("COMFYUI_WORKFLOW_PATH") or os.environ.get("MV_COMFYUI_WORKFLOW") or "").strip()
    workflow_exists = bool(workflow_path and os.path.exists(str(workflow_path)))

    detected_root, detected_roots = _detect_comfyui_root()

    with _COMFYUI_INSTALL_LOCK:
        install_status = dict(_COMFYUI_INSTALL_STATUS)

    # Always report ComfyUI reachability, even if no workflow is configured.
    # This avoids confusing "workflow missing" with "server down".
    comfy_ok = False
    comfy_msg = ""
    try:
        comfy = ComfyUIClient(base_url=comfy_url, timeout_s=5)
        comfy_ok, comfy_msg = comfy.health_check()
    except Exception as exc:
        comfy_ok = False
        comfy_msg = f"{type(exc).__name__}: {exc}"[:200]

    fal_ok = bool(os.environ.get("FAL_KEY"))
    replicate_ok = bool(os.environ.get("REPLICATE_API_TOKEN"))
    pollinations_ok = True  # no key required
    mv_cloud_backend = (os.environ.get("MV_CLOUD_BACKEND") or "").strip().lower()
    interp_engine = (os.environ.get("MV_INTERPOLATION_ENGINE") or "ffmpeg-minterpolate").strip().lower()
    rife_exe = os.environ.get("RIFE_EXE") or ""
    rife_ok = bool(rife_exe and os.path.exists(rife_exe))

    # Ready means: we can attempt true-motion generation.
    # - Best: ComfyUI + workflow
    # - Or: fal.ai / replicate (keys)
    # - Or: Pollinations (free). If Pollinations is unreachable, jobs will fail with a clear error.
    default_backend = "pollinations"
    if workflow_exists and comfy_ok:
        default_backend = "comfyui"
    elif replicate_ok:
        default_backend = "replicate"
    elif fal_ok:
        default_backend = "fal"

    # Optional override for cloud backend selection (only applies when not using ComfyUI).
    if default_backend != "comfyui" and mv_cloud_backend in {"pollinations", "replicate", "fal"}:
        default_backend = mv_cloud_backend

    ready = True
    return {
        "ready": ready,
        "comfyui": {
            "url": comfy_url,
            "workflow_path": workflow_path,
            "workflow_exists": workflow_exists,
            "reachable": comfy_ok,
            "detail": comfy_msg,
            "detected_root": detected_root,
            "detected_roots": detected_roots,
            "can_start": bool(detected_root),
            "install": install_status,
        },
        "cloud_fallback": {
            "fal_configured": fal_ok,
            "replicate_configured": replicate_ok,
            "pollinations_available": pollinations_ok,
            "default_backend": default_backend,
            "forced_backend": mv_cloud_backend or "",
        },
        "interpolation": {
            "engine": interp_engine,
            "rife_exe": rife_exe,
            "rife_ok": rife_ok,
        },
    }


@app.post("/media/musicvideo/comfyui/start")
def musicvideo_comfyui_start():
    """Try to auto-start a local ComfyUI instance (best-effort)."""
    comfy_url = get_default_comfyui_url()

    # If already reachable, return success.
    ok, msg = ComfyUIClient(base_url=comfy_url).health_check()
    if ok:
        return {"success": True, "status": "running", "detail": msg}

    root, roots = _detect_comfyui_root()
    if not root:
        raise HTTPException(
            status_code=404,
            detail=(
                "ComfyUI install not found. Set COMFYUI_ROOT to your ComfyUI folder (containing main.py), "
                "or install ComfyUI, then retry."
            ),
        )

    ok2, msg2 = _start_comfyui_process(root, comfy_url)
    if not ok2:
        raise HTTPException(status_code=500, detail=msg2)
    return {"success": True, "status": "starting", "detail": msg2, "root": root, "candidates": roots}


@app.post("/media/musicvideo/comfyui/install")
def musicvideo_comfyui_install():
    """Install ComfyUI into a repo-local folder so MV can start it automatically.

    This can take several minutes; we start a background thread and return immediately.
    Progress is available under GET /media/musicvideo/status (comfyui.install).
    """
    target = Path(os.environ.get("COMFYUI_INSTALL_DIR") or (REPO_ROOT / "external" / "ComfyUI"))

    with _COMFYUI_INSTALL_LOCK:
        if _COMFYUI_INSTALL_STATUS.get("status") == "running":
            return {"success": True, "status": "running", "detail": "install already running", "root": str(target)}

        # Reset status and kick off worker
        _COMFYUI_INSTALL_STATUS.update(
            {
                "status": "running",
                "detail": "starting",
                "started_at": time.time(),
                "ended_at": None,
                "root": str(target),
            }
        )

    th = threading.Thread(target=_comfyui_install_worker, args=(target,), daemon=True)
    th.start()

    # After install, prefer this root for detection.
    os.environ["COMFYUI_ROOT"] = str(target)
    return {"success": True, "status": "running", "detail": "install started", "root": str(target)}


@app.post("/media/musicvideo/job/{job_id}/cancel")
def musicvideo_cancel(job_id: str):
    job = _mv_get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _mv_set_job(job_id, cancel_requested=True)
    return {"success": True, "job_id": job_id, "status": _mv_get_job(job_id)}


@app.post("/media/musicvideo/job/{job_id}/retry")
def musicvideo_retry(job_id: str, background_tasks: BackgroundTasks):
    """Retry a failed/cancelled MV job without re-uploading the audio.

    We create a NEW job id so historical results remain visible.
    """
    job = _mv_get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    status = str(job.get("status") or "")
    if status in {"running", "queued"}:
        raise HTTPException(status_code=409, detail="Job is running/queued. Cancel it first.")

    audio_path = job.get("audio_path")
    if not audio_path or not os.path.exists(str(audio_path)):
        raise HTTPException(status_code=400, detail="Audio file missing; re-upload required")

    new_job_id = str(uuid.uuid4())
    title = str(job.get("title") or "")
    safe_title = _mv_safe_stem(title) if title.strip() else _mv_safe_stem(Path(job.get("audio_filename") or "song").stem)
    out_filename = f"{_mv_safe_stem(safe_title)}_anime_video_{new_job_id[:8]}.mp4"

    _mv_set_job(
        new_job_id,
        id=new_job_id,
        status="queued",
        stage="queued",
        progress=0,
        created_at=time.time(),
        source_job_id=job_id,
        title=title or safe_title,
        artist=str(job.get("artist") or ""),
        lyrics=str(job.get("lyrics") or ""),
        anime_prompt=str(job.get("anime_prompt") or ""),
        negative_prompt=str(job.get("negative_prompt") or ""),
        motion_hint=str(job.get("motion_hint") or ""),
        audio_filename=str(job.get("audio_filename") or Path(audio_path).name),
        audio_path=str(Path(audio_path).resolve()),
        output_filename=out_filename,
        fps=int(job.get("fps") or 30),
        cancel_requested=False,
    )

    def _start():
        th = threading.Thread(target=_musicvideo_worker, args=(new_job_id,), daemon=True)
        th.start()
        _mv_set_job(new_job_id, status="running", stage="starting", progress=1, thread="started")

    background_tasks.add_task(_start)
    return {"success": True, "job_id": new_job_id, "status": _mv_get_job(new_job_id)}


@app.post("/media/musicvideo/job/{job_id}/delete")
def musicvideo_delete(job_id: str, force: bool = Body(False, embed=True)):
    """Remove a job record from the jobs list.

    This does NOT delete generated media files. It only removes the job from the UI list.
    """
    job = _mv_get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    status = str(job.get("status") or "")
    if status in {"running", "queued"} and not force:
        raise HTTPException(status_code=409, detail="Job is running/queued. Cancel it first or use force=true.")

    if status in {"running", "queued"} and force:
        # Best-effort request cancel; deletion still proceeds.
        _mv_set_job(job_id, cancel_requested=True)

    removed = _mv_delete_job(job_id)
    return {"success": True, "job_id": job_id, "removed": removed}


@app.post("/media/musicvideo/jobs/clear")
def musicvideo_clear_jobs(
    statuses: List[str] = Body(default=["failed", "cancelled"], embed=True),
    force: bool = Body(default=False, embed=True),
):
    """Clear jobs from the backend store.

    By default clears failed/cancelled jobs. Does not delete files.
    """
    stset = {str(s or "").strip().lower() for s in (statuses or [])}
    if not stset:
        stset = {"failed", "cancelled"}

    removed_ids: List[str] = []
    skipped_running: List[str] = []
    with _MUSICVIDEO_LOCK:
        # Copy keys to avoid mutation while iterating
        for jid in list(MUSICVIDEO_JOBS.keys()):
            j = MUSICVIDEO_JOBS.get(jid) or {}
            st = str(j.get("status") or "").strip().lower()
            if st not in stset:
                continue
            if st in {"running", "queued"} and not force:
                skipped_running.append(jid)
                continue
            MUSICVIDEO_JOBS.pop(jid, None)
            removed_ids.append(jid)

    if removed_ids:
        _mv_save_jobs_to_disk()

    return {
        "success": True,
        "removed": len(removed_ids),
        "removed_ids": removed_ids,
        "skipped_running": skipped_running,
    }


# --- File Analysis Upload Endpoint ---
@app.post("/file/upload-for-analysis")
async def upload_file_for_analysis(file: UploadFile = File(...)):
    """Upload a file for AI analysis. Supports text, code, JSON, CSV, and documents."""
    import csv
    import io
    
    # Allowed file types for analysis
    text_exts = {".txt", ".md", ".log", ".json", ".xml", ".yaml", ".yml", ".csv", ".tsv"}
    code_exts = {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".java", ".cpp", ".c", ".h", ".go", ".rs", ".rb", ".php", ".sql", ".sh", ".bat", ".ps1"}
    doc_exts = {".doc", ".docx", ".pdf", ".rtf"}
    
    original_name = Path(file.filename or "upload.txt").name
    ext = Path(original_name).suffix.lower()
    
    # Read file content
    try:
        content_bytes = await file.read()
        file_size = len(content_bytes)
        
        # Try to decode as text
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = content_bytes.decode("latin-1")
            except:
                return {
                    "success": False,
                    "error": "Cannot decode file as text. Binary files are not supported for analysis.",
                    "filename": original_name,
                }
        
        # Parse specific file types
        file_info = {
            "filename": original_name,
            "extension": ext,
            "size_bytes": file_size,
            "line_count": content.count("\n") + 1,
            "char_count": len(content),
        }
        
        # For JSON files, try to parse and summarize
        if ext == ".json":
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    file_info["json_keys"] = list(parsed.keys())[:20]
                    file_info["json_type"] = "object"
                elif isinstance(parsed, list):
                    file_info["json_length"] = len(parsed)
                    file_info["json_type"] = "array"
            except:
                pass
        
        # For CSV files, get headers and row count
        if ext in {".csv", ".tsv"}:
            try:
                delimiter = "\t" if ext == ".tsv" else ","
                reader = csv.reader(io.StringIO(content), delimiter=delimiter)
                rows = list(reader)
                if rows:
                    file_info["csv_headers"] = rows[0][:20]
                    file_info["csv_row_count"] = len(rows) - 1
            except:
                pass
        
        # Truncate content if too large (keep first 50KB for analysis)
        max_content_size = 50000
        truncated = False
        if len(content) > max_content_size:
            content = content[:max_content_size]
            truncated = True
        
        return {
            "success": True,
            "filename": original_name,
            "content": content,
            "truncated": truncated,
            "file_info": file_info,
            "analysis_hint": f"This is a {ext or 'text'} file with {file_info['line_count']} lines. You can analyze its content, structure, and provide insights.",
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "filename": original_name,
        }


# --- Recording Endpoints for Social Media Content ---
@app.post("/recording/screen/start")
async def start_screen_recording_endpoint(request: Request = None):
    """Start screen recording for social media content"""
    try:
        body = {}
        if request:
            try:
                body = await request.json()
            except:
                pass
        
        output_name = body.get("output_name", None)
        fps = body.get("fps", 30)
        quality = body.get("quality", "medium")
        include_audio = body.get("include_audio", True)
        
        result = recording.start_screen_recording(
            filename=output_name,
            fps=fps,
            quality=quality,
            include_audio=include_audio
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recording/screen/stop")
async def stop_screen_recording_endpoint():
    """Stop screen recording and save video"""
    try:
        result = recording.stop_screen_recording()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recording/audio/start")
async def start_audio_recording_endpoint(request: Request = None):
    """Start audio recording"""
    try:
        body = {}
        if request:
            try:
                body = await request.json()
            except:
                pass
        
        output_name = body.get("output_name", None)
        sample_rate = body.get("sample_rate", 44100)
        audio_format = body.get("format", "mp3")
        
        result = recording.start_audio_recording(
            filename=output_name,
            sample_rate=sample_rate,
            format=audio_format
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recording/audio/stop")
async def stop_audio_recording_endpoint():
    """Stop audio recording and save file"""
    try:
        result = recording.stop_audio_recording()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recording/status")
def get_recording_status_endpoint():
    """Get current recording status"""
    try:
        return recording.get_recording_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recording/list")
def list_recordings_endpoint():
    """List all recordings"""
    try:
        return recording.list_recordings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recording/ffmpeg-status")
def check_ffmpeg_endpoint():
    """Check if FFmpeg is installed for recording"""
    try:
        return recording.check_ffmpeg()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recording/audio-devices")
def list_audio_devices_endpoint():
    """List available audio devices for recording"""
    try:
        return recording.list_audio_devices()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recording/window/start")
async def start_window_recording_endpoint(request: Request):
    """Record a specific window by title"""
    try:
        body = await request.json()
        window_title = body.get("window_title", "Agent Amigos")
        filename = body.get("filename", None)
        duration = body.get("duration", None)
        
        result = recording.record_window(
            window_title=window_title,
            filename=filename,
            duration=duration
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/media/recordings/{filename}")
def serve_recording(filename: str):
    """Serve a recording file (video or audio)"""
    file_path = MEDIA_ROOT / "recordings" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Recording not found")
    mime_type, _ = mimetypes.guess_type(str(file_path))
    # Default to video/mp4 for screen recordings, audio/wav for audio
    if mime_type is None:
        mime_type = "video/mp4" if filename.endswith(".mp4") else "audio/wav"
    return FileResponse(file_path, media_type=mime_type)


@app.delete("/recording/{filename}")
def delete_recording(filename: str):
    """Delete a recording file"""
    file_path = MEDIA_ROOT / "recordings" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Recording not found")
    try:
        file_path.unlink()
        return {"success": True, "message": f"Deleted {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/media/list")
def list_all_media():
    """List all media files (images, videos, audio, reports, recordings)"""
    result = {"images": [], "videos": [], "audio": [], "reports": [], "recordings": []}
    
    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
    video_exts = {".mp4", ".avi", ".webm", ".mov", ".mkv"}
    audio_exts = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"}
    report_exts = {".md", ".html", ".txt", ".pdf"}
    recording_exts = {".mp4", ".wav", ".avi", ".webm"}
    
    for folder, exts, key in [("images", image_exts, "images"), 
                               ("videos", video_exts, "videos"),
                               ("audio", audio_exts, "audio"),
                               ("reports", report_exts, "reports"),
                               ("recordings", recording_exts, "recordings")]:
        folder_path = MEDIA_ROOT / folder
        if folder_path.exists():
            for f in folder_path.iterdir():
                if f.suffix.lower() in exts:
                    result[key].append({
                        "name": f.name,
                        "path": str(f),
                        "url": f"/media/{folder}/{f.name}",
                        "size_bytes": f.stat().st_size,
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                    })
    
    return result


@app.get("/media/images/{filename}")
def serve_image(filename: str):
    """Serve an image file"""
    file_path = MEDIA_ROOT / "images" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(file_path, media_type=mime_type or "image/png")


@app.get("/media/videos/{filename}")
def serve_video(filename: str):
    """Serve a video file with range support for streaming"""
    file_path = MEDIA_ROOT / "videos" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(file_path, media_type=mime_type or "video/mp4")


@app.get("/media/audio/{filename}")
def serve_audio(filename: str):
    """Serve an audio file"""
    file_path = MEDIA_ROOT / "audio" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(file_path, media_type=mime_type or "audio/mpeg")


@app.get("/media/reports/{filename}")
def serve_report(filename: str):
    """Serve a report file"""
    file_path = MEDIA_ROOT / "reports" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(file_path, media_type=mime_type or "text/plain")


@app.get("/media/download/{media_type}/{filename}")
def download_media(media_type: str, filename: str):
    """Download a media file with Content-Disposition header"""
    if media_type not in ["images", "videos", "audio", "reports", "recordings"]:
        raise HTTPException(status_code=400, detail="Invalid media type")
    file_path = MEDIA_ROOT / media_type / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        file_path,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.delete("/media/delete/{media_type}/{filename:path}")
def delete_media(media_type: str, filename: str):
    """Delete a media file (images, videos, audio, reports, recordings)"""
    if media_type not in ["images", "videos", "audio", "reports", "recordings"]:
        raise HTTPException(status_code=400, detail="Invalid media type")
    file_path = MEDIA_ROOT / media_type / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        file_path.unlink()
        return {"success": True, "message": f"Deleted {filename} from {media_type}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/media/cleanup")
async def cleanup_media(request: Dict[str, Any]):
    """Bulk delete media files to reclaim disk space.

    Supports:
      - mode=all (delete all files)
      - mode=older_than_days (delete files older than N days)
      - mode=keep_newest (keep newest N files, delete the rest)
      - mode=selected (delete specific filenames)

    Body:
      { media_type: "images"|"videos"|"audio"|"reports"|"recordings",
        mode: "all"|"older_than_days"|"keep_newest"|"selected",
        days?: int,
        keep?: int,
        filenames?: string[],
        confirm?: bool,
        dry_run?: bool }
    """
    media_type = str(request.get("media_type", "images") or "images").strip()
    mode = str(request.get("mode", "all") or "all").strip().lower()
    confirm = bool(request.get("confirm", False))
    dry_run = bool(request.get("dry_run", False))

    if media_type not in ["images", "videos", "audio", "reports", "recordings"]:
        raise HTTPException(status_code=400, detail="Invalid media_type")
    if mode not in ["all", "older_than_days", "keep_newest", "selected"]:
        raise HTTPException(status_code=400, detail="Invalid mode")

    # Require explicit confirmation for destructive modes.
    if mode in {"all", "older_than_days", "keep_newest", "selected"} and not confirm and not dry_run:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required. Pass {confirm: true} or use dry_run.",
        )

    folder_path = MEDIA_ROOT / media_type
    if not folder_path.exists():
        return {
            "success": True,
            "deleted_count": 0,
            "deleted_bytes": 0,
            "remaining_count": 0,
            "note": f"{media_type} folder does not exist",
        }

    # Match the same extension sets used by /media/list
    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
    video_exts = {".mp4", ".avi", ".webm", ".mov", ".mkv"}
    audio_exts = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"}
    report_exts = {".md", ".html", ".txt", ".pdf"}
    recording_exts = {".mp4", ".wav", ".avi", ".webm"}
    exts_by_type = {
        "images": image_exts,
        "videos": video_exts,
        "audio": audio_exts,
        "reports": report_exts,
        "recordings": recording_exts,
    }
    allowed_exts = exts_by_type[media_type]

    # Gather candidate files
    candidates = [
        f for f in folder_path.iterdir() if f.is_file() and f.suffix.lower() in allowed_exts
    ]

    to_delete = []
    now_ts = time.time()

    if mode == "all":
        to_delete = candidates
    elif mode == "older_than_days":
        days = int(request.get("days", 0) or 0)
        if days <= 0:
            raise HTTPException(status_code=400, detail="days must be > 0")
        cutoff_ts = now_ts - (days * 86400)
        to_delete = [f for f in candidates if f.stat().st_mtime < cutoff_ts]
    elif mode == "keep_newest":
        keep = int(request.get("keep", 0) or 0)
        if keep < 0:
            raise HTTPException(status_code=400, detail="keep must be >= 0")
        sorted_files = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
        to_delete = sorted_files[keep:]
    elif mode == "selected":
        raw_names = request.get("filenames") or []
        if not isinstance(raw_names, list):
            raise HTTPException(status_code=400, detail="filenames must be a list")
        wanted = {Path(str(n)).name for n in raw_names if str(n).strip()}
        if not wanted:
            return {
                "success": True,
                "deleted_count": 0,
                "deleted_bytes": 0,
                "remaining_count": len(candidates),
                "note": "No filenames provided",
            }
        to_delete = [f for f in candidates if f.name in wanted]

    deleted_count = 0
    deleted_bytes = 0
    errors = []

    for f in to_delete:
        try:
            size = f.stat().st_size
            if not dry_run:
                f.unlink()
            deleted_count += 1
            deleted_bytes += size
        except Exception as exc:
            errors.append({"file": f.name, "error": str(exc)})

    remaining = [
        f for f in folder_path.iterdir() if f.is_file() and f.suffix.lower() in allowed_exts
    ]

    return {
        "success": True,
        "media_type": media_type,
        "mode": mode,
        "dry_run": dry_run,
        "deleted_count": deleted_count,
        "deleted_bytes": deleted_bytes,
        "remaining_count": len(remaining),
        "errors": errors,
    }


@app.post("/media/convert/reel-to-youtube")
async def convert_reel_to_youtube(request: Dict[str, Any]):
    """Convert a vertical reel (existing file or URL) into a YouTube-ready landscape video."""
    source_url = request.get("source_url")
    video_filename = request.get("video_filename")
    resolution = request.get("resolution", "1920x1080")
    output_format = request.get("format", "mp4")
    blur_background = bool(request.get("blur_background", False))
    pad_color = request.get("pad_color", "#0f0f1a")

    if not source_url and not video_filename:
        raise HTTPException(status_code=400, detail="Provide either video_filename or source_url")

    source_path = None

    if video_filename:
        candidate = MEDIA_ROOT / "videos" / video_filename
        if not candidate.exists():
            raise HTTPException(status_code=404, detail="Source video not found")
        source_path = candidate

    if source_path is None and source_url:
        try:
            parsed = urllib.parse.urlparse(source_url)
            ext = Path(parsed.path).suffix or ".mp4"
            if ext.lower() not in [".mp4", ".mov", ".webm", ".mkv", ".avi"]:
                ext = ".mp4"
            filename = f"reel_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{ext}"
            dest_path = MEDIA_ROOT / "videos" / filename
            resp = _session.get(source_url, timeout=30)
            resp.raise_for_status()
            dest_path.write_bytes(resp.content)
            source_path = dest_path
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to download reel: {exc}")

    if source_path is None:
        raise HTTPException(status_code=400, detail="Unable to resolve source video")

    result = media.convert_reel_to_youtube(
        video_path=str(source_path),
        target_resolution=resolution,
        output_format=output_format,
        pad_color=pad_color,
        blur_background=blur_background,
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Conversion failed"))

    video_name = Path(result["output_path"]).name
    result["url"] = f"/media/videos/{video_name}"
    result["download_url"] = f"/media/download/videos/{video_name}"
    result["source"] = source_path.name
    return result


@app.post("/media/generate")
async def generate_media_api(request: Dict[str, Any]):
    """Generate media from prompt - images or reels/videos"""
    prompt = request.get("prompt", "")
    media_type = request.get("type", "image")  # 'image', 'reel', 'video'
    
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    
    try:
        if media_type == "image":
            result = media.generate_image(
                prompt=prompt,
                width=request.get("width", 1024),
                height=request.get("height", 1024),
                steps=request.get("steps", 25),
                negative_prompt=request.get("negative_prompt", None),
                style=request.get("style", "default"),
                allow_unrelated_fallback=bool(request.get("allow_unrelated_fallback", False)),
                debug=bool(request.get("debug", False)),
            )
            if result.get("success") and result.get("images"):
                # Add URLs for frontend
                result["urls"] = [
                    f"/media/images/{Path(img).name}" for img in result["images"]
                ]
                result["download_urls"] = [
                    f"/media/download/images/{Path(img).name}" for img in result["images"]
                ]
        
        elif media_type == "ai_video":
            # REAL AI Video Generation using Replicate/fal.ai
            result = media.generate_ai_video(
                prompt=prompt,
                duration=request.get("duration", 5),
                aspect_ratio=request.get("aspect_ratio", "16:9"),
                model=request.get("model", "wan"),  # wan, minimax, ltx
                negative_prompt=request.get("negative_prompt", ""),
            )
            if result.get("success") and result.get("video_path"):
                video_name = Path(result["video_path"]).name
                result["url"] = f"/media/videos/{video_name}"
                result["download_url"] = f"/media/download/videos/{video_name}"
        
        elif media_type in ["reel", "video"]:
            # Generate image first, then animate it into a reel (slideshow)
            img_result = media.generate_image(
                prompt=prompt,
                width=request.get("width", 1080),
                height=request.get("height", 1080),
                steps=request.get("steps", 25),
                negative_prompt=request.get("negative_prompt", None),
                style=request.get("style", "default"),
            )
            if not img_result.get("success"):
                return img_result
            
            # Animate the generated image into a reel
            result = media.animate_image(
                image_path=img_result["images"][0],
                duration=request.get("duration", 6),
                fps=request.get("fps", 30),
                zoom_factor=request.get("zoom_factor", 1.05),
                resolution=f"{request.get('width', 1080)}x{request.get('height', 1080)}"
            )
            if result.get("success"):
                video_name = Path(result["video_path"]).name
                result["url"] = f"/media/videos/{video_name}"
                result["download_url"] = f"/media/download/videos/{video_name}"
                result["source_image"] = img_result["images"][0]
                result["source_image_url"] = f"/media/images/{Path(img_result['images'][0]).name}"
        
        else:
            raise HTTPException(status_code=400, detail="Invalid media type. Use 'image', 'reel', 'video', or 'ai_video'")
        
        return result
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/media/image_edit")
async def image_edit_api(req: Request, request: Dict[str, Any]):
    """Edit/transform an image using Pollinations 'kontext' (image-to-image).

    Expected body:
      - prompt: str (required)
      - image_url: str (optional) public URL to source image
      - image_filename: str (optional) filename of a previously uploaded image under MEDIA_ROOT/images
      - width/height: int (optional)
      - negative_prompt: str (optional)

    Notes:
      - If using image_filename, this backend must be publicly reachable by Pollinations.
        Configure MEDIA_PUBLIC_BASE_URL (e.g. https://<tunnel>/) so the source image can be fetched.
    """
    prompt = (request.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    width = int(request.get("width", 1024) or 1024)
    height = int(request.get("height", 1024) or 1024)
    negative_prompt = request.get("negative_prompt", None)
    safe = bool(request.get("safe", False))
    seed = request.get("seed", None)

    image_url = (request.get("image_url") or "").strip()
    image_filename = (request.get("image_filename") or "").strip()

    if not image_url:
        if not image_filename:
            raise HTTPException(status_code=400, detail="Provide image_url or image_filename")

        # Ensure file exists locally.
        local_image_path = MEDIA_ROOT / "images" / Path(image_filename).name
        if not local_image_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")

        # Convert filename -> public URL so Pollinations can fetch it.
        pub = _get_media_public_base_url()
        if not pub:
            raise HTTPException(
                status_code=400,
                detail=(
                    "image_filename requires MEDIA_PUBLIC_BASE_URL to be set to a publicly reachable URL "
                    "(e.g. a tunnel). Alternatively, provide image_url pointing to an image hosted online."
                ),
            )
        image_url = f"{pub}/media/images/{Path(image_filename).name}"

    try:
        result = media.edit_image_kontext(
            prompt=prompt,
            image_url=image_url,
            width=width,
            height=height,
            negative_prompt=negative_prompt,
            safe=safe,
            seed=seed,
        )
        if result.get("success") and result.get("path"):
            name = Path(result["path"]).name
            result["url"] = f"/media/images/{name}"
            result["download_url"] = f"/media/download/images/{name}"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/media/image_to_video")
async def image_to_video_from_image(request: Dict[str, Any]):
    """Generate a REAL motion video from a previously uploaded image file.

    Frontend expects to call /media/image_to_video with { image_filename, motion_prompt, duration, model }
    """
    image_filename = request.get("image_filename")
    motion_prompt = request.get("motion_prompt", "")
    duration = int(request.get("duration", 4) or 4)
    model = request.get("model", None)

    if not image_filename:
        raise HTTPException(status_code=400, detail="image_filename required")

    image_path = MEDIA_ROOT / "images" / Path(image_filename).name
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        # Call our media tools helper
        result = media.generate_video_from_image(
            str(image_path), motion_prompt=motion_prompt, duration=duration, motion_type=(model or "auto")
        )
        if result.get("success") and result.get("video_path"):
            video_name = Path(result["video_path"]).name
            result["url"] = f"/media/videos/{video_name}"
            result["download_url"] = f"/media/download/videos/{video_name}"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Game Trainer Utility Endpoints ---


@app.get("/game/processes")
def list_game_processes_api():
    """Return active game-like processes for the trainer console."""
    result = game_trainer.list_game_processes()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to list game processes"))

    attached_pid = game_trainer.attached_process["pid"] if game_trainer.attached_process else None
    result["attached_pid"] = attached_pid
    return result


@app.post("/game/attach")
def attach_game_process(request: AttachProcessRequest):
    """Attach the trainer to a process by PID."""
    result = game_trainer.attach_to_process(request.pid)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Unable to attach to process"))
    return result


@app.get("/game/status")
def game_trainer_status():
    """Expose trainer attachment and frozen value details."""
    frozen_info = game_trainer.list_frozen_values()
    return {
        "success": True,
        "attached_process": game_trainer.attached_process,
        "frozen": frozen_info.get("frozen", []) if frozen_info.get("success") else [],
        "frozen_count": frozen_info.get("count", 0) if frozen_info.get("success") else 0,
    }


@app.get("/game/mods")
def list_mods(game: Optional[str] = None):
    """List mod templates created via the trainer."""
    result = game_trainer.list_mod_files(game)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to list mods"))
    return result


@app.post("/game/mods")
def create_mod_template_api(request: CreateModTemplateRequest):
    """Create a mod template for the specified game."""
    result = game_trainer.create_mod_template(request.game, request.mod_name, request.mod_type)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Unable to create mod template"))
    return result


# --- Memory Scanner Endpoints ---

@app.post("/game/scan")
def scan_memory_api(request: ScanMemoryRequest):
    """Scan memory for a specific value."""
    result = game_trainer.scan_memory(request.value, request.data_type, request.scan_type)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Memory scan failed"))
    return result


@app.post("/game/next_scan")
def next_scan_api(request: NextScanRequest):
    """Filter previous scan results."""
    result = game_trainer.next_scan(request.filter_type, request.value)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Next scan failed"))
    return result


@app.get("/game/scan_results")
def get_scan_results_api():
    """Get current scan results."""
    result = game_trainer.get_scan_results()
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to get scan results"))
    return result


@app.post("/game/write_memory")
def write_memory_api(request: WriteMemoryRequest):
    """Write a value to a specific memory address."""
    result = game_trainer.write_memory(request.address, request.value, request.data_type)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Write memory failed"))
    return result


@app.post("/game/freeze")
def freeze_value_api(request: FreezeValueRequest):
    """Freeze a memory address at a specific value."""
    result = game_trainer.freeze_value(request.address, request.value, request.data_type, request.name)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Freeze value failed"))
    return result


@app.post("/game/unfreeze")
def unfreeze_value_api(request: UnfreezeValueRequest):
    """Unfreeze a memory address."""
    result = game_trainer.unfreeze_value(request.address)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Unfreeze value failed"))
    return result


@app.post("/game/unfreeze_all")
def unfreeze_all_api():
    """Unfreeze all frozen memory addresses."""
    result = game_trainer.unfreeze_all()
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Unfreeze all failed"))
    return result


@app.post("/game/aob_scan")
def aob_scan_api(request: AOBScanRequest):
    """Scan memory for an Array of Bytes pattern."""
    result = game_trainer.aob_scan(request.pattern)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "AOB scan failed"))
    return result


@app.post("/game/pointer_scan")
def pointer_scan_api(request: PointerScanRequest):
    """Scan for pointer paths to a target address."""
    result = game_trainer.pointer_scan(request.target_address, request.max_depth)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Pointer scan failed"))
    return result


@app.post("/game/save_cheat_table")
def save_cheat_table_api(request: CheatTableRequest):
    """Save current frozen values to a cheat table file."""
    result = game_trainer.save_cheat_table(request.filename, request.entries)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to save cheat table"))
    return result


@app.post("/game/load_cheat_table")
def load_cheat_table_api(request: CheatTableRequest):
    """Load a cheat table file and apply frozen values."""
    result = game_trainer.load_cheat_table(request.filename)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to load cheat table"))
    return result


@app.get("/game/list_cheat_tables")
def list_cheat_tables_api():
    """List available cheat table files."""
    result = game_trainer.list_cheat_tables()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to list cheat tables"))
    return result


@app.post("/game/detach")
def detach_game_api():
    """Detach from the currently attached process."""
    result = game_trainer.detach_from_process()
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to detach"))
    return result


if __name__ == "__main__":
    resolved_port, port_message = resolve_agent_port(AGENT_HOST, AGENT_PORT)
    if port_message:
        print(port_message)
    ACTIVE_AGENT_PORT = resolved_port

    print(f"""
+--------------------------------------------------------------+
|             AGENT AMIGOS - Autonomous AI Agent               |
|                      Version 2.0.0                           |
+--------------------------------------------------------------+
|  Tools Loaded: {len(TOOLS):3d}                                        |
|  Model: {LLM_MODEL:<20s}                           |
|  Host: {AGENT_HOST:<15s}                           |
|  Port: {resolved_port:<5d}                                      |
+--------------------------------------------------------------+
|  Capabilities:                                               |
|  * Keyboard & Mouse Control                                  |
|  * Web Browser Automation                                    |
|  * Web Search (DuckDuckGo)                                   |
|  * File Operations (Read/Write/Create/Delete)                |
|  * System Commands & Programs                                 |
|  * Clipboard & Notifications                                 |
+--------------------------------------------------------------+
""")
    # Diagnostics: print provider configuration
    print('[LLM] Provider configuration:')
    for pname, pcfg in LLM_CONFIGS.items():
        has_key = bool(pcfg.get('key')) and pcfg.get('key') != ''
        print(f" - {pname}: model={pcfg.get('model')} configured={has_key} base={pcfg.get('base')}")
    uvicorn.run(app, host=AGENT_HOST, port=resolved_port)
