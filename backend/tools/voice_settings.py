
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

VOICE_CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "voice_settings.json"

DEFAULT_VOICES = [
    {"id": "pNInz6obpgmqEHC3fNo7", "name": "Adam (CEO)", "style": "Professional", "provider": "elevenlabs"},
    {"id": "Lcf7uRWj7BnUu85ty37p", "name": "Josh (Engineering)", "style": "Technical", "provider": "elevenlabs"},
    {"id": "MF3mGyEYCl7XYW7L9i06", "name": "Sam (Sales)", "style": "Energetic", "provider": "elevenlabs"},
    {"id": "TX38ocp6n383pSfsr2nd", "name": "Serena (Marketing)", "style": "Creative", "provider": "elevenlabs"},
    {"id": "VR6A6Nn20Hn9VndUe4W5", "name": "Rachel (Operations)", "style": "Calm", "provider": "elevenlabs"},
]

def get_available_voices():
    """List all available AI voices for the company agents."""
    return {
        "success": True,
        "voices": DEFAULT_VOICES,
        "message": "Select a voice ID to assign to an agent role."
    }

def set_agent_voice(agent_id: str, voice_id: str):
    """Assign a specific voice to an AI agent."""
    try:
        config = {}
        if VOICE_CONFIG_PATH.exists():
            with open(VOICE_CONFIG_PATH, "r") as f:
                config = json.load(f)
        
        config[agent_id] = voice_id
        
        VOICE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(VOICE_CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
            
        return {"success": True, "message": f"Voice {voice_id} assigned to {agent_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_agent_voice(agent_id: str):
    """Retrieve the voice ID for an agent."""
    if VOICE_CONFIG_PATH.exists():
        with open(VOICE_CONFIG_PATH, "r") as f:
            config = json.load(f)
            return config.get(agent_id)
    return None
