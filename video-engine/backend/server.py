"""
FastAPI Server for Agent Amigos Video Engine
Main entry point for the video generation API
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from loguru import logger

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings, detect_gpu, get_best_model, OUTPUT_DIR, VideoMode, VIDEO_MODES
from backend.video_router import router as video_router

# Configure logging
logger.add(
    "logs/video_engine_{time}.log",
    rotation="10 MB",
    level=settings.LOG_LEVEL,
    format="{time} | {level} | {message}"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🎬 Agent Amigos Video Engine starting...")
    gpu_info = detect_gpu()
    logger.info(f"GPU Detection: {gpu_info}")
    logger.info(f"Best available model: {get_best_model()}")
    
    # Create output directories
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "videos").mkdir(exist_ok=True)
    (OUTPUT_DIR / "images").mkdir(exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("Video Engine shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Agent Amigos Video Engine",
    description="AI-powered video generation using open-source and free APIs",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(video_router, prefix="/video", tags=["Video Generation"])

# Serve static files (output videos)
if OUTPUT_DIR.exists():
    app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")


# ============== API Models ==============

class HealthResponse(BaseModel):
    status: str
    gpu_available: bool
    gpu_device: Optional[str]
    best_model: str
    api_keys_configured: dict
    timestamp: str


class SystemInfoResponse(BaseModel):
    version: str
    available_modes: dict
    supported_models: list
    gpu_info: dict
    settings: dict


# ============== Core Endpoints ==============

@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Agent Amigos Video Engine",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "video_create": "/video/create"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with system status"""
    gpu_info = detect_gpu()
    
    return HealthResponse(
        status="healthy",
        gpu_available=gpu_info["cuda_available"] or gpu_info["mps_available"],
        gpu_device=gpu_info.get("cuda_device"),
        best_model=get_best_model(),
        api_keys_configured={
            "replicate": bool(settings.REPLICATE_API_TOKEN),
            "huggingface": bool(settings.HUGGINGFACE_TOKEN),
            "stability": bool(settings.STABILITY_API_KEY),
            "deapi": bool(settings.DEAPI_KEY),
            "shotstack": bool(settings.SHOTSTACK_KEY),
            "openai": bool(settings.OPENAI_KEY),
        },
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/system", response_model=SystemInfoResponse)
async def system_info():
    """Get detailed system information"""
    gpu_info = detect_gpu()
    
    return SystemInfoResponse(
        version="1.0.0",
        available_modes=VIDEO_MODES,
        supported_models=[
            "replicate (Stable Video Diffusion)",
            "huggingface (SVD, AnimateDiff)",
            "stability (Stability AI)",
            "deapi (Free image-to-video)",
            "waver (Local open-source)",
            "fallback (Ken Burns effect)"
        ],
        gpu_info=gpu_info,
        settings={
            "default_duration": settings.DEFAULT_DURATION,
            "default_fps": settings.DEFAULT_FPS,
            "default_resolution": settings.DEFAULT_RESOLUTION,
            "use_gpu": settings.USE_GPU,
            "use_local_model": settings.USE_LOCAL_MODEL,
            "add_watermark": settings.ADD_WATERMARK,
        }
    )


@app.get("/models")
async def list_models():
    """List available video generation models"""
    models = []
    
    # Cloud APIs
    if settings.REPLICATE_API_TOKEN:
        models.append({
            "id": "replicate",
            "name": "Replicate - Stable Video Diffusion",
            "type": "cloud",
            "status": "available",
            "quality": "high",
            "speed": "medium"
        })
    
    if settings.HUGGINGFACE_TOKEN:
        models.append({
            "id": "huggingface", 
            "name": "HuggingFace - SVD/AnimateDiff",
            "type": "cloud",
            "status": "available",
            "quality": "high",
            "speed": "slow"
        })
    
    if settings.STABILITY_API_KEY:
        models.append({
            "id": "stability",
            "name": "Stability AI - Video Generation",
            "type": "cloud",
            "status": "available",
            "quality": "highest",
            "speed": "medium"
        })
    
    if settings.DEAPI_KEY:
        models.append({
            "id": "deapi",
            "name": "deAPI - Free Image-to-Video",
            "type": "cloud",
            "status": "available",
            "quality": "medium",
            "speed": "fast"
        })
    
    # Local models
    gpu_info = detect_gpu()
    if gpu_info["cuda_available"]:
        models.append({
            "id": "waver",
            "name": "Waver - Local Open Source",
            "type": "local",
            "status": "available" if settings.USE_LOCAL_MODEL else "disabled",
            "quality": "high",
            "speed": "depends on GPU"
        })
    
    # Fallback always available
    models.append({
        "id": "fallback",
        "name": "Ken Burns Effect (Enhanced)",
        "type": "local",
        "status": "always_available",
        "quality": "basic",
        "speed": "fast"
    })
    
    return {"models": models, "recommended": get_best_model()}


# ============== Quick Test Endpoints ==============

@app.get("/video/test")
async def test_video_generation():
    """Quick test to verify video generation works"""
    from backend.video_generator import VideoGenerator
    
    generator = VideoGenerator()
    result = await generator.generate_test_video()
    
    if result.get("success"):
        return {
            "status": "success",
            "message": "Video generation test passed!",
            "video_path": result.get("video_path"),
            "model_used": result.get("model_used")
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Test failed"))


# ============== Run Server ==============

if __name__ == "__main__":
    import uvicorn
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    logger.info("Starting Agent Amigos Video Engine...")
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8081,  # Different from main backend
        reload=True,
        log_level="info"
    )
