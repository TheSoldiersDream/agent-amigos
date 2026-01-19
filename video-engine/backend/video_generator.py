"""
Video Generator - Generate videos from images with AI motion
Uses free/open-source APIs: Replicate, HuggingFace, Stability AI, Local models
"""
import os
import base64
import urllib.request
import urllib.parse
import json
import asyncio
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from loguru import logger

from backend.config import settings, OUTPUT_DIR, TEMP_DIR, get_best_model


class VideoGenerator:
    """Generate videos with AI motion from images"""
    
    def __init__(self):
        self.output_dir = OUTPUT_DIR / "videos"
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir = TEMP_DIR
        self.temp_dir.mkdir(exist_ok=True)
    
    async def generate_from_image(
        self,
        image_path: str,
        motion_prompt: str = "",
        duration: int = 4,
        motion_type: str = "auto",
        model: str = "auto"
    ) -> Dict[str, Any]:
        """
        Generate a video with real motion from a still image
        
        Args:
            image_path: Path to source image
            motion_prompt: Description of desired motion
            duration: Video duration in seconds
            motion_type: Type of motion (walk, run, talk, dance, etc.)
            model: Model to use (auto, replicate, huggingface, stability, fallback)
        """
        if not os.path.exists(image_path):
            return {"success": False, "error": f"Image not found: {image_path}"}
        
        # Build motion prompt
        if not motion_prompt:
            motion_prompts = {
                "auto": "natural subtle movement, breathing, slight motion",
                "walk": "person walking forward naturally, smooth movement",
                "run": "running motion, dynamic movement, action",
                "talk": "person talking, mouth moving, natural gestures",
                "dance": "dancing motion, rhythmic movement",
                "wave": "waving hand, greeting gesture",
                "breathe": "subtle breathing motion, natural idle movement",
                "fly": "flying motion, wings flapping",
                "swim": "swimming motion through water",
                "pan": "camera panning across the scene",
                "zoom": "camera slowly zooming in",
            }
            motion_prompt = motion_prompts.get(motion_type, motion_prompts["auto"])
        
        # Determine which model to use
        if model == "auto":
            model = get_best_model()
        
        logger.info(f"Generating video from image with model: {model}")
        
        # Route to appropriate generator
        generators = {
            "replicate": self._generate_replicate,
            "huggingface": self._generate_huggingface,
            "stability": self._generate_stability,
            "deapi": self._generate_deapi,
            "waver": self._generate_waver_local,
            "fallback": self._generate_kenburns,
        }
        
        generator = generators.get(model, self._generate_kenburns)
        
        try:
            result = await generator(image_path, motion_prompt, duration)
            result["model_used"] = model
            return result
        except Exception as e:
            logger.error(f"Video generation with {model} failed: {e}")
            # Fallback to Ken Burns
            if model != "fallback":
                logger.info("Falling back to Ken Burns effect")
                result = await self._generate_kenburns(image_path, motion_prompt, duration)
                result["model_used"] = "fallback"
                result["fallback_reason"] = str(e)
                return result
            return {"success": False, "error": str(e)}
    
    async def _generate_replicate(self, image_path: str, motion_prompt: str, duration: int) -> Dict[str, Any]:
        """Use Replicate's Stable Video Diffusion"""
        if not settings.REPLICATE_API_TOKEN:
            return {"success": False, "error": "REPLICATE_API_TOKEN not configured"}
        
        try:
            # Read and encode image
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Detect mime type
            ext = Path(image_path).suffix.lower()
            mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
            mime_type = mime_types.get(ext, "image/png")
            data_uri = f"data:{mime_type};base64,{image_data}"
            
            headers = {
                "Authorization": f"Token {settings.REPLICATE_API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # Stable Video Diffusion model
            payload = {
                "version": "3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
                "input": {
                    "input_image": data_uri,
                    "motion_bucket_id": min(255, max(1, int(duration * 30))),
                    "fps": 8,
                    "num_frames": min(25, duration * 8),
                }
            }
            
            req = urllib.request.Request(
                "https://api.replicate.com/v1/predictions",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=30)
            )
            result = json.loads(response.read().decode("utf-8"))
            prediction_id = result.get("id")
            
            if not prediction_id:
                return {"success": False, "error": "No prediction ID returned"}
            
            logger.info(f"Replicate prediction started: {prediction_id}")
            
            # Poll for completion
            for _ in range(120):
                await asyncio.sleep(2)
                
                status_req = urllib.request.Request(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers={"Authorization": f"Token {settings.REPLICATE_API_TOKEN}"}
                )
                
                response = await loop.run_in_executor(
                    None,
                    lambda: urllib.request.urlopen(status_req, timeout=30)
                )
                status_result = json.loads(response.read().decode("utf-8"))
                
                status = status_result.get("status")
                
                if status == "succeeded":
                    output_url = status_result.get("output")
                    if output_url:
                        if isinstance(output_url, list):
                            output_url = output_url[0]
                        
                        # Download video
                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                        output_path = self.output_dir / f"video_{timestamp}.mp4"
                        
                        await loop.run_in_executor(
                            None,
                            lambda: urllib.request.urlretrieve(output_url, str(output_path))
                        )
                        
                        return {
                            "success": True,
                            "video_path": str(output_path),
                            "duration": duration,
                            "source": "replicate"
                        }
                
                elif status == "failed":
                    return {"success": False, "error": status_result.get("error", "Generation failed")}
            
            return {"success": False, "error": "Timeout waiting for video"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_huggingface(self, image_path: str, motion_prompt: str, duration: int) -> Dict[str, Any]:
        """Use HuggingFace Inference API"""
        token = settings.HUGGINGFACE_TOKEN
        if not token:
            return {"success": False, "error": "HUGGINGFACE_TOKEN not configured"}
        
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            headers = {"Authorization": f"Bearer {token}"}
            
            # Stable Video Diffusion on HuggingFace
            model_url = "https://api-inference.huggingface.co/models/stabilityai/stable-video-diffusion-img2vid-xt"
            
            req = urllib.request.Request(
                model_url,
                data=image_data,
                headers=headers,
                method="POST"
            )
            
            loop = asyncio.get_event_loop()
            logger.info("Calling HuggingFace SVD...")
            
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=180)
            )
            video_data = response.read()
            
            # Save video
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            output_path = self.output_dir / f"video_{timestamp}.mp4"
            
            with open(output_path, "wb") as f:
                f.write(video_data)
            
            return {
                "success": True,
                "video_path": str(output_path),
                "duration": duration,
                "source": "huggingface"
            }
            
        except urllib.error.HTTPError as e:
            if e.code == 503:
                return {"success": False, "error": "Model is loading, try again in a few minutes"}
            return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_stability(self, image_path: str, motion_prompt: str, duration: int) -> Dict[str, Any]:
        """Use Stability AI API"""
        if not settings.STABILITY_API_KEY:
            return {"success": False, "error": "STABILITY_API_KEY not configured"}
        
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            
            body = []
            body.append(f"--{boundary}".encode())
            body.append(b'Content-Disposition: form-data; name="image"; filename="image.png"')
            body.append(b"Content-Type: image/png")
            body.append(b"")
            body.append(image_data)
            body.append(f"--{boundary}".encode())
            body.append(b'Content-Disposition: form-data; name="seed"')
            body.append(b"")
            body.append(b"0")
            body.append(f"--{boundary}".encode())
            body.append(b'Content-Disposition: form-data; name="motion_bucket_id"')
            body.append(b"")
            body.append(str(min(255, duration * 40)).encode())
            body.append(f"--{boundary}--".encode())
            
            body_data = b"\r\n".join(body)
            
            headers = {
                "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            }
            
            req = urllib.request.Request(
                "https://api.stability.ai/v2beta/image-to-video",
                data=body_data,
                headers=headers,
                method="POST"
            )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=30)
            )
            result = json.loads(response.read().decode("utf-8"))
            generation_id = result.get("id")
            
            if not generation_id:
                return {"success": False, "error": "No generation ID returned"}
            
            # Poll for completion
            for _ in range(90):
                await asyncio.sleep(2)
                
                status_req = urllib.request.Request(
                    f"https://api.stability.ai/v2beta/image-to-video/result/{generation_id}",
                    headers={
                        "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
                        "Accept": "video/*"
                    }
                )
                
                try:
                    response = await loop.run_in_executor(
                        None,
                        lambda: urllib.request.urlopen(status_req, timeout=30)
                    )
                    
                    if response.status == 200:
                        video_data = response.read()
                        
                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                        output_path = self.output_dir / f"video_{timestamp}.mp4"
                        
                        with open(output_path, "wb") as f:
                            f.write(video_data)
                        
                        return {
                            "success": True,
                            "video_path": str(output_path),
                            "duration": duration,
                            "source": "stability"
                        }
                        
                except urllib.error.HTTPError as e:
                    if e.code == 202:
                        continue  # Still processing
                    raise
            
            return {"success": False, "error": "Timeout waiting for video"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_deapi(self, image_path: str, motion_prompt: str, duration: int) -> Dict[str, Any]:
        """Use deAPI free image-to-video service"""
        if not settings.DEAPI_KEY:
            return {"success": False, "error": "DEAPI_KEY not configured"}
        
        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            headers = {
                "Authorization": f"Bearer {settings.DEAPI_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "image": image_data,
                "prompt": motion_prompt,
                "duration": duration
            }
            
            # Note: Replace with actual deAPI endpoint
            req = urllib.request.Request(
                "https://api.deapi.com/v1/image-to-video",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=120)
            )
            result = json.loads(response.read().decode("utf-8"))
            
            if result.get("video_url"):
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                output_path = self.output_dir / f"video_{timestamp}.mp4"
                
                await loop.run_in_executor(
                    None,
                    lambda: urllib.request.urlretrieve(result["video_url"], str(output_path))
                )
                
                return {
                    "success": True,
                    "video_path": str(output_path),
                    "duration": duration,
                    "source": "deapi"
                }
            
            return {"success": False, "error": "No video URL returned"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_waver_local(self, image_path: str, motion_prompt: str, duration: int) -> Dict[str, Any]:
        """Use local Waver/open-source model"""
        try:
            # Check if local model is available
            try:
                import torch
                from diffusers import StableVideoDiffusionPipeline
            except ImportError:
                return {"success": False, "error": "Local models not installed. Run: pip install torch diffusers"}
            
            from PIL import Image
            
            logger.info("Loading local Stable Video Diffusion model...")
            
            # Load model (cached after first load)
            pipe = StableVideoDiffusionPipeline.from_pretrained(
                "stabilityai/stable-video-diffusion-img2vid-xt",
                torch_dtype=torch.float16,
                variant="fp16"
            )
            
            # Move to GPU if available
            device = "cuda" if torch.cuda.is_available() else "cpu"
            pipe.to(device)
            
            # Load and resize image
            image = Image.open(image_path).convert("RGB")
            image = image.resize((1024, 576))  # SVD expects this size
            
            logger.info("Generating video with local model...")
            
            # Generate frames
            loop = asyncio.get_event_loop()
            frames = await loop.run_in_executor(
                None,
                lambda: pipe(
                    image,
                    num_frames=min(25, duration * 7),
                    num_inference_steps=25,
                    motion_bucket_id=127,
                    decode_chunk_size=8
                ).frames[0]
            )
            
            # Save video
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            output_path = self.output_dir / f"video_{timestamp}.mp4"
            
            # Export frames to video using moviepy
            from moviepy.editor import ImageSequenceClip
            import numpy as np
            
            frame_arrays = [np.array(frame) for frame in frames]
            clip = ImageSequenceClip(frame_arrays, fps=7)
            clip.write_videofile(
                str(output_path),
                codec="libx264",
                audio=False,
                preset="medium",
                logger=None
            )
            clip.close()
            
            return {
                "success": True,
                "video_path": str(output_path),
                "duration": len(frames) / 7,
                "source": "waver_local"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_kenburns(self, image_path: str, motion_prompt: str, duration: int) -> Dict[str, Any]:
        """Fallback: Enhanced Ken Burns effect with dramatic motion"""
        try:
            from PIL import Image, ImageFilter, ImageEnhance
            from moviepy.editor import ImageSequenceClip
            import numpy as np
            
            logger.info("Generating enhanced Ken Burns video...")
            
            # Load image
            img = Image.open(image_path).convert("RGB")
            orig_w, orig_h = img.size
            
            # Target resolution
            target_w, target_h = 1080, 1080
            
            # Determine motion based on prompt
            zoom_factor = 1.35  # 35% zoom - very noticeable
            pan_direction = "center"
            
            if "walk" in motion_prompt.lower() or "left" in motion_prompt.lower():
                pan_direction = "right"
            elif "right" in motion_prompt.lower():
                pan_direction = "left"
            elif "up" in motion_prompt.lower() or "fly" in motion_prompt.lower():
                pan_direction = "up"
            elif "down" in motion_prompt.lower() or "fall" in motion_prompt.lower():
                pan_direction = "down"
            
            # Calculate working canvas
            work_scale = zoom_factor + 0.15
            work_w = int(target_w * work_scale)
            work_h = int(target_h * work_scale)
            
            # High-quality resize
            img = img.resize((work_w, work_h), Image.Resampling.LANCZOS)
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=2))
            
            # Generate frames
            fps = settings.DEFAULT_FPS
            total_frames = int(duration * fps)
            frames = []
            
            for frame_idx in range(total_frames):
                t = frame_idx / total_frames
                
                # Smooth easing function
                t_eased = 0.5 - 0.5 * np.cos(t * np.pi)  # Smooth start/end
                
                # Calculate zoom
                current_zoom = 1.0 + (zoom_factor - 1.0) * t_eased
                
                # Calculate crop size
                crop_w = int(target_w / current_zoom)
                crop_h = int(target_h / current_zoom)
                
                # Calculate pan
                max_offset_x = (work_w - crop_w) // 2
                max_offset_y = (work_h - crop_h) // 2
                
                center_x = work_w // 2
                center_y = work_h // 2
                
                if pan_direction == "left":
                    offset_x = int(max_offset_x * (1 - t_eased * 2))
                    offset_y = 0
                elif pan_direction == "right":
                    offset_x = int(-max_offset_x * (1 - t_eased * 2))
                    offset_y = 0
                elif pan_direction == "up":
                    offset_x = 0
                    offset_y = int(max_offset_y * (1 - t_eased * 2))
                elif pan_direction == "down":
                    offset_x = 0
                    offset_y = int(-max_offset_y * (1 - t_eased * 2))
                else:
                    offset_x = 0
                    offset_y = 0
                
                # Crop
                left = max(0, min(center_x - crop_w // 2 + offset_x, work_w - crop_w))
                top = max(0, min(center_y - crop_h // 2 + offset_y, work_h - crop_h))
                
                frame = img.crop((left, top, left + crop_w, top + crop_h))
                
                # Resize to target
                if frame.size != (target_w, target_h):
                    frame = frame.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    frame = frame.filter(ImageFilter.UnsharpMask(radius=1.5, percent=80, threshold=2))
                
                frames.append(np.array(frame))
            
            # Create video
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            output_path = self.output_dir / f"video_{timestamp}.mp4"
            
            clip = ImageSequenceClip(frames, fps=fps)
            clip.write_videofile(
                str(output_path),
                fps=fps,
                codec="libx264",
                audio=False,
                preset="slow",
                bitrate=settings.VIDEO_BITRATE,
                ffmpeg_params=["-crf", str(settings.VIDEO_CRF)],
                logger=None
            )
            clip.close()
            
            return {
                "success": True,
                "video_path": str(output_path),
                "duration": duration,
                "source": "kenburns",
                "note": "Used Ken Burns effect (AI APIs not available)"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def generate_test_video(self) -> Dict[str, Any]:
        """Generate a simple test video to verify the pipeline"""
        try:
            from PIL import Image, ImageDraw
            import numpy as np
            
            # Create test image
            img = Image.new('RGB', (512, 512), color=(50, 50, 80))
            draw = ImageDraw.Draw(img)
            draw.ellipse([156, 156, 356, 356], fill=(100, 150, 200))
            draw.text((180, 240), "Test Video", fill=(255, 255, 255))
            
            # Save temp image
            test_image = self.temp_dir / "test_image.png"
            img.save(str(test_image))
            
            # Generate video
            result = await self.generate_from_image(
                image_path=str(test_image),
                motion_prompt="gentle zoom",
                duration=3,
                model="fallback"
            )
            
            # Cleanup
            test_image.unlink()
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
