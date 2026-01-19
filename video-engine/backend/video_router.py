"""
Video Router - API endpoints for video generation
"""
import os
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Literal

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from loguru import logger

from backend.config import settings, OUTPUT_DIR, VideoMode, VIDEO_MODES, get_best_model
from backend.image_generator import ImageGenerator
from backend.video_generator import VideoGenerator
from backend.editor import VideoEditor

router = APIRouter()


# ============== Request/Response Models ==============

class VideoCreateRequest(BaseModel):
    """Request model for video creation"""
    prompt: str = Field(..., description="Text prompt describing the video")
    duration: int = Field(default=6, ge=2, le=60, description="Video duration in seconds")
    mode: str = Field(default="single_clip", description="Video mode (test, single_clip, multi_scene, etc.)")
    model: Optional[str] = Field(default=None, description="Model to use (auto, replicate, huggingface, etc.)")
    resolution: Optional[str] = Field(default="1080x1080", description="Output resolution")
    motion_type: str = Field(default="auto", description="Type of motion (walk, run, talk, dance, etc.)")
    add_watermark: bool = Field(default=True, description="Add Agent Amigos watermark")
    add_music: bool = Field(default=False, description="Add background music")
    style: str = Field(default="cinematic", description="Visual style (cinematic, anime, realistic, etc.)")


class VideoFromImageRequest(BaseModel):
    """Request for image-to-video generation"""
    image_path: str = Field(..., description="Path to source image")
    motion_prompt: str = Field(default="", description="Description of desired motion")
    duration: int = Field(default=4, ge=2, le=10)
    motion_type: str = Field(default="auto")


class MultiSceneRequest(BaseModel):
    """Request for multi-scene video generation"""
    scenes: List[str] = Field(..., description="List of scene prompts")
    duration_per_scene: int = Field(default=5, ge=2, le=15)
    transitions: str = Field(default="crossfade", description="Transition type between scenes")
    add_intro: bool = Field(default=False)
    add_outro: bool = Field(default=False)


class VideoResponse(BaseModel):
    """Response model for video generation"""
    success: bool
    job_id: str
    status: str
    video_path: Optional[str] = None
    video_url: Optional[str] = None
    duration: Optional[float] = None
    model_used: Optional[str] = None
    scenes_generated: int = 0
    message: Optional[str] = None
    error: Optional[str] = None


class JobStatus(BaseModel):
    """Job status response"""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0.0 to 1.0
    current_step: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


# ============== Job Tracking ==============

# Simple in-memory job storage (use Redis in production)
jobs = {}


def create_job(prompt: str) -> str:
    """Create a new job and return its ID"""
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "id": job_id,
        "status": "pending",
        "progress": 0.0,
        "prompt": prompt,
        "created_at": datetime.utcnow().isoformat(),
        "result": None,
        "error": None
    }
    return job_id


def update_job(job_id: str, **kwargs):
    """Update job status"""
    if job_id in jobs:
        jobs[job_id].update(kwargs)


# ============== Video Generation Endpoints ==============

@router.post("/create", response_model=VideoResponse)
async def create_video(request: VideoCreateRequest, background_tasks: BackgroundTasks):
    """
    Create a video from a text prompt
    
    This is the main endpoint for video generation. It:
    1. Generates keyframe images based on the prompt
    2. Animates the images using AI video models
    3. Optionally adds effects, watermarks, and music
    4. Returns the final video
    """
    logger.info(f"Video creation request: {request.prompt[:50]}...")
    
    # Create job
    job_id = create_job(request.prompt)
    
    # Determine model to use
    model = request.model or get_best_model()
    
    # Get mode config
    mode_config = VIDEO_MODES.get(request.mode, VIDEO_MODES[VideoMode.SINGLE_CLIP])
    
    # Start background processing
    background_tasks.add_task(
        process_video_creation,
        job_id=job_id,
        prompt=request.prompt,
        duration=request.duration or mode_config["duration"],
        model=model,
        resolution=request.resolution or mode_config["resolution"],
        motion_type=request.motion_type,
        add_watermark=request.add_watermark,
        style=request.style,
        num_scenes=mode_config["scenes"]
    )
    
    return VideoResponse(
        success=True,
        job_id=job_id,
        status="processing",
        message=f"Video generation started. Use /video/status/{job_id} to check progress."
    )


