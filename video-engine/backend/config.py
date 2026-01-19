"""
Configuration for Agent Amigos Video Engine
Supports both cloud APIs and local open-source models
"""
import os
from pathlib import Path
from typing import Optional, Literal
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"
MODELS_DIR = BASE_DIR / "models"

# Create directories
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    """Video Engine Settings"""
    
    # API Keys (Free/Freemium services)
    DEAPI_KEY: str = os.getenv("DEAPI_KEY", "")
    SHOTSTACK_KEY: str = os.getenv("SHOTSTACK_KEY", "")
    OPENAI_KEY: str = os.getenv("OPENAI_KEY", "")
    REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN", "")
    HUGGINGFACE_TOKEN: str = os.getenv("HUGGINGFACE_TOKEN", os.getenv("HF_TOKEN", ""))
    STABILITY_API_KEY: str = os.getenv("STABILITY_API_KEY", "")
    
    # Model Selection
    USE_LOCAL_MODEL: bool = os.getenv("USE_LOCAL_MODEL", "false").lower() == "true"
    DEFAULT_VIDEO_MODEL: Literal["waver", "deapi", "replicate", "stability", "huggingface"] = "replicate"
    DEFAULT_IMAGE_MODEL: Literal["sdxl", "openai", "pollinations"] = "pollinations"
    
    # Video Settings
    DEFAULT_DURATION: int = 6
    DEFAULT_FPS: int = 24
    DEFAULT_RESOLUTION: str = "1080x1080"
    MAX_VIDEO_DURATION: int = 60
    
    # Compression Settings
    VIDEO_BITRATE: str = "8000k"
    VIDEO_CRF: int = 18
    FACEBOOK_REEL_FORMAT: bool = True
    
    # Processing
    USE_GPU: bool = os.getenv("USE_GPU", "true").lower() == "true"
    MAX_CONCURRENT_JOBS: int = 3
    JOB_TIMEOUT: int = 300  # 5 minutes
    
    # Watermark
    WATERMARK_TEXT: str = "#darrellbuttigieg #thesoldiersdream"
    ADD_WATERMARK: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def detect_gpu() -> dict:
    """Detect available GPU for acceleration"""
    gpu_info = {
        "cuda_available": False,
        "cuda_device": None,
        "mps_available": False,  # Apple Silicon
        "device": "cpu"
    }
    
    try:
        import torch
        if torch.cuda.is_available():
            gpu_info["cuda_available"] = True
            gpu_info["cuda_device"] = torch.cuda.get_device_name(0)
            gpu_info["device"] = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            gpu_info["mps_available"] = True
            gpu_info["device"] = "mps"
    except ImportError:
        pass
    
    return gpu_info


def get_best_model() -> str:
    """Determine best available model based on API keys and hardware"""
    # Check for API keys first (cloud is usually faster)
    if settings.REPLICATE_API_TOKEN:
        return "replicate"
    if settings.HUGGINGFACE_TOKEN:
        return "huggingface"
    if settings.STABILITY_API_KEY:
        return "stability"
    if settings.DEAPI_KEY:
        return "deapi"
    
    # Fall back to local if GPU available
    gpu = detect_gpu()
    if gpu["cuda_available"] or gpu["mps_available"]:
        return "waver"
    
    return "fallback"  # Ken Burns effect


# Video modes
class VideoMode:
    TEST = "test"
    SINGLE_CLIP = "single_clip"
    MULTI_SCENE = "multi_scene"
    FACEBOOK_REEL = "facebook_reel"
    MANGO_MANIA = "mango_mania"
    MILITARY_CLIP = "military_clip"
    CINEMATIC = "cinematic"


# Export configuration
VIDEO_MODES = {
    VideoMode.TEST: {"duration": 3, "scenes": 1, "resolution": "512x512"},
    VideoMode.SINGLE_CLIP: {"duration": 6, "scenes": 1, "resolution": "1080x1080"},
    VideoMode.MULTI_SCENE: {"duration": 15, "scenes": 3, "resolution": "1080x1080"},
    VideoMode.FACEBOOK_REEL: {"duration": 30, "scenes": 5, "resolution": "1080x1920"},
    VideoMode.MANGO_MANIA: {"duration": 10, "scenes": 2, "resolution": "1080x1080"},
    VideoMode.MILITARY_CLIP: {"duration": 20, "scenes": 4, "resolution": "1920x1080"},
    VideoMode.CINEMATIC: {"duration": 60, "scenes": 10, "resolution": "1920x1080"},
}
