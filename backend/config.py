"""
Global configuration for Agent Amigos backend.
"""
from typing import List

# Default LLM model used by server and clients when not otherwise specified
# Empty default means use provider-specific env vars or provider defaults.
DEFAULT_LLM_MODEL = None

# Models that we consider 'preview' or behind special flags
PREVIEW_MODELS: List[str] = ["raptor-mini"]

# When True, enforce DEFAULT_LLM_MODEL across all providers at runtime even if env-specific model is set.
ENFORCE_DEFAULT_MODEL = False

# Trusted model routing for different task types (fallbacks)
MODEL_ROUTING = {
    "default": DEFAULT_LLM_MODEL,
}

def get_default_model() -> str:
    return DEFAULT_LLM_MODEL

def set_default_model(model_name: str):
    global DEFAULT_LLM_MODEL
    DEFAULT_LLM_MODEL = model_name

def get_enforce_default() -> bool:
    return ENFORCE_DEFAULT_MODEL

def set_enforce_default(enforce: bool):
    global ENFORCE_DEFAULT_MODEL
    ENFORCE_DEFAULT_MODEL = bool(enforce)