async def process_video_creation(
    job_id: str,
    prompt: str,
    duration: int,
    model: str,
    resolution: str,
    motion_type: str,
    add_watermark: bool,
    style: str,
    num_scenes: int = 1
):
    """Background task for video creation"""
    try:
        update_job(job_id, status="processing", progress=0.1, current_step="Initializing...")
        
        image_gen = ImageGenerator()
        video_gen = VideoGenerator()
        editor = VideoEditor()
        
        # Step 1: Generate keyframe images
        update_job(job_id, progress=0.2, current_step="Generating keyframes...")
        logger.info(f"[{job_id}] Generating {num_scenes} keyframe(s)...")
        
        keyframes = []
        for i in range(num_scenes):
            scene_prompt = f"{prompt}, scene {i+1}" if num_scenes > 1 else prompt
            image_result = await image_gen.generate_keyframe(
                prompt=scene_prompt,
                style=style,
                resolution=resolution
            )
            if image_result.get("success"):
                keyframes.append(image_result["image_path"])
                update_job(job_id, progress=0.2 + (0.3 * (i+1) / num_scenes))
        
        if not keyframes:
            raise Exception("Failed to generate keyframe images")
        
        # Step 2: Generate video from keyframes
        update_job(job_id, progress=0.5, current_step="Generating video animation...")
        logger.info(f"[{job_id}] Animating keyframes with model: {model}")
        
        video_clips = []
        clip_duration = duration // len(keyframes)
        
        for i, keyframe in enumerate(keyframes):
            video_result = await video_gen.generate_from_image(
                image_path=keyframe,
                motion_prompt=prompt,
                duration=clip_duration,
                motion_type=motion_type,
                model=model
            )
            if video_result.get("success"):
                video_clips.append(video_result["video_path"])
                update_job(job_id, progress=0.5 + (0.3 * (i+1) / len(keyframes)))
        
        if not video_clips:
            raise Exception("Failed to generate video clips")
        
        # Step 3: Merge clips and add effects
        update_job(job_id, progress=0.8, current_step="Finalizing video...")
        
        # Merge if multiple clips
        if len(video_clips) > 1:
            final_video = await editor.merge_clips(
                video_clips,
                transition="crossfade",
                output_name=f"video_{job_id}"
            )
        else:
            final_video = video_clips[0]
        
        # Add watermark if enabled
        if add_watermark and settings.ADD_WATERMARK:
            final_video = await editor.add_watermark(
                final_video,
                text=settings.WATERMARK_TEXT
            )
        
        # Step 4: Compress for web
        update_job(job_id, progress=0.9, current_step="Compressing for web...")
        final_video = await editor.compress_for_web(final_video)
        
        # Complete
        update_job(
            job_id,
            status="completed",
            progress=1.0,
            current_step="Done!",
            result={
                "video_path": final_video,
                "video_url": f"/output/videos/{Path(final_video).name}",
                "duration": duration,
                "model_used": model,
                "scenes_generated": len(keyframes)
            }
        )
        
        logger.info(f"[{job_id}] Video generation completed: {final_video}")
        
    except Exception as e:
        logger.error(f"[{job_id}] Video generation failed: {e}")
        update_job(job_id, status="failed", error=str(e))


@router.post("/from-image", response_model=VideoResponse)
async def create_video_from_image(request: VideoFromImageRequest, background_tasks: BackgroundTasks):
    """Create video with real motion from an existing image"""
    logger.info(f"Image-to-video request: {request.image_path}")
    
    if not os.path.exists(request.image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    job_id = create_job(f"Image: {request.image_path}")
    model = get_best_model()
    
    background_tasks.add_task(
        process_image_to_video,
        job_id=job_id,
        image_path=request.image_path,
        motion_prompt=request.motion_prompt,
        duration=request.duration,
        motion_type=request.motion_type,
        model=model
    )
    
    return VideoResponse(
        success=True,
        job_id=job_id,
        status="processing",
        message="Image-to-video generation started"
    )


async def process_image_to_video(
    job_id: str,
    image_path: str,
    motion_prompt: str,
    duration: int,
    motion_type: str,
    model: str
):
    """Background task for image-to-video"""
    try:
        update_job(job_id, status="processing", progress=0.1)
        
        video_gen = VideoGenerator()
        result = await video_gen.generate_from_image(
            image_path=image_path,
            motion_prompt=motion_prompt,
            duration=duration,
            motion_type=motion_type,
            model=model
        )
        
        if result.get("success"):
            update_job(
                job_id,
                status="completed",
                progress=1.0,
                result=result
            )
        else:
            update_job(job_id, status="failed", error=result.get("error"))
            
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))


@router.post("/multi-scene", response_model=VideoResponse)
async def create_multi_scene_video(request: MultiSceneRequest, background_tasks: BackgroundTasks):
    """Create a video with multiple scenes"""
    logger.info(f"Multi-scene video request: {len(request.scenes)} scenes")
    
    job_id = create_job(f"Multi-scene: {len(request.scenes)} scenes")
    
    background_tasks.add_task(
        process_multi_scene,
        job_id=job_id,
        scenes=request.scenes,
        duration_per_scene=request.duration_per_scene,
        transitions=request.transitions,
        add_intro=request.add_intro,
        add_outro=request.add_outro
    )
    
    return VideoResponse(
        success=True,
        job_id=job_id,
        status="processing",
        message=f"Multi-scene video with {len(request.scenes)} scenes started"
    )


async def process_multi_scene(
    job_id: str,
    scenes: List[str],
    duration_per_scene: int,
    transitions: str,
    add_intro: bool,
    add_outro: bool
):
    """Process multi-scene video creation"""
    try:
        update_job(job_id, status="processing", progress=0.1)
        
        image_gen = ImageGenerator()
        video_gen = VideoGenerator()
        editor = VideoEditor()
        
        video_clips = []
        total_scenes = len(scenes)
        
        for i, scene_prompt in enumerate(scenes):
            update_job(
                job_id,
                progress=0.1 + (0.7 * i / total_scenes),
                current_step=f"Processing scene {i+1}/{total_scenes}"
            )
            
            # Generate keyframe
            image_result = await image_gen.generate_keyframe(scene_prompt)
            if not image_result.get("success"):
                continue
            
            # Animate
            video_result = await video_gen.generate_from_image(
                image_path=image_result["image_path"],
                motion_prompt=scene_prompt,
                duration=duration_per_scene
            )
            if video_result.get("success"):
                video_clips.append(video_result["video_path"])
        
        if not video_clips:
            raise Exception("No scenes could be generated")
        
        # Merge all clips
        update_job(job_id, progress=0.85, current_step="Merging scenes...")
        final_video = await editor.merge_clips(
            video_clips,
            transition=transitions,
            output_name=f"multiscene_{job_id}"
        )
        
        # Add intro/outro if requested
        if add_intro:
            final_video = await editor.add_intro(final_video)
        if add_outro:
            final_video = await editor.add_outro(final_video)
        
        update_job(
            job_id,
            status="completed",
            progress=1.0,
            result={
                "video_path": final_video,
                "video_url": f"/output/videos/{Path(final_video).name}",
                "scenes_generated": len(video_clips),
                "total_duration": len(video_clips) * duration_per_scene
            }
        )
        
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))


# ============== Job Management ==============

@router.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a video generation job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return JobStatus(
        job_id=job["id"],
        status=job["status"],
        progress=job["progress"],
        current_step=job.get("current_step"),
        result=job.get("result"),
        error=job.get("error")
    )


@router.get("/jobs")
async def list_jobs():
    """List all video generation jobs"""
    return {"jobs": list(jobs.values())}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its output"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs.pop(job_id)
    
    # Clean up output files
    if job.get("result", {}).get("video_path"):
        try:
            os.remove(job["result"]["video_path"])
        except:
            pass
    
    return {"message": f"Job {job_id} deleted"}


# ============== Quick Generation (Synchronous) ==============

@router.post("/quick")
async def quick_video(prompt: str = Form(...), duration: int = Form(default=4)):
    """
    Quick synchronous video generation (waits for result)
    Best for short videos (< 10 seconds)
    """
    logger.info(f"Quick video: {prompt[:50]}...")
    
    image_gen = ImageGenerator()
    video_gen = VideoGenerator()
    
    # Generate keyframe
    image_result = await image_gen.generate_keyframe(prompt)
    if not image_result.get("success"):
        raise HTTPException(status_code=500, detail="Failed to generate keyframe")
    
    # Generate video
    video_result = await video_gen.generate_from_image(
        image_path=image_result["image_path"],
        motion_prompt=prompt,
        duration=duration
    )
    
    if video_result.get("success"):
        return {
            "success": True,
            "video_path": video_result["video_path"],
            "video_url": f"/output/videos/{Path(video_result['video_path']).name}",
            "model_used": video_result.get("model_used", "unknown")
        }
    else:
        raise HTTPException(status_code=500, detail=video_result.get("error", "Generation failed"))


# ============== Download Endpoint ==============

@router.get("/download/{filename}")
async def download_video(filename: str):
    """Download a generated video"""
    video_path = OUTPUT_DIR / "videos" / filename
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=filename
    )
