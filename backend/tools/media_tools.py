"""Media generation tools for images, videos, and audio."""
from __future__ import annotations

import os
import random
import textwrap
import subprocess
import shutil
import base64
import json
import time
import urllib.request
import urllib.parse
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
import logging

# Set up logging
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Prompt defaults / guardrails
# ------------------------------------------------------------------

# A strong default list of things we *generally* want to avoid in generated images.
# This is applied automatically unless the caller explicitly overrides it.
DEFAULT_IMAGE_NEGATIVE_PROMPT = os.environ.get(
    "DEFAULT_IMAGE_NEGATIVE_PROMPT",
    "lowres, blurry, out of focus, worst quality, low quality, jpeg artifacts, watermark, signature, logo, "
    "bad anatomy, bad proportions, deformed, disfigured, malformed, extra limbs, extra arms, extra legs, extra fingers, fused fingers, "
    "missing fingers, mutated hands, poorly drawn hands, poorly drawn face, duplicate, twin, cloned face, double head, two heads, extra head, "
    "cropped, out of frame",
)


def _normalize_negative_prompt(value: Any) -> str:
    """Normalize user-provided negative prompt.

    Rules:
    - None / empty -> use DEFAULT_IMAGE_NEGATIVE_PROMPT
    - 'none'/'off'/'disable' -> disable negatives entirely
    - otherwise -> use provided string
    """
    if value is None:
        return DEFAULT_IMAGE_NEGATIVE_PROMPT
    s = str(value).strip()
    if not s:
        return DEFAULT_IMAGE_NEGATIVE_PROMPT
    if s.lower() in {"none", "off", "disable", "disabled", "false", "0"}:
        return ""
    return s


def _build_image_prompt(prompt: str, style: str, negative_prompt: str) -> str:
    """Build the best-effort prompt text for free APIs.

    NOTE: Pollinations.ai does NOT support negative prompts and has URL length limits.
    We keep the prompt concise to avoid 403 errors from overly long URLs.
    """
    base = (prompt or "").strip()
    if not base:
        return ""

    # Keep style hints short and effective
    style_prompts = {
        "realistic": ", photorealistic, detailed",
        "anime": ", anime style, vibrant colors",
        "artistic": ", artistic, painterly",
        "3d": ", 3d render, detailed",
        "default": ", high quality, detailed",
    }
    style_suffix = style_prompts.get(style, style_prompts["default"])

    # Short quality hints that actually help
    full = base + style_suffix

    # NOTE: Negative prompts are NOT appended to URL - Pollinations ignores them
    # and long URLs cause 403 Forbidden errors
    return full

MEDIA_ROOT = Path(__file__).resolve().parent.parent / "media_outputs"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

# --- Optional heavy dependencies (lazy loaded) ---
Image = None
ImageDraw = None
ImageFont = None
ImageFilter = None
ImageEnhance = None
ImageOps = None
ImageChops = None
IMAGE_LIBS_AVAILABLE = False

np = None
ImageClip = None
ImageSequenceClip = None
AudioFileClip = None
CompositeAudioClip = None
concatenate_audioclips = None
vfx_resize = None
VIDEO_LIBS_AVAILABLE = False

AudioSegment = None
AUDIO_LIBS_AVAILABLE = False

# Fix for Pillow 10+ compatibility (ANTIALIAS was removed)
try:
    from PIL import Image as _PILImage
    if not hasattr(_PILImage, 'ANTIALIAS'):
        _PILImage.ANTIALIAS = _PILImage.Resampling.LANCZOS
except ImportError:
    pass


def _lazy_import_image_libs() -> None:
    """Load Pillow only when first needed."""
    global Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps, ImageChops, IMAGE_LIBS_AVAILABLE
    if IMAGE_LIBS_AVAILABLE:
        return
    try:
        from PIL import (
            Image as _Image,
            ImageDraw as _ID,
            ImageFont as _IFont,
            ImageFilter as _IF,
            ImageEnhance as _IE,
            ImageOps as _IO,
            ImageChops as _IChops,
        )
        # Pillow 10+ compatibility fix
        if not hasattr(_Image, 'ANTIALIAS'):
            _Image.ANTIALIAS = _Image.Resampling.LANCZOS
        Image = _Image
        ImageDraw = _ID
        ImageFont = _IFont
        ImageFilter = _IF
        ImageEnhance = _IE
        ImageOps = _IO
        ImageChops = _IChops
        IMAGE_LIBS_AVAILABLE = True
    except ImportError:
        IMAGE_LIBS_AVAILABLE = False


def _lazy_import_video_libs() -> None:
    """Load numpy/moviepy on demand."""
    global np, ImageClip, ImageSequenceClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips, vfx_resize, VIDEO_LIBS_AVAILABLE
    if VIDEO_LIBS_AVAILABLE:
        return
    try:
        import numpy as _np
        from moviepy.editor import (
            ImageClip as _ImageClip, 
            ImageSequenceClip as _ImageSequenceClip,
            AudioFileClip as _AudioFileClip,
            CompositeAudioClip as _CompositeAudioClip,
            concatenate_audioclips as _concat_audio
        )
        from moviepy.video.fx.all import resize as _vfx_resize

        np = _np
        ImageClip = _ImageClip
        ImageSequenceClip = _ImageSequenceClip
        AudioFileClip = _AudioFileClip
        CompositeAudioClip = _CompositeAudioClip
        concatenate_audioclips = _concat_audio
        vfx_resize = _vfx_resize
        VIDEO_LIBS_AVAILABLE = True
    except ImportError:
        VIDEO_LIBS_AVAILABLE = False


def _lazy_import_audio_libs() -> None:
    """Load pydub for audio manipulation."""
    global AudioSegment, AUDIO_LIBS_AVAILABLE
    if AUDIO_LIBS_AVAILABLE:
        return
    try:
        from pydub import AudioSegment as _AS
        AudioSegment = _AS
        AUDIO_LIBS_AVAILABLE = True
    except ImportError:
        AUDIO_LIBS_AVAILABLE = False


class MediaTools:
    """High-level helpers for AI-generated images, videos, and audio using FREE APIs."""

    def __init__(self):
        self.image_output_dir = MEDIA_ROOT / "images"
        self.video_output_dir = MEDIA_ROOT / "videos"
        self.audio_output_dir = MEDIA_ROOT / "audio"
        self.image_output_dir.mkdir(parents=True, exist_ok=True)
        self.video_output_dir.mkdir(parents=True, exist_ok=True)
        self.audio_output_dir.mkdir(parents=True, exist_ok=True)
        self.llm_func = None

    def set_llm_func(self, llm_func):
        """Set the LLM function for vision analysis or other AI tasks."""
        self.llm_func = llm_func
        logger.info("Media Tools connected to LLM function")

    # ------------------------------------------------------------------
    # High-quality image upscaling helper
    # ------------------------------------------------------------------
    def _upscale_image_hq(self, img: "Image.Image", target_w: int, target_h: int) -> "Image.Image":
        """
        High-quality image upscaling using LANCZOS + UnsharpMask.
        This produces sharper, cleaner results than basic upscaling.
        """
        _lazy_import_image_libs()
        if not IMAGE_LIBS_AVAILABLE:
            return img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        orig_w, orig_h = img.size
        
        # If downscaling or same size, just use LANCZOS directly
        if target_w <= orig_w and target_h <= orig_h:
            return img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        # Step 1: LANCZOS upscale (best general-purpose upscaling)
        upscaled = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        # Step 2: Apply UnsharpMask to recover edges lost during upscaling
        # UnsharpMask is the industry-standard technique for sharpening after resize
        # Parameters: radius=2 (blur radius), percent=120 (strength), threshold=2 (edge threshold)
        scale_factor = max(target_w / orig_w, target_h / orig_h)
        
        # Adjust sharpening based on scale factor (more scaling = more sharpening needed)
        if scale_factor > 2.0:
            # Heavy upscaling - use stronger sharpening
            sharpened = upscaled.filter(ImageFilter.UnsharpMask(radius=2, percent=180, threshold=2))
        elif scale_factor > 1.5:
            # Moderate upscaling
            sharpened = upscaled.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=2))
        else:
            # Light upscaling
            sharpened = upscaled.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=2))
        
        # Step 3: Slight contrast boost to improve perceived sharpness
        result = ImageEnhance.Contrast(sharpened).enhance(1.02)
        
        return result

    # ------------------------------------------------------------------
    # FREE Image Generation APIs
    # ------------------------------------------------------------------
    def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        num_images: int = 1,
        output_dir: Optional[str] = None,
        style: str = "default",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate images from text using FREE APIs.
        Tries multiple free services in order:
        1. Local ComfyUI (prompt-faithful, requires local ComfyUI + workflow)
        2. Pollinations.ai (free, no API key)
        3. Craiyon (free, no API key)

        IMPORTANT: By default we do NOT fall back to unrelated stock-photo endpoints.
        Returning a random photo is worse than failing when the user expects prompt adherence.
        """
        if not prompt:
            return {"success": False, "error": "Prompt is required"}
        
        output_path = Path(output_dir) if output_dir else self.image_output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        negative_prompt = _normalize_negative_prompt(kwargs.get("negative_prompt"))

        allow_unrelated_fallback = bool(kwargs.get("allow_unrelated_fallback", False))
        debug = bool(kwargs.get("debug", False))

        saved_images = []
        errors = []

        # Optional: local ComfyUI workflow (prompt-faithful) if configured.
        comfy_workflow = (
            os.environ.get("COMFYUI_IMAGE_WORKFLOW")
            or os.environ.get("MEDIA_COMFYUI_IMAGE_WORKFLOW")
            or ""
        ).strip()
        
        for idx in range(max(1, num_images)):
            # 0) Try local ComfyUI workflow (best prompt adherence, if available)
            if comfy_workflow:
                result = self._generate_with_comfyui_workflow(
                    workflow_path=comfy_workflow,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    output_path=output_path,
                    idx=idx,
                )
                if result.get("success"):
                    saved_images.append(result["path"])
                    continue
                errors.append(f"ComfyUI: {result.get('error', 'Unknown')}")

            # Try Pollinations.ai first (completely free, but has rate limits)
            result = self._generate_with_pollinations(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                output_path=output_path,
                idx=idx,
                style=style,
            )
            if result.get("success"):
                saved_images.append(result["path"])
                continue
            errors.append(f"Pollinations: {result.get('error', 'Unknown')}")
            
            # Try Craiyon/DALL-E Mini API
            result = self._generate_with_craiyon(
                prompt=prompt,
                negative_prompt=negative_prompt,
                output_path=output_path,
                idx=idx,
            )
            if result.get("success"):
                saved_images.append(result["path"])
                continue
            errors.append(f"Craiyon: {result.get('error', 'Unknown')}")

            # Optional last resort: unrelated image fallback (disabled by default)
            if allow_unrelated_fallback:
                result = self._generate_with_picsum(
                    prompt=prompt,
                    width=width,
                    height=height,
                    output_path=output_path,
                    idx=idx,
                )
                if result.get("success"):
                    saved_images.append(result["path"])
                    # Mark that we used an unrelated fallback.
                    continue
                errors.append(f"Picsum: {result.get('error', 'Unknown')}")
        
        if saved_images:
            return {
                "success": True,
                "images": saved_images,
                "count": len(saved_images),
                "resolution": f"{width}x{height}",
                "method": "image_generation",
                "provider_errors": errors if debug else [],
                "allow_unrelated_fallback": allow_unrelated_fallback,
            }
        
        return {
            "success": False,
            "error": (
                "Prompt-faithful image generation failed. "
                "Pollinations/Craiyon may be blocked from your network. "
                "If you want reliable prompt-following locally, start ComfyUI and set COMFYUI_IMAGE_WORKFLOW."
            ),
            "provider_errors": errors,
            "allow_unrelated_fallback": allow_unrelated_fallback,
        }

    def _generate_with_comfyui_workflow(
        self,
        workflow_path: str,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        output_path: Path,
        idx: int = 0,
    ) -> Dict[str, Any]:
        """Generate an image via a local ComfyUI workflow.

        This is workflow-driven to avoid hardcoding node graphs. Provide a workflow JSON exported
        from ComfyUI and include placeholders like {{PROMPT}}, {{NEG_PROMPT}}, {{WIDTH}}, {{HEIGHT}}, etc.

        Configure:
          - COMFYUI_URL (optional; defaults to http://127.0.0.1:8188)
          - COMFYUI_IMAGE_WORKFLOW / MEDIA_COMFYUI_IMAGE_WORKFLOW (path to workflow JSON)
        """
        import json as _json
        import requests as req_lib
        import uuid

        def _deep_replace(obj, mapping):
            if isinstance(obj, dict):
                return {k: _deep_replace(v, mapping) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_deep_replace(v, mapping) for v in obj]
            if isinstance(obj, str):
                s = obj
                for key, val in mapping.items():
                    token = "{{" + key + "}}"
                    # If the entire field is a token, preserve numeric types (int/float)
                    # instead of forcing everything to a string.
                    if s == token:
                        return val
                    if token in s:
                        s = s.replace(token, str(val))
                return s
            return obj

        def _resolve_workflow_file(path_value: str) -> Tuple[Optional[Path], List[str]]:
            """Resolve a workflow JSON path in a user-friendly way.

            Users often provide:
              - absolute paths
              - repo-relative paths like `backend/workflows/foo.json`
              - backend-CWD-relative paths
            """
            tried: List[str] = []
            raw = (path_value or "").strip()
            if not raw:
                return None, tried

            p = Path(raw)
            if p.is_absolute():
                tried.append(str(p))
                return (p if p.exists() else None), tried

            project_root = Path(__file__).resolve().parents[2]
            candidates = [Path.cwd() / p, project_root / p]
            for c in candidates:
                tried.append(str(c))
                if c.exists():
                    return c, tried
            return None, tried

        def _pick_first_image_from_history(history: dict):
            try:
                inner = None
                if isinstance(history, dict) and len(history) == 1:
                    inner = next(iter(history.values()))
                else:
                    inner = history
                outputs = inner.get("outputs", {}) if isinstance(inner, dict) else {}
                for _node_id, node_out in outputs.items():
                    if not isinstance(node_out, dict):
                        continue
                    images = node_out.get("images")
                    if isinstance(images, list) and images:
                        i0 = images[0]
                        filename = i0.get("filename")
                        subfolder = i0.get("subfolder", "")
                        itype = i0.get("type", "output")
                        if filename:
                            return str(filename), str(subfolder or ""), str(itype or "output")
            except Exception:
                return None
            return None

        try:
            workflow_path = (workflow_path or "").strip()
            if not workflow_path:
                return {"success": False, "error": "COMFYUI_IMAGE_WORKFLOW not set"}

            wf_file, tried_paths = _resolve_workflow_file(workflow_path)
            if not wf_file:
                extra = f" (tried: {', '.join(tried_paths)})" if tried_paths else ""
                return {"success": False, "error": f"Workflow not found: {workflow_path}{extra}"}

            base_url = (os.environ.get("COMFYUI_URL") or "http://127.0.0.1:8188").rstrip("/")

            # Quick health check
            try:
                hc = req_lib.get(base_url + "/system_stats", timeout=6)
                if hc.status_code >= 500:
                    return {"success": False, "error": f"ComfyUI not healthy (http {hc.status_code})"}
            except Exception as exc:
                return {"success": False, "error": f"ComfyUI not reachable at {base_url}: {exc}"}

            wf = _json.loads(wf_file.read_text(encoding="utf-8"))
            mapping = {
                "PROMPT": (prompt or "").strip(),
                "NEG_PROMPT": (negative_prompt or "").strip(),
                "WIDTH": int(min(max(256, width), 2048)),
                "HEIGHT": int(min(max(256, height), 2048)),
                # Provide defaults commonly used by workflows.
                "SEED": int(time.time()) % 1000000,
                "STEPS": 20,
                "CFG": 6.0,
                "SAMPLER": "euler",
                "SCHEDULER": "normal",
                "MODEL": (
                    os.environ.get("COMFYUI_DEFAULT_CHECKPOINT")
                    or os.environ.get("MEDIA_COMFYUI_DEFAULT_CHECKPOINT")
                    or "v1-5-pruned-emaonly.safetensors"
                ),
            }
            wf2 = _deep_replace(wf, mapping)

            payload = {"prompt": wf2, "client_id": str(uuid.uuid4())}
            r = req_lib.post(base_url + "/prompt", json=payload, timeout=30)
            r.raise_for_status()
            pid = (r.json() or {}).get("prompt_id")
            if not pid:
                return {"success": False, "error": f"ComfyUI did not return prompt_id: {r.text[:300]}"}

            # Poll history
            deadline = time.time() + 60 * 20
            history = None
            while time.time() < deadline:
                hr = req_lib.get(base_url + f"/history/{pid}", timeout=15)
                if hr.status_code == 200:
                    data = hr.json()
                    inner = data.get(pid) if isinstance(data, dict) and pid in data else data
                    if isinstance(inner, dict) and inner.get("outputs"):
                        history = inner
                        break
                time.sleep(1.5)

            if history is None:
                return {"success": False, "error": "Timed out waiting for ComfyUI output"}

            pick = _pick_first_image_from_history(history)
            if not pick:
                return {"success": False, "error": "ComfyUI completed but no image output found"}

            filename, subfolder, itype = pick
            params = {"filename": filename, "type": itype}
            if subfolder:
                params["subfolder"] = subfolder

            img_r = req_lib.get(base_url + "/view", params=params, timeout=120)
            img_r.raise_for_status()
            content = img_r.content
            if not content or len(content) < 1000:
                return {"success": False, "error": "ComfyUI returned empty image"}

            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            out_file = output_path / f"comfyui_img_{timestamp}_{idx+1}.png"
            with open(out_file, "wb") as fh:
                fh.write(content)
            return {"success": True, "path": str(out_file), "method": "comfyui"}
        except Exception as exc:
            return {"success": False, "error": str(exc)[:800]}
    
    def _generate_with_picsum(
        self,
        prompt: str,
        width: int,
        height: int,
        output_path: Path,
        idx: int = 0,
    ) -> Dict[str, Any]:
        """Use multiple stock photo APIs for images matching the prompt."""
        import requests as req_lib
        import random
        
        # Clamp to reasonable sizes
        width = min(max(256, width), 2048)
        height = min(max(256, height), 2048)
        
        try:
            # Extract key terms from prompt for better search
            prompt_lower = prompt.lower()
            search_terms = []
            
            # Comprehensive keyword mapping for better prompt matching
            keyword_map = {
                'sunset': ['sunset', 'dusk', 'evening sky', 'golden hour'],
                'mountain': ['mountain', 'mountains', 'landscape', 'peaks', 'alps'],
                'ocean': ['ocean', 'sea', 'beach', 'waves', 'coast'],
                'forest': ['forest', 'woods', 'trees', 'nature', 'woods'],
                'city': ['city', 'urban', 'buildings', 'skyscrapers', 'metropolitan'],
                'dog': ['dog', 'puppy', 'pet dog', 'canine', 'animal'],
                'cat': ['cat', 'kitten', 'pet cat', 'feline', 'animal'],
                'flower': ['flower', 'flowers', 'garden', 'bloom', 'petals'],
                'sky': ['sky', 'clouds', 'atmosphere', 'heavens', 'blue sky'],
                'river': ['river', 'stream', 'water', 'flowing water', 'creek'],
                'lake': ['lake', 'pond', 'water', 'reflection', 'serene'],
                'snow': ['snow', 'winter', 'ice', 'frozen', 'white'],
                'desert': ['desert', 'sand', 'dunes', 'arid', 'sahara'],
                'beach': ['beach', 'coast', 'shore', 'sand', 'tropical'],
                'animal': ['animal', 'wildlife', 'creature', 'mammal'],
                'bird': ['bird', 'avian', 'flying', 'wings'],
                'car': ['car', 'vehicle', 'automobile', 'transport', 'auto'],
                'house': ['house', 'home', 'building', 'architecture', 'residence'],
                'food': ['food', 'meal', 'cuisine', 'delicious', 'gourmet'],
                'portrait': ['portrait', 'face', 'person', 'human', 'people'],
                'space': ['space', 'stars', 'galaxy', 'universe', 'cosmos'],
                'art': ['art', 'painting', 'creative', 'design', 'abstract'],
                'technology': ['technology', 'computer', 'digital', 'tech', 'electronic'],
                'nature': ['nature', 'outdoor', 'scenic', 'beautiful', 'natural'],
                'happy': ['happy', 'joy', 'smile', 'positive', 'cheerful'],
                'dark': ['dark', 'night', 'shadow', 'mysterious', 'moody'],
                'bright': ['bright', 'light', 'sunny', 'vibrant', 'luminous'],
                'colorful': ['colorful', 'vibrant', 'rainbow', 'bright', 'vivid'],
                'black and white': ['black and white', 'monochrome', 'grayscale', 'bw'],
            }
            
            # Find matching keywords
            for keyword, terms in keyword_map.items():
                if keyword in prompt_lower:
                    search_terms.extend(terms)
            
            # Extract additional descriptive words
            words = prompt_lower.split()
            adjectives = ['beautiful', 'amazing', 'stunning', 'gorgeous', 'majestic', 'serene', 'peaceful', 'dramatic', 'vibrant', 'colorful', 'bright', 'dark', 'mysterious', 'magical']
            for word in words:
                if word in adjectives and word not in search_terms:
                    search_terms.append(word)
            
            # If no specific matches, try to extract nouns
            if not search_terms:
                common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'an', 'a', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'shall'}
                search_terms = [word for word in words if len(word) > 3 and word not in common_words]
            
            # Fallback
            if not search_terms:
                search_terms = ['nature', 'landscape', 'photography', 'scenic']
            
            # Try multiple services in order
            services = [
                ('pexels', lambda term: f"https://api.pexels.com/v1/search?query={term}&per_page=1&page=1&size=large"),
                ('unsplash', lambda term: f"https://source.unsplash.com/featured/{width}x{height}/?{term}"),
                ('picsum', lambda term: f"https://picsum.photos/seed/{hash(term)%1000000}/{width}/{height}"),
            ]
            
            for service_name, url_func in services:
                try:
                    # Choose 1-2 search terms
                    selected_terms = random.sample(search_terms, min(2, len(search_terms)))
                    search_query = '+'.join(selected_terms) if service_name == 'pexels' else ','.join(selected_terms)
                    
                    if service_name == 'pexels':
                        url = url_func(search_query)
                        response = req_lib.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
                        if response.status_code == 200:
                            data = response.json()
                            if data.get('photos') and len(data['photos']) > 0:
                                image_url = data['photos'][0]['src']['large']
                                img_response = req_lib.get(image_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
                                if img_response.status_code == 200 and len(img_response.content) > 5000:
                                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                                    filename = output_path / f"{service_name}_img_{timestamp}_{idx+1}.jpg"
                                    with open(filename, 'wb') as f:
                                        f.write(img_response.content)
                                    logger.info(f"{service_name.title()} image saved: {filename}")
                                    return {"success": True, "path": str(filename), "method": service_name}
                    else:
                        # Unsplash or Picsum
                        url = url_func(search_query)
                        response = req_lib.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30, allow_redirects=True)
                        if response.status_code == 200 and len(response.content) > 5000:
                            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                            filename = output_path / f"{service_name}_img_{timestamp}_{idx+1}.jpg"
                            with open(filename, 'wb') as f:
                                f.write(response.content)
                            logger.info(f"{service_name.title()} image saved: {filename}")
                            return {"success": True, "path": str(filename), "method": service_name}
                            
                except Exception as e:
                    logger.warning(f"{service_name.title()} failed: {e}")
                    continue
            
            return {"success": False, "error": "All image services failed"}
                
        except Exception as e:
            logger.warning(f"Image generation error: {e}")
            return {"success": False, "error": str(e)}

    def _generate_with_pollinations(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        output_path: Path,
        idx: int = 0,
        style: str = "default"
    ) -> Dict[str, Any]:
        """Use Pollinations.ai - completely FREE, no API key needed."""
        import requests as req_lib
        
        # Clamp dimensions to Pollinations limits (max 2048x2048)
        width = min(max(256, width), 2048)
        height = min(max(256, height), 2048)
        
        # Retry logic for transient failures
        max_retries = 3
        last_error = None
        
        # Use simple prompt - don't add style suffixes as Pollinations doesn't need them.
        # IMPORTANT: Pollinations uses the prompt in the URL path; overly long prompts
        # can produce 403 errors due to CDN/WAF limits. We never reject user input;
        # we truncate *only for the Pollinations request*.
        simple_prompt = (prompt or "").strip()
        if not simple_prompt:
            return {"success": False, "error": "Empty prompt"}

        def _truncate_for_pollinations(raw: str, *, max_encoded_len: int = 1400) -> tuple[str, bool]:
            """Return (prompt, truncated) such that quote(prompt) length <= max_encoded_len."""
            raw = (raw or "").strip()
            encoded = urllib.parse.quote(raw, safe='')
            if len(encoded) <= max_encoded_len:
                return raw, False

            # Binary-search the longest prefix that fits once URL-encoded.
            lo, hi = 0, len(raw)
            best = 0
            while lo <= hi:
                mid = (lo + hi) // 2
                enc = urllib.parse.quote(raw[:mid], safe='')
                if len(enc) <= max_encoded_len:
                    best = mid
                    lo = mid + 1
                else:
                    hi = mid - 1

            truncated = raw[:best].rstrip()
            # Prefer cutting on a word boundary if possible.
            if " " in truncated:
                truncated = truncated.rsplit(" ", 1)[0].rstrip()
            return truncated, True

        safe_prompt, was_truncated = _truncate_for_pollinations(simple_prompt)
        if was_truncated:
            logger.info(
                "Pollinations prompt truncated for URL safety (original_chars=%s, used_chars=%s)",
                len(simple_prompt),
                len(safe_prompt),
            )
        
        for attempt in range(max_retries):
            try:
                # Small delay before each attempt to avoid rate limiting
                # Pollinations needs time between requests
                if attempt > 0:
                    delay = 20 * attempt  # 20s, 40s between retries
                    logger.info(f"Rate limit backoff: waiting {delay}s before attempt {attempt+1}")
                    time.sleep(delay)
                else:
                    # Small initial delay to let CDN warm up
                    time.sleep(2)
                
                # Use the prompt directly - Pollinations handles the AI generation
                encoded_prompt = urllib.parse.quote(safe_prompt, safe='')
                
                # Build URL without seed - seed parameter causes 403 rate limiting
                # The CDN will cache identical prompts, but that's okay for image generation
                url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
                
                # Download the image
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                filename = output_path / f"ai_img_{timestamp}_{idx+1}.jpg"
                
                logger.info(f"Pollinations attempt {attempt+1}/{max_retries}: generating image...")
                
                # Use requests library with browser-like headers
                response = req_lib.get(
                    url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                    },
                    timeout=180,  # Longer timeout as generation can take time
                )
                
                # Check for rate limiting
                if response.status_code == 403:
                    last_error = f"Rate limited (attempt {attempt+1}/{max_retries}): waiting longer..."
                    logger.warning(last_error)
                    continue  # The delay at start of next iteration will handle backoff
                
                response.raise_for_status()
                
                # Get image data
                image_data = response.content
                
                if not image_data or len(image_data) < 1000:
                    last_error = f"Empty or too small response ({len(image_data) if image_data else 0} bytes)"
                    logger.warning(f"Attempt {attempt+1}: {last_error}")
                    continue
                
                # Determine file extension from content type or magic bytes
                content_type = response.headers.get('Content-Type', '')
                if 'png' in content_type or image_data[:4] == b'\x89PNG':
                    filename = filename.with_suffix('.png')
                elif 'jpeg' in content_type or 'jpg' in content_type or image_data[:2] == b'\xff\xd8':
                    filename = filename.with_suffix('.jpg')
                
                with open(filename, 'wb') as f:
                    f.write(image_data)
                
                file_size = os.path.getsize(filename)
                logger.info(f"Pollinations image generated: {filename} ({file_size} bytes)")
                result = {"success": True, "path": str(filename)}
                if was_truncated:
                    result["note"] = "Prompt was truncated for Pollinations URL length limits; try a shorter prompt for more precise results."
                return result
            
            except req_lib.exceptions.Timeout:
                last_error = f"Timeout (attempt {attempt+1}/{max_retries}): Request took too long"
                logger.warning(last_error)
                continue
                
            except req_lib.exceptions.HTTPError as e:
                status = e.response.status_code if e.response else 'unknown'
                if status in (403, 429, 503):
                    last_error = f"Rate limited/unavailable (attempt {attempt+1}/{max_retries}): HTTP {status}"
                    logger.warning(last_error)
                    continue
                else:
                    last_error = f"HTTP {status}: {str(e)}"
                    logger.error(f"Pollinations HTTP error: {last_error}")
                    continue
                
            except req_lib.exceptions.ConnectionError as e:
                last_error = f"Connection error (attempt {attempt+1}/{max_retries}): {str(e)}"
                logger.warning(last_error)
                continue
                
            except Exception as e:
                last_error = f"Unexpected error: {type(e).__name__}: {str(e)}"
                logger.error(f"Pollinations error: {last_error}")
                continue
        
        return {"success": False, "error": last_error or "Unknown error after all retries"}

    def edit_image_kontext(
        self,
        prompt: str,
        image_url: str,
        width: int = 1024,
        height: int = 1024,
        output_dir: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        safe: bool = False,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Image-to-image editing via Pollinations 'kontext'.

        Pollinations API docs:
          GET https://image.pollinations.ai/prompt/{prompt}?model=kontext&image=<URL>

        NOTE: The input image must be reachable by Pollinations (public URL).
        """
        base_prompt = (prompt or "").strip()
        src = (image_url or "").strip()
        if not base_prompt:
            return {"success": False, "error": "Prompt is required"}
        if not src:
            return {"success": False, "error": "image_url is required"}

        output_path = Path(output_dir) if output_dir else self.image_output_dir
        output_path.mkdir(parents=True, exist_ok=True)

        neg = _normalize_negative_prompt(negative_prompt)

        # Best-effort: when the provider doesn't support a separate negative prompt
        # parameter reliably, bake it into the prompt text.
        full_prompt = _build_image_prompt(base_prompt, style="default", negative_prompt=neg)

        def _try_model(model_name: str) -> Dict[str, Any]:
            encoded_prompt = urllib.parse.quote(full_prompt)

            params: Dict[str, Any] = {
                "model": model_name,
                "image": src,
                "width": int(width or 1024),
                "height": int(height or 1024),
                "nologo": "true",
            }

            if safe:
                params["safe"] = "true"

            if seed is not None:
                try:
                    params["seed"] = int(seed)
                except Exception:
                    # Ignore bad seed values.
                    pass

            qs = urllib.parse.urlencode(params, doseq=True)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?{qs}"

            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = output_path / f"{model_name}_{timestamp}.png"
            counter = 1
            while filename.exists():
                filename = output_path / f"{model_name}_{timestamp}_{counter}.png"
                counter += 1

            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
            )

            # Image-to-image models can take longer than text-to-image.
            with urllib.request.urlopen(req, timeout=300) as response:
                image_data = response.read()

            with open(filename, 'wb') as f:
                f.write(image_data)

            if os.path.getsize(filename) < 1000:
                os.remove(filename)
                return {"success": False, "error": "Generated image too small (API error)"}

            return {"success": True, "path": str(filename), "source_image_url": src, "model": model_name}

        # Try kontext first; if it fails (often 500 for anonymous access), fall back to
        # a normal image model while still providing the source image as a reference.
        try:
            return _try_model("kontext")
        except urllib.error.HTTPError as e:
            # Fallback path: keep a useful result even if kontext is temporarily down.
            if getattr(e, "code", None) in {500, 503}:
                try:
                    result = _try_model("flux")
                    if result.get("success"):
                        result["note"] = "Kontext model failed upstream; used model=flux as fallback (may be less faithful to source)."
                    return result
                except Exception:
                    logger.debug("Kontext fallback to flux failed", exc_info=True)
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_with_craiyon(
        self,
        prompt: str,
        negative_prompt: str,
        output_path: Path,
        idx: int = 0
    ) -> Dict[str, Any]:
        """Use Craiyon (DALL-E Mini) - FREE but slower."""
        import requests as req_lib
        
        try:
            url = "https://api.craiyon.com/v3"

            # Craiyon doesn't expose a separate negative prompt field; best-effort only.
            full_prompt = prompt
            neg = (negative_prompt or "").strip()
            if neg:
                full_prompt = f"{prompt}\n\nAvoid: {neg}"

            payload = {
                "prompt": full_prompt,
                "version": "c4ue22fb7kb6wlac",
                "token": None
            }
            
            response = req_lib.post(
                url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                timeout=120
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'images' in result and result['images']:
                # Decode base64 image
                img_data = base64.b64decode(result['images'][0])
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                filename = output_path / f"craiyon_{timestamp}_{idx+1}.webp"
                
                with open(filename, 'wb') as f:
                    f.write(img_data)
                
                # Convert to PNG if Pillow available
                _lazy_import_image_libs()
                if IMAGE_LIBS_AVAILABLE:
                    img = Image.open(filename)
                    png_path = filename.with_suffix('.png')
                    img.save(png_path, 'PNG')
                    os.remove(filename)
                    return {"success": True, "path": str(png_path)}
                
                return {"success": True, "path": str(filename)}
            
            return {"success": False, "error": "No images in response"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_placeholder_image(
        self,
        prompt: str,
        width: int,
        height: int,
        output_path: Path
    ) -> Dict[str, Any]:
        """Create a stylized placeholder when APIs fail."""
        _lazy_import_image_libs()
        if not IMAGE_LIBS_AVAILABLE:
            return {"success": False, "error": "Pillow not installed. Run: pip install pillow"}

        try:
            # Create gradient background
            bg_colors = [
                ((31, 41, 55), (75, 85, 99)),
                ((30, 64, 175), (59, 130, 246)),
                ((6, 95, 70), (16, 185, 129)),
                ((120, 53, 15), (245, 158, 11)),
                ((76, 29, 149), (139, 92, 246)),
            ]
            color1, color2 = random.choice(bg_colors)

            image = Image.new("RGB", (width, height), color1)
            draw = ImageDraw.Draw(image)

            # Create gradient effect
            for y in range(height):
                r = int(color1[0] + (color2[0] - color1[0]) * y / height)
                g = int(color1[1] + (color2[1] - color1[1]) * y / height)
                b = int(color1[2] + (color2[2] - color1[2]) * y / height)
                draw.line([(0, y), (width, y)], fill=(r, g, b))

            # Add decorative shapes
            for _ in range(5):
                radius = random.randint(50, min(width, height) // 2)
                x = random.randint(0, width)
                y = random.randint(0, height)
                alpha = random.randint(20, 50)
                shade = tuple(min(255, c + alpha) for c in color2)
                draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=shade)

            # Add prompt text
            text = prompt[:100] + "..." if len(prompt) > 100 else prompt
            wrapped = "\n".join(textwrap.wrap(text, width=35))
            
            try:
                font = ImageFont.truetype("arial.ttf", size=max(24, width // 25))
            except:
                font = ImageFont.load_default()

            text_box = draw.multiline_textbbox((0, 0), wrapped, font=font)
            text_width = text_box[2] - text_box[0]
            text_height = text_box[3] - text_box[1]
            text_x = (width - text_width) / 2
            text_y = (height - text_height) / 2

            # Draw shadow
            draw.multiline_text((text_x + 2, text_y + 2), wrapped, fill=(0, 0, 0), font=font, align="center")
            # Draw text
            draw.multiline_text((text_x, text_y), wrapped, fill=(255, 255, 255), font=font, align="center")

            # Add "AI Generated" watermark
            draw.text((10, height - 30), "🎨 AI Placeholder", fill=(255, 255, 255, 128), font=font)

            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = output_path / f"placeholder_{timestamp}.png"
            image.save(filename)
            
            return {"success": True, "path": str(filename), "placeholder": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # FREE Video Generation
    # ------------------------------------------------------------------
    def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        fps: int = 24,
        resolution: str = "1080x1080",
        output_path: Optional[str] = None,
        style: str = "default"
    ) -> Dict[str, Any]:
        """
        [DISABLED] Generate a video from text prompt.
        Disabled per user request due to limited network speed.
        """
        return {
            "success": False, 
            "error": "Video generation is currently disabled globally to save bandwidth (limited network speed)."
        }

    def generate_video_from_image(
        self,
        image_path: str,
        motion_prompt: str = "",
        duration: int = 4,
        output_path: Optional[str] = None,
        motion_type: str = "auto",  # auto, walk, run, talk, dance, wave, etc.
    ) -> Dict[str, Any]:
        """
        [DISABLED] Generate a video with REAL MOTION from a still image.
        Disabled per user request due to limited network speed.
        """
        return {
            "success": False, 
            "error": "Real-motion video generation is currently disabled globally to save bandwidth."
        }

    def create_video_from_prompt(
        self,
        prompt: str,
        frames: int = 8,
        fps: int = 24,
        resolution: str = "1080x1080",
        output_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Alias for generate_video with frame control."""
        return self.generate_video(
            prompt=prompt,
            duration=frames,
            fps=fps,
            resolution=resolution,
            output_path=output_path
        )

    # ------------------------------------------------------------------
    # Video helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_resolution(resolution: str) -> Tuple[int, int]:
        """Parse resolution string like '1080x1080' into (width, height)."""
        try:
            width_str, height_str = resolution.lower().split("x")
            return int(width_str), int(height_str)
        except Exception:
            return 1080, 1080  # Facebook friendly square

    def create_video_from_images(
        self,
        image_paths: List[str],
        output_path: Optional[str] = None,
        fps: int = 24,
        resolution: str = "1080x1080",
        duration_per_image: float = 1.0,
        transition: str = "crossfade",  # "none", "crossfade", "fade"
        transition_duration: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Concatenate images into a high-quality mp4 with optional transitions.
        
        Args:
            image_paths: List of image file paths
            output_path: Optional custom output path
            fps: Frames per second
            resolution: Output resolution (e.g., "1080x1080")
            duration_per_image: How long each image displays (seconds)
            transition: Transition type between images
            transition_duration: Duration of transition effect (seconds)
        """
        if not image_paths:
            return {"success": False, "error": "image_paths cannot be empty"}
        _lazy_import_video_libs()
        _lazy_import_image_libs()
        if not VIDEO_LIBS_AVAILABLE or not IMAGE_LIBS_AVAILABLE:
            return {
                "success": False,
                "error": "Video libraries missing. Install: pip install moviepy numpy pillow",
            }

        width, height = self._parse_resolution(resolution)
        
        try:
            from moviepy.editor import concatenate_videoclips, CompositeVideoClip
            
            clips = []
            print(f"[MediaTools] Processing {len(image_paths)} images...")
            
            for idx, path in enumerate(image_paths):
                if not os.path.exists(path):
                    print(f"[MediaTools] Warning: Image not found, skipping: {path}")
                    continue
                    
                # Load and resize with HIGH QUALITY
                img = Image.open(path).convert("RGB")
                orig_w, orig_h = img.size
                
                # Calculate aspect-aware resize to fill frame
                img_aspect = orig_w / orig_h
                target_aspect = width / height
                
                if img_aspect > target_aspect:
                    # Image is wider - fit height, crop width
                    new_h = height
                    new_w = int(height * img_aspect)
                else:
                    # Image is taller - fit width, crop height
                    new_w = width
                    new_h = int(width / img_aspect)
                
                # Use high-quality upscaling method
                img = self._upscale_image_hq(img, new_w, new_h)
                
                # Center crop to exact dimensions
                left = (new_w - width) // 2
                top = (new_h - height) // 2
                img = img.crop((left, top, left + width, top + height))
                
                img_array = np.array(img)
                clip = ImageClip(img_array).set_duration(duration_per_image)
                clips.append(clip)
                
                print(f"[MediaTools] Processed image {idx + 1}/{len(image_paths)}")
            
            if not clips:
                return {"success": False, "error": "No valid images found"}
            
            # Apply transitions
            if transition == "crossfade" and len(clips) > 1 and transition_duration > 0:
                # Create crossfade effect
                processed_clips = []
                for i, clip in enumerate(clips):
                    if i == 0:
                        processed_clips.append(clip.crossfadeout(transition_duration))
                    elif i == len(clips) - 1:
                        processed_clips.append(clip.crossfadein(transition_duration))
                    else:
                        processed_clips.append(clip.crossfadein(transition_duration).crossfadeout(transition_duration))
                
                # Concatenate with overlap
                final_clip = concatenate_videoclips(processed_clips, method="compose", padding=-transition_duration)
            elif transition == "fade" and len(clips) > 1:
                # Fade to black between clips
                processed_clips = []
                for clip in clips:
                    processed_clips.append(clip.fadein(transition_duration).fadeout(transition_duration))
                final_clip = concatenate_videoclips(processed_clips, method="compose")
            else:
                # No transition
                final_clip = concatenate_videoclips(clips, method="compose")
            
            output_file = (
                Path(output_path)
                if output_path
                else self.video_output_dir / f"video_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
            )
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            print(f"[MediaTools] Encoding video...")
            
            final_clip.write_videofile(
                str(output_file),
                fps=fps,
                codec="libx264",
                audio=False,
                preset="slow",  # Better quality encoding
                bitrate="6000k",  # Good bitrate for quality
                threads=4,
                ffmpeg_params=["-crf", "20"],  # High quality
                logger=None
            )
            final_clip.close()
            for clip in clips:
                clip.close()
                
            total_duration = duration_per_image * len(clips)
            if transition == "crossfade" and len(clips) > 1:
                total_duration -= transition_duration * (len(clips) - 1)
                
            return {
                "success": True,
                "video_path": str(output_file),
                "frame_count": len(clips),
                "fps": fps,
                "resolution": f"{width}x{height}",
                "duration": total_duration,
                "transition": transition,
            }
        except Exception as exc:
            import traceback
            return {"success": False, "error": str(exc), "traceback": traceback.format_exc()}

    def animate_image(
        self,
        image_path: str,
        duration: int = 6,
        fps: int = 30,
        zoom_factor: float = 1.25,  # 25% zoom - much more visible Ken Burns effect
        resolution: str = "1080x1080",
        output_path: Optional[str] = None,
        pan_direction: str = "center",  # center, left, right, up, down
    ) -> Dict[str, Any]:
        """
        Create a high-quality Ken Burns style video from a single still image.
        Uses frame-by-frame rendering with high-quality interpolation for crisp output.
        
        Args:
            image_path: Path to source image
            duration: Video duration in seconds
            fps: Frames per second (24-60 recommended)
            zoom_factor: Total zoom amount (1.25 = 25% zoom in, 0.8 = 20% zoom out)
            resolution: Output resolution (e.g., "1080x1080", "1920x1080")
            output_path: Optional custom output path
            pan_direction: Pan direction ("center", "left", "right", "up", "down")
        """
        _lazy_import_video_libs()
        _lazy_import_image_libs()
        if not VIDEO_LIBS_AVAILABLE or not IMAGE_LIBS_AVAILABLE:
            return {
                "success": False,
                "error": "Video libraries missing. Install: pip install moviepy numpy pillow",
            }
        if not os.path.exists(image_path):
            return {"success": False, "error": f"Image not found: {image_path}"}

        width, height = self._parse_resolution(resolution)
        
        try:
            # Load and prepare the source image at HIGHER resolution for quality
            base_image = Image.open(image_path).convert("RGB")
            orig_w, orig_h = base_image.size
            
            print(f"[MediaTools] Source image: {orig_w}x{orig_h}")
            
            # Calculate working resolution - use larger canvas for zoom headroom
            # This prevents blur by starting with more pixels than needed
            max_zoom = max(zoom_factor, 1.0 / zoom_factor) if zoom_factor != 1.0 else 1.0
            work_scale = max_zoom + 0.15  # Extra 15% headroom
            work_w = int(width * work_scale)
            work_h = int(height * work_scale)
            
            # Use high-quality upscaling method
            base_image = self._upscale_image_hq(base_image, work_w, work_h)
            
            work_w, work_h = base_image.size
            print(f"[MediaTools] Working canvas: {work_w}x{work_h}")
            
            # Generate frames with smooth Ken Burns effect
            total_frames = int(duration * fps)
            frames = []
            
            print(f"[MediaTools] Generating {total_frames} high-quality frames...")
            
            for frame_idx in range(total_frames):
                t = frame_idx / total_frames  # Progress 0.0 to 1.0
                
                # Calculate current zoom level (smooth interpolation)
                if zoom_factor >= 1.0:
                    # Zooming in: start at 1.0, end at zoom_factor
                    current_zoom = 1.0 + (zoom_factor - 1.0) * t
                else:
                    # Zooming out: start at 1/zoom_factor, end at 1.0
                    current_zoom = (1.0 / zoom_factor) - ((1.0 / zoom_factor) - 1.0) * t
                
                # Calculate crop size based on zoom (smaller crop = more zoomed in)
                crop_w = int(width / current_zoom)
                crop_h = int(height / current_zoom)
                
                # Calculate pan offset based on direction
                max_offset_x = (work_w - crop_w) // 2
                max_offset_y = (work_h - crop_h) // 2
                
                # Start from center
                center_x = work_w // 2
                center_y = work_h // 2
                
                # Apply pan direction
                pan_amount = t  # How far along the pan (0 to 1)
                if pan_direction == "left":
                    offset_x = int(max_offset_x * (1 - pan_amount * 2))  # Pan from right to left
                    offset_y = 0
                elif pan_direction == "right":
                    offset_x = int(-max_offset_x * (1 - pan_amount * 2))  # Pan from left to right
                    offset_y = 0
                elif pan_direction == "up":
                    offset_x = 0
                    offset_y = int(max_offset_y * (1 - pan_amount * 2))  # Pan from bottom to top
                elif pan_direction == "down":
                    offset_x = 0
                    offset_y = int(-max_offset_y * (1 - pan_amount * 2))  # Pan from top to bottom
                else:  # center - just zoom, no pan
                    offset_x = 0
                    offset_y = 0
                
                # Calculate crop box
                left = center_x - crop_w // 2 + offset_x
                top = center_y - crop_h // 2 + offset_y
                right = left + crop_w
                bottom = top + crop_h
                
                # Clamp to valid bounds
                left = max(0, min(left, work_w - crop_w))
                top = max(0, min(top, work_h - crop_h))
                right = left + crop_w
                bottom = top + crop_h
                
                # Crop and resize to final output resolution with HIGH QUALITY
                frame = base_image.crop((left, top, right, bottom))
                
                # Only resize if the crop is not already the exact target size
                if frame.size != (width, height):
                    frame = frame.resize((width, height), Image.Resampling.LANCZOS)
                    # Apply sharpening after resize to maintain crispness
                    frame = frame.filter(ImageFilter.UnsharpMask(radius=1.5, percent=80, threshold=2))
                
                # Convert to numpy array for moviepy
                frames.append(np.array(frame))
                
                # Progress indicator
                if frame_idx % (total_frames // 4) == 0:
                    print(f"[MediaTools] Progress: {int((frame_idx / total_frames) * 100)}%")
            
            print(f"[MediaTools] Encoding video...")
            
            # Create video from frame sequence
            clip = ImageSequenceClip(frames, fps=fps)
            
            output_file = (
                Path(output_path)
                if output_path
                else self.video_output_dir / f"kenburns_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
            )
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write with high quality settings
            clip.write_videofile(
                str(output_file),
                fps=fps,
                codec="libx264",
                audio=False,
                preset="slow",  # Better quality encoding
                bitrate="8000k",  # High bitrate for quality
                threads=4,
                ffmpeg_params=["-crf", "18"],  # High quality (lower = better, 18 is visually lossless)
                logger=None
            )
            clip.close()
            
            return {
                "success": True,
                "video_path": str(output_file),
                "duration": duration,
                "fps": fps,
                "resolution": f"{width}x{height}",
                "zoom_factor": zoom_factor,
                "pan_direction": pan_direction,
                "total_frames": total_frames,
            }
        except Exception as exc:
            import traceback
            return {"success": False, "error": str(exc), "traceback": traceback.format_exc()}

    # ------------------------------------------------------------------
    # AI Video Generation (Image-to-Video with actual motion)
    # ------------------------------------------------------------------
    def generate_video_from_image(
        self,
        image_path: str,
        motion_prompt: str = "",
        duration: int = 4,
        output_path: Optional[str] = None,
        motion_type: str = "auto",  # auto, walk, run, talk, dance, wave, etc.
    ) -> Dict[str, Any]:
        """
        Generate a video with REAL MOTION from a still image using FREE AI APIs.
        This makes people walk, animals move, etc. - not just zoom/pan effects.
        
        Uses free services:
        1. Replicate (free tier) - Stable Video Diffusion
        2. Hugging Face Inference API (free) - Various video models
        3. Pollinations video (if available)
        
        Args:
            image_path: Path to the source image
            motion_prompt: Description of the motion (e.g., "person walking forward", "dog running")
            duration: Desired video duration in seconds (2-8 seconds typical)
            output_path: Optional custom output path
            motion_type: Type of motion - auto, walk, run, talk, dance, wave, breathe, etc.
        """
        if not os.path.exists(image_path):
            return {"success": False, "error": f"Image not found: {image_path}"}
        
        output_file = (
            Path(output_path)
            if output_path
            else self.video_output_dir / f"ai_video_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Build motion prompt if not provided
        if not motion_prompt:
            motion_prompts = {
                "auto": "natural subtle movement, breathing, slight motion",
                "walk": "person walking forward naturally",
                "run": "running motion, dynamic movement",
                "talk": "person talking, mouth moving, natural gestures",
                "dance": "dancing motion, rhythmic movement",
                "wave": "waving hand, greeting gesture",
                "breathe": "subtle breathing motion, natural idle movement",
                "fly": "flying motion, wings flapping",
                "swim": "swimming motion through water",
            }
            motion_prompt = motion_prompts.get(motion_type, motion_prompts["auto"])
        
        print(f"[MediaTools] Generating AI video from image with motion: {motion_prompt}")
        
        # Try multiple free APIs in order
        errors = []
        
        # Method 1: Try Pollinations.ai FREE API (NO API KEY REQUIRED!)
        result = self._generate_video_pollinations_i2v(image_path, motion_prompt, duration, str(output_file))
        if result.get("success"):
            return result
        errors.append(f"Pollinations: {result.get('error', 'Unknown error')}")
        
        # Method 2: Try Replicate Stable Video Diffusion (has free tier)
        result = self._generate_video_replicate(image_path, motion_prompt, duration, str(output_file))
        if result.get("success"):
            return result
        errors.append(f"Replicate: {result.get('error', 'Unknown error')}")
        
        # Method 3: Try Hugging Face free inference
        result = self._generate_video_huggingface(image_path, motion_prompt, duration, str(output_file))
        if result.get("success"):
            return result
        errors.append(f"HuggingFace: {result.get('error', 'Unknown error')}")
        
        # Method 3: Try Stability AI (if API key available)
        result = self._generate_video_stability(image_path, motion_prompt, duration, str(output_file))
        if result.get("success"):
            return result
        errors.append(f"Stability: {result.get('error', 'Unknown error')}")
        
        # Method 4: Fallback to enhanced Ken Burns with more dramatic motion
        print("[MediaTools] AI video APIs unavailable, using enhanced Ken Burns fallback...")
        result = self.animate_image(
            image_path=image_path,
            duration=duration,
            zoom_factor=1.35,  # More dramatic zoom
            pan_direction="right" if "walk" in motion_type.lower() else "center",
            output_path=str(output_file)
        )
        if result.get("success"):
            result["note"] = "Used enhanced Ken Burns effect (AI video APIs require API keys)"
            result["setup_instructions"] = (
                "For real AI video generation with actual motion, try:\n"
                "- Pollinations.ai (FREE, no API key required!)\n"
                "- REPLICATE_API_TOKEN (get free at replicate.com)\n"
                "- HUGGINGFACE_TOKEN (get free at huggingface.co)\n"
                "- STABILITY_API_KEY (get at stability.ai)"
            )
        return result
    
    # ------------------------------------------------------------------
    # Pollinations.ai FREE Video Generation (NO API KEY REQUIRED!)
    # ------------------------------------------------------------------
    def _generate_video_pollinations_i2v(
        self, image_path: str, motion_prompt: str, duration: int, output_path: str
    ) -> Dict[str, Any]:
        """
        Generate video from image using Pollinations.ai FREE API.
        
        This is 100% FREE with NO API key required!
        Uses Seedance model for image-to-video generation.
        """
        try:
            _lazy_import_image_libs()
            
            # Read and encode image as base64 data URI
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Detect mime type
            img = Image.open(image_path)
            fmt = img.format.lower() if img.format else "png"
            mime_type = f"image/{fmt}"
            data_uri = f"data:{mime_type};base64,{image_data}"
            
            # Build Pollinations URL - seedance model supports image-to-video
            # Use POST to avoid URL length limits, but keep model in query params to ensure it's respected
            base_url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(motion_prompt or "natural motion")
            api_url = f"{base_url}?model=seedance&nologo=true"
            
            # Construct payload for POST
            payload = {
                "model": "seedance",
                "duration": str(min(10, max(2, duration))),
                "image": data_uri,
                "nologo": "true",
                "nofeed": "true",
                "prompt": motion_prompt or "natural motion"
            }
            
            print(f"[MediaTools] Calling Pollinations.ai FREE image-to-video API (POST)...")
            print(f"[MediaTools] Duration: {duration}s, Motion: {motion_prompt[:50]}...")
            
            # Make request (this can take 30-90 seconds for video)
            req = urllib.request.Request(
                api_url, 
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "AgentAmigos/1.0"},
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=180) as resp:  # 3 minute timeout
                content_type = resp.headers.get("Content-Type", "")
                
                if "video" in content_type:
                    video_data = resp.read()
                    
                    # Save the video
                    with open(output_path, "wb") as f:
                        f.write(video_data)
                    
                    file_size = os.path.getsize(output_path)
                    if file_size < 1000:
                        return {"success": False, "error": f"Downloaded file too small: {file_size} bytes"}
                    
                    return {
                        "success": True,
                        "video_path": output_path,
                        "file_size": file_size,
                        "source": "pollinations",
                        "model": "seedance",
                        "prompt": motion_prompt,
                        "duration": duration,
                        "note": "Generated using Pollinations.ai FREE API (no API key required!)"
                    }
                else:
                    return {"success": False, "error": f"Unexpected content type: {content_type}"}
                    
        except urllib.error.HTTPError as e:
            return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return {"success": False, "error": f"URL Error: {e.reason}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    
    def generate_video_pollinations_t2v(
        self,
        prompt: str,
        duration: int = 4,
        model: str = "seedance",  # seedance or veo
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate video from text using Pollinations.ai FREE API.
        
        This is 100% FREE with NO API key required!
        
        Models available:
        - seedance: BytePlus Seedance Lite (2-10 seconds, good quality)
        - veo: Google Veo 3.1 Fast (4-8 seconds, excellent quality)
        
        Args:
            prompt: Text description of the video
            duration: Video duration in seconds (2-10 for seedance, 4-8 for veo)
            model: "seedance" (default) or "veo"
            output_path: Optional custom output path
            
        Returns:
            Dict with success, video_path, and metadata
        """
        if not prompt:
            return {"success": False, "error": "Prompt is required"}
        
        output_file = (
            Path(output_path)
            if output_path
            else self.video_output_dir / f"pollinations_video_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Build Pollinations URL
            prompt_encoded = urllib.parse.quote(prompt)
            api_url = "https://image.pollinations.ai/prompt/" + prompt_encoded
            
            # Configure duration based on model
            if model == "veo":
                video_duration = str(min(8, max(4, duration)))  # Veo: 4-8 seconds
            else:
                video_duration = str(min(10, max(2, duration)))  # Seedance: 2-10 seconds
            
            params = {
                "model": model,
                "duration": video_duration,
                "nologo": "true",
                "nofeed": "true",
            }
            full_url = api_url + "?" + urllib.parse.urlencode(params)
            
            print(f"[MediaTools] Calling Pollinations.ai FREE text-to-video API...")
            print(f"[MediaTools] Model: {model}, Duration: {video_duration}s")
            print(f"[MediaTools] Prompt: {prompt[:80]}...")
            
            # Make request (video generation takes 30-90 seconds)
            req = urllib.request.Request(full_url, method="GET")
            req.add_header("User-Agent", "AgentAmigos/1.0")
            
            with urllib.request.urlopen(req, timeout=180) as resp:  # 3 minute timeout
                content_type = resp.headers.get("Content-Type", "")
                
                if "video" in content_type:
                    video_data = resp.read()
                    
                    # Save the video
                    with open(str(output_file), "wb") as f:
                        f.write(video_data)
                    
                    file_size = os.path.getsize(str(output_file))
                    if file_size < 1000:
                        return {"success": False, "error": f"Downloaded file too small: {file_size} bytes"}
                    
                    return {
                        "success": True,
                        "video_path": str(output_file),
                        "file_size": file_size,
                        "source": "pollinations",
                        "model": model,
                        "prompt": prompt,
                        "duration": int(video_duration),
                        "note": "Generated using Pollinations.ai FREE API (no API key required!)"
                    }
                else:
                    # Might be an image - try to interpret response
                    return {"success": False, "error": f"Expected video, got: {content_type}. Try adding more motion-related words to your prompt."}
                    
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            if e.code == 503:
                error_msg = "Model is loading, try again in a few minutes"
            return {"success": False, "error": error_msg}
        except urllib.error.URLError as e:
            return {"success": False, "error": f"URL Error: {e.reason}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    
    def _generate_video_replicate(
        self, image_path: str, motion_prompt: str, duration: int, output_path: str
    ) -> Dict[str, Any]:
        """Generate video using Replicate's Stable Video Diffusion (free tier available)."""
        api_token = os.environ.get("REPLICATE_API_TOKEN")
        if not api_token:
            return {"success": False, "error": "REPLICATE_API_TOKEN not set"}
        
        try:
            # Read and encode image
            _lazy_import_image_libs()
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Determine image mime type
            img = Image.open(image_path)
            fmt = img.format.lower() if img.format else "png"
            mime_type = f"image/{fmt}"
            data_uri = f"data:{mime_type};base64,{image_data}"
            
            # Call Replicate API for Stable Video Diffusion
            headers = {
                "Authorization": f"Token {api_token}",
                "Content-Type": "application/json"
            }
            
            # Use stable-video-diffusion model
            payload = {
                "version": "3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
                "input": {
                    "input_image": data_uri,
                    "motion_bucket_id": min(255, max(1, int(duration * 30))),  # Controls motion amount
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
            
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            
            prediction_id = result.get("id")
            if not prediction_id:
                return {"success": False, "error": "No prediction ID returned"}
            
            # Poll for completion
            print(f"[MediaTools] Replicate prediction started: {prediction_id}")
            for _ in range(120):  # Wait up to 2 minutes
                time.sleep(2)
                status_req = urllib.request.Request(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers={"Authorization": f"Token {api_token}"}
                )
                with urllib.request.urlopen(status_req, timeout=30) as resp:
                    status_result = json.loads(resp.read().decode("utf-8"))
                
                status = status_result.get("status")
                if status == "succeeded":
                    output_url = status_result.get("output")
                    if output_url:
                        # Download the video
                        if isinstance(output_url, list):
                            output_url = output_url[0]
                        urllib.request.urlretrieve(output_url, output_path)
                        return {
                            "success": True,
                            "video_path": output_path,
                            "source": "replicate",
                            "model": "stable-video-diffusion",
                            "motion_prompt": motion_prompt
                        }
                elif status == "failed":
                    return {"success": False, "error": status_result.get("error", "Generation failed")}
            
            return {"success": False, "error": "Timeout waiting for video generation"}
            
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    
    def _generate_video_huggingface(
        self, image_path: str, motion_prompt: str, duration: int, output_path: str
    ) -> Dict[str, Any]:
        """Generate video using Hugging Face Inference API (free tier)."""
        api_token = os.environ.get("HUGGINGFACE_TOKEN") or os.environ.get("HF_TOKEN")
        if not api_token:
            return {"success": False, "error": "HUGGINGFACE_TOKEN not set"}
        
        try:
            _lazy_import_image_libs()
            
            # Read and encode image
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            # Try Stable Video Diffusion on HuggingFace
            headers = {
                "Authorization": f"Bearer {api_token}",
            }
            
            # Use image-to-video model
            model_url = "https://api-inference.huggingface.co/models/stabilityai/stable-video-diffusion-img2vid-xt"
            
            req = urllib.request.Request(
                model_url,
                data=image_data,
                headers=headers,
                method="POST"
            )
            
            print("[MediaTools] Calling HuggingFace Stable Video Diffusion...")
            with urllib.request.urlopen(req, timeout=120) as resp:
                video_data = resp.read()
            
            # Save the video
            with open(output_path, "wb") as f:
                f.write(video_data)
            
            return {
                "success": True,
                "video_path": output_path,
                "source": "huggingface",
                "model": "stable-video-diffusion-img2vid-xt",
                "motion_prompt": motion_prompt
            }
            
        except urllib.error.HTTPError as e:
            if e.code == 503:
                return {"success": False, "error": "Model is loading, try again in a few minutes"}
            return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    
    def _generate_video_stability(
        self, image_path: str, motion_prompt: str, duration: int, output_path: str
    ) -> Dict[str, Any]:
        """Generate video using Stability AI API."""
        api_key = os.environ.get("STABILITY_API_KEY")
        if not api_key:
            return {"success": False, "error": "STABILITY_API_KEY not set"}
        
        try:
            _lazy_import_image_libs()
            
            # Read image
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            # Stability AI image-to-video endpoint
            import urllib.request
            from urllib.parse import urlencode
            
            # Create multipart form data
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
            body.append(b'Content-Disposition: form-data; name="cfg_scale"')
            body.append(b"")
            body.append(b"2.5")
            body.append(f"--{boundary}".encode())
            body.append(b'Content-Disposition: form-data; name="motion_bucket_id"')
            body.append(b"")
            body.append(str(min(255, duration * 40)).encode())
            body.append(f"--{boundary}--".encode())
            
            body_data = b"\r\n".join(body)
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            }
            
            req = urllib.request.Request(
                "https://api.stability.ai/v2beta/image-to-video",
                data=body_data,
                headers=headers,
                method="POST"
            )
            
            print("[MediaTools] Calling Stability AI image-to-video...")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            
            generation_id = result.get("id")
            if not generation_id:
                return {"success": False, "error": "No generation ID returned"}
            
            # Poll for completion
            for _ in range(90):  # Wait up to 3 minutes
                time.sleep(2)
                status_req = urllib.request.Request(
                    f"https://api.stability.ai/v2beta/image-to-video/result/{generation_id}",
                    headers={"Authorization": f"Bearer {api_key}", "Accept": "video/*"}
                )
                try:
                    with urllib.request.urlopen(status_req, timeout=30) as resp:
                        if resp.status == 200:
                            video_data = resp.read()
                            with open(output_path, "wb") as f:
                                f.write(video_data)
                            return {
                                "success": True,
                                "video_path": output_path,
                                "source": "stability",
                                "model": "stable-video-diffusion",
                                "motion_prompt": motion_prompt
                            }
                except urllib.error.HTTPError as e:
                    if e.code == 202:
                        continue  # Still processing
                    raise
            
            return {"success": False, "error": "Timeout waiting for video generation"}
            
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # TEXT-TO-VIDEO - Real AI Video Generation (FREE with Pollinations!)
    # ------------------------------------------------------------------
    def generate_ai_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        output_path: Optional[str] = None,
        model: str = "pollinations",  # pollinations (FREE!), wan, minimax, ltx
        negative_prompt: str = "",
    ) -> Dict[str, Any]:
        """
        Generate REAL AI video from text prompt.
        
        This creates actual animated video with motion (not slideshows).
        
        RECOMMENDED: Use "pollinations" model (FREE, no API key required!)
        Other models require API keys from Replicate or fal.ai.
        
        Args:
            prompt: Text description of the video to generate
            duration: Video duration in seconds (2-10 typically)
            aspect_ratio: "16:9", "9:16", "1:1"
            output_path: Optional custom output path
            model: "pollinations" (FREE!), "veo", "seedance", "wan", "minimax", "ltx"
            negative_prompt: What to avoid in the video
            
        Returns:
            Dict with success, video_path, and metadata
        """
        if not prompt:
            return {"success": False, "error": "Prompt is required"}
        
        output_file = (
            Path(output_path)
            if output_path
            else self.video_output_dir / f"ai_video_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"[MediaTools] Generating AI video with {model} model...")
        print(f"[MediaTools] Prompt: {prompt[:100]}...")
        
        errors = []
        
        # Try Pollinations.ai FIRST (FREE, no API key!)
        if model in ["pollinations", "seedance", "veo"]:
            pollinations_model = "veo" if model == "veo" else "seedance"
            result = self.generate_video_pollinations_t2v(prompt, duration, pollinations_model, str(output_file))
            if result.get("success"):
                return result
            errors.append(f"Pollinations ({pollinations_model}): {result.get('error', 'Unknown error')}")
            
            # If user specifically asked for Pollinations and it failed, try the other model
            if model == "pollinations":
                alt_model = "veo" if pollinations_model == "seedance" else "seedance"
                result = self.generate_video_pollinations_t2v(prompt, duration, alt_model, str(output_file))
                if result.get("success"):
                    return result
                errors.append(f"Pollinations ({alt_model}): {result.get('error', 'Unknown error')}")
        
        # Try Replicate (requires API key)
        api_token = os.environ.get("REPLICATE_API_TOKEN")
        if api_token:
            result = self._text_to_video_replicate(prompt, duration, aspect_ratio, str(output_file), model, negative_prompt)
            if result.get("success"):
                return result
            errors.append(f"Replicate: {result.get('error', 'Unknown error')}")
        else:
            errors.append("Replicate: REPLICATE_API_TOKEN not set")
        
        # Try fal.ai as backup
        fal_key = os.environ.get("FAL_KEY")
        if fal_key:
            result = self._text_to_video_fal(prompt, duration, aspect_ratio, str(output_file))
            if result.get("success"):
                return result
            errors.append(f"Fal.ai: {result.get('error', 'Unknown error')}")
        else:
            errors.append("Fal.ai: FAL_KEY not set")
        
        # Fallback: Generate images and create slideshow
        print("[MediaTools] No video API available, falling back to AI image slideshow...")
        result = self.generate_video(prompt=prompt, duration=duration, fps=24, resolution="1920x1080")
        if result.get("success"):
            result["note"] = "Created slideshow from AI images (no video API key set)"
            result["setup_instructions"] = (
                "For REAL AI video generation with actual motion, set:\n"
                "  REPLICATE_API_TOKEN=r8_... (get at replicate.com)\n"
                "  or FAL_KEY=... (get at fal.ai)\n\n"
                "Replicate offers: WAN (fast/cheap), Minimax (high quality), LTX-Video"
            )
        return result
    
    def _text_to_video_replicate(
        self,
        prompt: str,
        duration: int,
        aspect_ratio: str,
        output_path: str,
        model: str = "wan",
        negative_prompt: str = "",
    ) -> Dict[str, Any]:
        """Generate video using Replicate's text-to-video models."""
        api_token = os.environ.get("REPLICATE_API_TOKEN")
        if not api_token:
            return {"success": False, "error": "REPLICATE_API_TOKEN not set"}
        
        try:
            headers = {
                "Authorization": f"Token {api_token}",
                "Content-Type": "application/json"
            }
            
            # Select model and build payload
            if model == "minimax" or model == "hailuo":
                # Minimax/Hailuo - high quality 6s videos
                model_version = "minimax/video-01"
                payload = {
                    "input": {
                        "prompt": prompt,
                        "prompt_optimizer": True,
                    }
                }
            elif model == "ltx":
                # LTX-Video - Lightricks fast generation
                model_version = "lightricks/ltx-video"
                payload = {
                    "input": {
                        "prompt": prompt,
                        "negative_prompt": negative_prompt or "worst quality, inconsistent motion, blurry",
                        "num_frames": min(97, duration * 24),
                        "width": 768 if "9:16" in aspect_ratio else 1280 if "16:9" in aspect_ratio else 768,
                        "height": 1280 if "9:16" in aspect_ratio else 720 if "16:9" in aspect_ratio else 768,
                    }
                }
            else:
                # WAN 2.1 - Default, fast and affordable
                model_version = "wan-video/wan-2.1-t2v-480p"
                payload = {
                    "input": {
                        "prompt": prompt,
                        "negative_prompt": negative_prompt or "Bright tones, overexposed, static, blurred details, subtitles, style, works, paintings, images, static, overall gray, worst quality, low quality, JPEG compression residue, ugly, incomplete, extra fingers, poorly drawn hands, poorly drawn faces, deformed, disfigured, misshapen limbs, fused fingers, still picture, messy background, three legs, many people in the background, walking backwards",
                        "max_area": "832x480" if "16:9" in aspect_ratio else "480x832" if "9:16" in aspect_ratio else "624x624",
                        "duration": min(5, duration),  # WAN supports up to 5s
                        "seed": random.randint(0, 2147483647),
                    }
                }
            
            # Create prediction
            create_url = f"https://api.replicate.com/v1/models/{model_version}/predictions"
            
            req = urllib.request.Request(
                create_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            
            print(f"[MediaTools] Starting Replicate {model_version}...")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            
            prediction_id = result.get("id")
            prediction_url = result.get("urls", {}).get("get")
            
            if not prediction_id:
                return {"success": False, "error": f"No prediction ID: {result}"}
            
            print(f"[MediaTools] Prediction {prediction_id} started, waiting for completion...")
            
            # Poll for completion (video can take 1-5 minutes)
            poll_url = prediction_url or f"https://api.replicate.com/v1/predictions/{prediction_id}"
            
            for attempt in range(180):  # Wait up to 6 minutes
                time.sleep(2)
                
                status_req = urllib.request.Request(
                    poll_url,
                    headers={"Authorization": f"Token {api_token}"}
                )
                
                with urllib.request.urlopen(status_req, timeout=30) as resp:
                    status_result = json.loads(resp.read().decode("utf-8"))
                
                status = status_result.get("status")
                
                if status == "succeeded":
                    output = status_result.get("output")
                    
                    # Handle different output formats
                    video_url = None
                    if isinstance(output, str):
                        video_url = output
                    elif isinstance(output, list) and output:
                        video_url = output[0]
                    elif isinstance(output, dict):
                        video_url = output.get("video") or output.get("url")
                    
                    if video_url:
                        print(f"[MediaTools] Downloading video from {video_url[:50]}...")
                        urllib.request.urlretrieve(video_url, output_path)
                        
                        # Verify file size
                        file_size = os.path.getsize(output_path)
                        if file_size < 1000:
                            return {"success": False, "error": f"Downloaded file too small: {file_size} bytes"}
                        
                        return {
                            "success": True,
                            "video_path": output_path,
                            "file_size": file_size,
                            "source": "replicate",
                            "model": model_version,
                            "prompt": prompt,
                            "duration": duration,
                        }
                    else:
                        return {"success": False, "error": f"No video URL in output: {output}"}
                        
                elif status == "failed":
                    error = status_result.get("error", "Generation failed")
                    return {"success": False, "error": error}
                    
                elif status == "canceled":
                    return {"success": False, "error": "Generation was canceled"}
                
                # Still processing
                if attempt % 15 == 0:
                    print(f"[MediaTools] Still processing... ({attempt * 2}s elapsed)")
            
            return {"success": False, "error": "Timeout waiting for video (6 min)"}
            
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            return {"success": False, "error": f"HTTP {e.code}: {error_body[:200]}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    
    def _text_to_video_fal(
        self,
        prompt: str,
        duration: int,
        aspect_ratio: str,
        output_path: str,
    ) -> Dict[str, Any]:
        """Generate video using fal.ai's video models (backup)."""
        api_key = os.environ.get("FAL_KEY")
        if not api_key:
            return {"success": False, "error": "FAL_KEY not set"}
        
        try:
            headers = {
                "Authorization": f"Key {api_key}",
                "Content-Type": "application/json"
            }
            
            # Use fal.ai's text-to-video endpoint
            payload = {
                "prompt": prompt,
                "num_frames": duration * 8,
                "aspect_ratio": aspect_ratio,
            }
            
            req = urllib.request.Request(
                "https://queue.fal.run/fal-ai/fast-animatediff/turbo/text-to-video",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            
            print("[MediaTools] Starting fal.ai video generation...")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            
            request_id = result.get("request_id")
            if not request_id:
                return {"success": False, "error": "No request ID returned"}
            
            # Poll for completion
            for _ in range(120):
                time.sleep(2)
                
                status_req = urllib.request.Request(
                    f"https://queue.fal.run/fal-ai/fast-animatediff/turbo/text-to-video/status/{request_id}",
                    headers={"Authorization": f"Key {api_key}"}
                )
                
                with urllib.request.urlopen(status_req, timeout=30) as resp:
                    status_result = json.loads(resp.read().decode("utf-8"))
                
                if status_result.get("status") == "COMPLETED":
                    video_url = status_result.get("response", {}).get("video", {}).get("url")
                    if video_url:
                        urllib.request.urlretrieve(video_url, output_path)
                        return {
                            "success": True,
                            "video_path": output_path,
                            "source": "fal.ai",
                            "model": "animatediff-turbo",
                            "prompt": prompt
                        }
                elif status_result.get("status") == "FAILED":
                    return {"success": False, "error": "fal.ai generation failed"}
            
            return {"success": False, "error": "Timeout waiting for fal.ai"}
            
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def generate_ai_video_from_image(
        self,
        image_path: str,
        prompt: str = "",
        duration: int = 5,
        output_path: Optional[str] = None,
        model: str = "wan",  # wan, minimax, stability
    ) -> Dict[str, Any]:
        """
        Generate REAL AI video from an image using cloud APIs.
        
        This animates a still image into actual video with motion.
        Uses Replicate's image-to-video models.
        
        Args:
            image_path: Path to the source image
            prompt: Optional motion description (e.g., "person walking")
            duration: Video duration in seconds
            output_path: Optional custom output path
            model: "wan" (fast/cheap), "minimax" (high quality), "stability" (svd)
            
        Returns:
            Dict with success, video_path, and metadata
        """
        if not os.path.exists(image_path):
            return {"success": False, "error": f"Image not found: {image_path}"}
        
        output_file = (
            Path(output_path)
            if output_path
            else self.video_output_dir / f"ai_video_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        api_token = os.environ.get("REPLICATE_API_TOKEN")
        if not api_token:
            # Fallback to existing image-to-video that uses multiple APIs
            return self.generate_video_from_image(
                image_path=image_path,
                motion_prompt=prompt,
                duration=duration,
                output_path=str(output_file)
            )
        
        try:
            # Read and encode image
            _lazy_import_image_libs()
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            img = Image.open(image_path)
            fmt = img.format.lower() if img.format else "png"
            data_uri = f"data:image/{fmt};base64,{image_data}"
            
            headers = {
                "Authorization": f"Token {api_token}",
                "Content-Type": "application/json"
            }
            
            # Select model
            if model == "minimax" or model == "hailuo":
                model_version = "minimax/video-01-live"
                payload = {
                    "input": {
                        "prompt": prompt or "natural motion, smooth animation",
                        "first_frame_image": data_uri,
                    }
                }
            elif model == "stability":
                model_version = "stability-ai/stable-video-diffusion"
                payload = {
                    "input": {
                        "input_image": data_uri,
                        "motion_bucket_id": min(255, duration * 40),
                        "fps": 8,
                    }
                }
            else:
                # WAN 2.1 Image-to-Video
                model_version = "wan-video/wan-2.1-i2v-480p"
                payload = {
                    "input": {
                        "prompt": prompt or "smooth natural motion, cinematic",
                        "image": data_uri,
                        "max_area": "832x480",
                        "duration": min(5, duration),
                        "seed": random.randint(0, 2147483647),
                    }
                }
            
            create_url = f"https://api.replicate.com/v1/models/{model_version}/predictions"
            
            req = urllib.request.Request(
                create_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            
            print(f"[MediaTools] Starting Replicate {model_version} image-to-video...")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            
            prediction_id = result.get("id")
            prediction_url = result.get("urls", {}).get("get")
            
            if not prediction_id:
                return {"success": False, "error": f"No prediction ID: {result}"}
            
            # Poll for completion
            poll_url = prediction_url or f"https://api.replicate.com/v1/predictions/{prediction_id}"
            
            for attempt in range(180):
                time.sleep(2)
                
                status_req = urllib.request.Request(
                    poll_url,
                    headers={"Authorization": f"Token {api_token}"}
                )
                
                with urllib.request.urlopen(status_req, timeout=30) as resp:
                    status_result = json.loads(resp.read().decode("utf-8"))
                
                status = status_result.get("status")
                
                if status == "succeeded":
                    output = status_result.get("output")
                    video_url = output if isinstance(output, str) else (output[0] if isinstance(output, list) else None)
                    
                    if video_url:
                        urllib.request.urlretrieve(video_url, str(output_file))
                        file_size = os.path.getsize(str(output_file))
                        
                        return {
                            "success": True,
                            "video_path": str(output_file),
                            "file_size": file_size,
                            "source": "replicate",
                            "model": model_version,
                            "source_image": image_path,
                        }
                        
                elif status == "failed":
                    return {"success": False, "error": status_result.get("error", "Generation failed")}
                
                if attempt % 15 == 0:
                    print(f"[MediaTools] Processing... ({attempt * 2}s)")
            
            return {"success": False, "error": "Timeout"}
            
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Image manipulation tools
    # ------------------------------------------------------------------
    def open_image(self, image_path: str) -> Dict[str, Any]:
        """Open and get info about an image file."""
        _lazy_import_image_libs()
        if not IMAGE_LIBS_AVAILABLE:
            return {"success": False, "error": "Pillow not installed. Run: pip install pillow"}
        try:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"Image not found: {image_path}"}
            img = Image.open(image_path)
            return {
                "success": True,
                "path": image_path,
                "format": img.format,
                "mode": img.mode,
                "size": {"width": img.width, "height": img.height},
                "info": str(img.info) if img.info else None
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def resize_image(
        self,
        image_path: str,
        width: int,
        height: int,
        output_path: Optional[str] = None,
        maintain_aspect: bool = True
    ) -> Dict[str, Any]:
        """Resize an image to specified dimensions."""
        _lazy_import_image_libs()
        if not IMAGE_LIBS_AVAILABLE:
            return {"success": False, "error": "Pillow not installed. Run: pip install pillow"}
        try:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"Image not found: {image_path}"}
            img = Image.open(image_path)
            if maintain_aspect:
                img.thumbnail((width, height), Image.Resampling.LANCZOS)
            else:
                img = img.resize((width, height), Image.Resampling.LANCZOS)
            
            out_path = output_path or str(
                self.image_output_dir / f"resized_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            )
            img.save(out_path)
            return {"success": True, "output_path": out_path, "size": {"width": img.width, "height": img.height}}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def crop_image(
        self,
        image_path: str,
        left: int,
        top: int,
        right: int,
        bottom: int,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crop an image to specified box (left, top, right, bottom)."""
        _lazy_import_image_libs()
        if not IMAGE_LIBS_AVAILABLE:
            return {"success": False, "error": "Pillow not installed. Run: pip install pillow"}
        try:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"Image not found: {image_path}"}
            img = Image.open(image_path)
            cropped = img.crop((left, top, right, bottom))
            out_path = output_path or str(
                self.image_output_dir / f"cropped_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            )
            cropped.save(out_path)
            return {"success": True, "output_path": out_path, "size": {"width": cropped.width, "height": cropped.height}}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def rotate_image(
        self,
        image_path: str,
        degrees: float,
        output_path: Optional[str] = None,
        expand: bool = True
    ) -> Dict[str, Any]:
        """Rotate an image by specified degrees."""
        _lazy_import_image_libs()
        if not IMAGE_LIBS_AVAILABLE:
            return {"success": False, "error": "Pillow not installed. Run: pip install pillow"}
        try:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"Image not found: {image_path}"}
            img = Image.open(image_path)
            rotated = img.rotate(degrees, expand=expand)
            out_path = output_path or str(
                self.image_output_dir / f"rotated_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            )
            rotated.save(out_path)
            return {"success": True, "output_path": out_path, "degrees": degrees}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def convert_image_format(
        self,
        image_path: str,
        output_format: str = "PNG",
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert image to different format (PNG, JPEG, BMP, GIF, WEBP)."""
        _lazy_import_image_libs()
        if not IMAGE_LIBS_AVAILABLE:
            return {"success": False, "error": "Pillow not installed. Run: pip install pillow"}
        try:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"Image not found: {image_path}"}
            img = Image.open(image_path)
            # Handle format-specific conversions
            if output_format.upper() in ["JPEG", "JPG"] and img.mode in ["RGBA", "P"]:
                img = img.convert("RGB")
            ext = output_format.lower()
            if ext == "jpg":
                ext = "jpeg"
            out_path = output_path or str(
                self.image_output_dir / f"converted_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}"
            )
            img.save(out_path, format=output_format.upper())
            return {"success": True, "output_path": out_path, "format": output_format.upper()}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def apply_image_filter(
        self,
        image_path: str,
        filter_name: str = "BLUR",
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Apply filter to image (BLUR, SHARPEN, CONTOUR, EMBOSS, EDGE_ENHANCE, SMOOTH)."""
        _lazy_import_image_libs()
        if not IMAGE_LIBS_AVAILABLE:
            return {"success": False, "error": "Pillow not installed. Run: pip install pillow"}
        try:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"Image not found: {image_path}"}
            
            filters = {
                "BLUR": ImageFilter.BLUR,
                "SHARPEN": ImageFilter.SHARPEN,
                "CONTOUR": ImageFilter.CONTOUR,
                "EMBOSS": ImageFilter.EMBOSS,
                "EDGE_ENHANCE": ImageFilter.EDGE_ENHANCE,
                "SMOOTH": ImageFilter.SMOOTH,
                "DETAIL": ImageFilter.DETAIL,
            }
            if filter_name.upper() not in filters:
                return {"success": False, "error": f"Unknown filter. Available: {list(filters.keys())}"}
            
            img = Image.open(image_path)
            filtered = img.filter(filters[filter_name.upper()])
            out_path = output_path or str(
                self.image_output_dir / f"{filter_name.lower()}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            )
            filtered.save(out_path)
            return {"success": True, "output_path": out_path, "filter": filter_name.upper()}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def adjust_image(
        self,
        image_path: str,
        brightness: float = 1.0,
        contrast: float = 1.0,
        saturation: float = 1.0,
        sharpness: float = 1.0,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Adjust image properties (brightness, contrast, saturation, sharpness). 1.0 = no change."""
        _lazy_import_image_libs()
        if not IMAGE_LIBS_AVAILABLE:
            return {"success": False, "error": "Pillow not installed. Run: pip install pillow"}
        try:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"Image not found: {image_path}"}
            img = Image.open(image_path)
            if brightness != 1.0:
                img = ImageEnhance.Brightness(img).enhance(brightness)
            if contrast != 1.0:
                img = ImageEnhance.Contrast(img).enhance(contrast)
            if saturation != 1.0:
                img = ImageEnhance.Color(img).enhance(saturation)
            if sharpness != 1.0:
                img = ImageEnhance.Sharpness(img).enhance(sharpness)
            out_path = output_path or str(
                self.image_output_dir / f"adjusted_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            )
            img.save(out_path)
            return {
                "success": True, 
                "output_path": out_path,
                "adjustments": {"brightness": brightness, "contrast": contrast, "saturation": saturation, "sharpness": sharpness}
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def create_thumbnail(
        self,
        image_path: str,
        max_size: int = 200,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a thumbnail of an image."""
        _lazy_import_image_libs()
        if not IMAGE_LIBS_AVAILABLE:
            return {"success": False, "error": "Pillow not installed. Run: pip install pillow"}
        try:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"Image not found: {image_path}"}
            img = Image.open(image_path)
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            out_path = output_path or str(
                self.image_output_dir / f"thumb_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            )
            img.save(out_path)
            return {"success": True, "output_path": out_path, "size": {"width": img.width, "height": img.height}}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def list_images(self, directory: Optional[str] = None) -> Dict[str, Any]:
        """List all images in a directory (defaults to media_outputs/images)."""
        _lazy_import_image_libs()
        try:
            search_dir = Path(directory) if directory else self.image_output_dir
            if not search_dir.exists():
                return {"success": False, "error": f"Directory not found: {search_dir}"}
            
            image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
            images = []
            for f in search_dir.iterdir():
                if f.suffix.lower() in image_extensions:
                    images.append({
                        "name": f.name,
                        "path": str(f),
                        "size_bytes": f.stat().st_size,
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                    })
            return {"success": True, "directory": str(search_dir), "images": images, "count": len(images)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Audio/MP3 tools
    # ------------------------------------------------------------------
    def get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """Get information about an audio file (MP3, WAV, etc.)."""
        _lazy_import_audio_libs()
        if not AUDIO_LIBS_AVAILABLE:
            return {"success": False, "error": "pydub not installed. Run: pip install pydub"}
        try:
            if not os.path.exists(audio_path):
                return {"success": False, "error": f"Audio file not found: {audio_path}"}
            audio = AudioSegment.from_file(audio_path)
            return {
                "success": True,
                "path": audio_path,
                "duration_seconds": len(audio) / 1000.0,
                "duration_ms": len(audio),
                "channels": audio.channels,
                "sample_rate": audio.frame_rate,
                "sample_width": audio.sample_width,
                "frame_count": audio.frame_count()
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def convert_audio(
        self,
        audio_path: str,
        output_format: str = "mp3",
        output_path: Optional[str] = None,
        bitrate: str = "192k"
    ) -> Dict[str, Any]:
        """Convert audio file to different format (mp3, wav, ogg, flac, aac)."""
        _lazy_import_audio_libs()
        if not AUDIO_LIBS_AVAILABLE:
            return {"success": False, "error": "pydub not installed. Run: pip install pydub"}
        try:
            if not os.path.exists(audio_path):
                return {"success": False, "error": f"Audio file not found: {audio_path}"}
            audio = AudioSegment.from_file(audio_path)
            out_path = output_path or str(
                self.audio_output_dir / f"converted_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{output_format}"
            )
            export_params = {}
            if output_format == "mp3":
                export_params["bitrate"] = bitrate
            audio.export(out_path, format=output_format, **export_params)
            return {"success": True, "output_path": out_path, "format": output_format}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def trim_audio(
        self,
        audio_path: str,
        start_ms: int = 0,
        end_ms: Optional[int] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trim audio file from start to end (in milliseconds)."""
        _lazy_import_audio_libs()
        if not AUDIO_LIBS_AVAILABLE:
            return {"success": False, "error": "pydub not installed. Run: pip install pydub"}
        try:
            if not os.path.exists(audio_path):
                return {"success": False, "error": f"Audio file not found: {audio_path}"}
            audio = AudioSegment.from_file(audio_path)
            end = end_ms if end_ms else len(audio)
            trimmed = audio[start_ms:end]
            ext = Path(audio_path).suffix.lstrip(".")
            out_path = output_path or str(
                self.audio_output_dir / f"trimmed_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}"
            )
            trimmed.export(out_path, format=ext)
            return {
                "success": True,
                "output_path": out_path,
                "original_duration_ms": len(audio),
                "trimmed_duration_ms": len(trimmed)
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def merge_audio(
        self,
        audio_paths: List[str],
        output_path: Optional[str] = None,
        output_format: str = "mp3"
    ) -> Dict[str, Any]:
        """Merge multiple audio files into one."""
        _lazy_import_audio_libs()
        if not AUDIO_LIBS_AVAILABLE:
            return {"success": False, "error": "pydub not installed. Run: pip install pydub"}
        try:
            if not audio_paths:
                return {"success": False, "error": "No audio paths provided"}
            combined = AudioSegment.empty()
            for path in audio_paths:
                if not os.path.exists(path):
                    return {"success": False, "error": f"Audio file not found: {path}"}
                audio = AudioSegment.from_file(path)
                combined += audio
            out_path = output_path or str(
                self.audio_output_dir / f"merged_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{output_format}"
            )
            combined.export(out_path, format=output_format)
            return {
                "success": True,
                "output_path": out_path,
                "total_duration_ms": len(combined),
                "files_merged": len(audio_paths)
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def adjust_audio_volume(
        self,
        audio_path: str,
        volume_db: float = 0.0,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Adjust audio volume by decibels (positive = louder, negative = quieter)."""
        _lazy_import_audio_libs()
        if not AUDIO_LIBS_AVAILABLE:
            return {"success": False, "error": "pydub not installed. Run: pip install pydub"}
        try:
            if not os.path.exists(audio_path):
                return {"success": False, "error": f"Audio file not found: {audio_path}"}
            audio = AudioSegment.from_file(audio_path)
            adjusted = audio + volume_db
            ext = Path(audio_path).suffix.lstrip(".")
            out_path = output_path or str(
                self.audio_output_dir / f"volume_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}"
            )
            adjusted.export(out_path, format=ext)
            return {"success": True, "output_path": out_path, "volume_change_db": volume_db}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def add_fade(
        self,
        audio_path: str,
        fade_in_ms: int = 0,
        fade_out_ms: int = 0,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add fade in/out effects to audio."""
        _lazy_import_audio_libs()
        if not AUDIO_LIBS_AVAILABLE:
            return {"success": False, "error": "pydub not installed. Run: pip install pydub"}
        try:
            if not os.path.exists(audio_path):
                return {"success": False, "error": f"Audio file not found: {audio_path}"}
            audio = AudioSegment.from_file(audio_path)
            if fade_in_ms > 0:
                audio = audio.fade_in(fade_in_ms)
            if fade_out_ms > 0:
                audio = audio.fade_out(fade_out_ms)
            ext = Path(audio_path).suffix.lstrip(".")
            out_path = output_path or str(
                self.audio_output_dir / f"faded_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}"
            )
            audio.export(out_path, format=ext)
            return {"success": True, "output_path": out_path, "fade_in_ms": fade_in_ms, "fade_out_ms": fade_out_ms}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def extract_audio_from_video(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        output_format: str = "mp3"
    ) -> Dict[str, Any]:
        """Extract audio track from a video file."""
        _lazy_import_video_libs()
        if not VIDEO_LIBS_AVAILABLE:
            return {"success": False, "error": "moviepy not installed. Run: pip install moviepy"}
        try:
            if not os.path.exists(video_path):
                return {"success": False, "error": f"Video file not found: {video_path}"}
            from moviepy.editor import VideoFileClip
            video = VideoFileClip(video_path)
            if video.audio is None:
                video.close()
                return {"success": False, "error": "Video has no audio track"}
            out_path = output_path or str(
                self.audio_output_dir / f"extracted_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{output_format}"
            )
            video.audio.write_audiofile(out_path)
            duration = video.audio.duration
            video.close()
            return {"success": True, "output_path": out_path, "duration_seconds": duration}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def list_audio_files(self, directory: Optional[str] = None) -> Dict[str, Any]:
        """List all audio files in a directory (defaults to media_outputs/audio)."""
        try:
            search_dir = Path(directory) if directory else self.audio_output_dir
            if not search_dir.exists():
                return {"success": False, "error": f"Directory not found: {search_dir}"}
            
            audio_extensions = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a", ".wma"}
            files = []
            for f in search_dir.iterdir():
                if f.suffix.lower() in audio_extensions:
                    files.append({
                        "name": f.name,
                        "path": str(f),
                        "size_bytes": f.stat().st_size,
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                    })
            return {"success": True, "directory": str(search_dir), "audio_files": files, "count": len(files)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Video/MP4 tools
    # ------------------------------------------------------------------
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Get information about a video file."""
        _lazy_import_video_libs()
        if not VIDEO_LIBS_AVAILABLE:
            return {"success": False, "error": "moviepy not installed. Run: pip install moviepy"}
        try:
            if not os.path.exists(video_path):
                return {"success": False, "error": f"Video file not found: {video_path}"}
            from moviepy.editor import VideoFileClip
            video = VideoFileClip(video_path)
            info = {
                "success": True,
                "path": video_path,
                "duration_seconds": video.duration,
                "size": {"width": video.w, "height": video.h},
                "fps": video.fps,
                "has_audio": video.audio is not None
            }
            video.close()
            return info
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def trim_video(
        self,
        video_path: str,
        start_seconds: float = 0,
        end_seconds: Optional[float] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trim video from start to end time (in seconds)."""
        _lazy_import_video_libs()
        if not VIDEO_LIBS_AVAILABLE:
            return {"success": False, "error": "moviepy not installed. Run: pip install moviepy"}
        try:
            if not os.path.exists(video_path):
                return {"success": False, "error": f"Video file not found: {video_path}"}
            from moviepy.editor import VideoFileClip
            video = VideoFileClip(video_path)
            end = end_seconds if end_seconds else video.duration
            trimmed = video.subclip(start_seconds, end)
            out_path = output_path or str(
                self.video_output_dir / f"trimmed_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
            )
            trimmed.write_videofile(out_path, codec="libx264", audio_codec="aac")
            original_duration = video.duration
            new_duration = trimmed.duration
            video.close()
            trimmed.close()
            return {
                "success": True,
                "output_path": out_path,
                "original_duration": original_duration,
                "trimmed_duration": new_duration
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def merge_videos(
        self,
        video_paths: List[str],
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Concatenate multiple videos into one."""
        _lazy_import_video_libs()
        if not VIDEO_LIBS_AVAILABLE:
            return {"success": False, "error": "moviepy not installed. Run: pip install moviepy"}
        try:
            if not video_paths:
                return {"success": False, "error": "No video paths provided"}
            from moviepy.editor import VideoFileClip, concatenate_videoclips
            clips = []
            for path in video_paths:
                if not os.path.exists(path):
                    return {"success": False, "error": f"Video file not found: {path}"}
                clips.append(VideoFileClip(path))
            merged = concatenate_videoclips(clips)
            out_path = output_path or str(
                self.video_output_dir / f"merged_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
            )
            merged.write_videofile(out_path, codec="libx264", audio_codec="aac")
            total_duration = merged.duration
            merged.close()
            for clip in clips:
                clip.close()
            return {
                "success": True,
                "output_path": out_path,
                "total_duration": total_duration,
                "videos_merged": len(video_paths)
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def resize_video(
        self,
        video_path: str,
        width: int,
        height: int,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resize video to specified dimensions."""
        _lazy_import_video_libs()
        if not VIDEO_LIBS_AVAILABLE:
            return {"success": False, "error": "moviepy not installed. Run: pip install moviepy"}
        try:
            if not os.path.exists(video_path):
                return {"success": False, "error": f"Video file not found: {video_path}"}
            from moviepy.editor import VideoFileClip
            video = VideoFileClip(video_path)
            resized = video.resize(newsize=(width, height))
            out_path = output_path or str(
                self.video_output_dir / f"resized_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
            )
            resized.write_videofile(out_path, codec="libx264", audio_codec="aac")
            resized.close()
            video.close()
            return {"success": True, "output_path": out_path, "size": {"width": width, "height": height}}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def add_audio_to_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: Optional[str] = None,
        loop_audio: bool = True
    ) -> Dict[str, Any]:
        """Add audio track to a video file."""
        _lazy_import_video_libs()
        if not VIDEO_LIBS_AVAILABLE:
            return {"success": False, "error": "moviepy not installed. Run: pip install moviepy"}
        try:
            if not os.path.exists(video_path):
                return {"success": False, "error": f"Video file not found: {video_path}"}
            if not os.path.exists(audio_path):
                return {"success": False, "error": f"Audio file not found: {audio_path}"}
            from moviepy.editor import VideoFileClip, AudioFileClip, afx
            video = VideoFileClip(video_path)
            audio = AudioFileClip(audio_path)
            if loop_audio and audio.duration < video.duration:
                audio = afx.audio_loop(audio, duration=video.duration)
            elif audio.duration > video.duration:
                audio = audio.subclip(0, video.duration)
            video_with_audio = video.set_audio(audio)
            out_path = output_path or str(
                self.video_output_dir / f"with_audio_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
            )
            video_with_audio.write_videofile(out_path, codec="libx264", audio_codec="aac")
            video.close()
            audio.close()
            video_with_audio.close()
            return {"success": True, "output_path": out_path, "duration": video.duration}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def convert_video(
        self,
        video_path: str,
        output_format: str = "mp4",
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert video to different format (mp4, avi, webm, mov)."""
        _lazy_import_video_libs()
        if not VIDEO_LIBS_AVAILABLE:
            return {"success": False, "error": "moviepy not installed. Run: pip install moviepy"}
        try:
            if not os.path.exists(video_path):
                return {"success": False, "error": f"Video file not found: {video_path}"}
            from moviepy.editor import VideoFileClip
            video = VideoFileClip(video_path)
            codecs = {
                "mp4": ("libx264", "aac"),
                "avi": ("mpeg4", "mp3"),
                "webm": ("libvpx", "libvorbis"),
                "mov": ("libx264", "aac"),
            }
            if output_format.lower() not in codecs:
                return {"success": False, "error": f"Unsupported format. Use: {list(codecs.keys())}"}
            video_codec, audio_codec = codecs[output_format.lower()]
            out_path = output_path or str(
                self.video_output_dir / f"converted_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{output_format}"
            )
            video.write_videofile(out_path, codec=video_codec, audio_codec=audio_codec)
            video.close()
            return {"success": True, "output_path": out_path, "format": output_format}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def convert_reel_to_youtube(
        self,
        video_path: str,
        target_resolution: str = "1920x1080",
        output_format: str = "mp4",
        output_path: Optional[str] = None,
        pad_color: Any = "#0f0f1a",
        blur_background: bool = False,
    ) -> Dict[str, Any]:
        """Convert a vertical reel into a YouTube-friendly landscape with padding/blur."""
        _lazy_import_video_libs()
        if not VIDEO_LIBS_AVAILABLE:
            return {"success": False, "error": "moviepy not installed. Run: pip install moviepy"}
        try:
            if not os.path.exists(video_path):
                return {"success": False, "error": f"Video file not found: {video_path}"}

            target_w, target_h = self._parse_resolution(target_resolution)

            def _parse_color(value: Any) -> Tuple[int, int, int]:
                if isinstance(value, (list, tuple)) and len(value) == 3:
                    try:
                        return tuple(int(x) for x in value)
                    except Exception:
                        return (15, 15, 26)
                if isinstance(value, str):
                    val = value.lstrip("#")
                    if len(val) == 6:
                        try:
                            return tuple(int(val[i:i+2], 16) for i in (0, 2, 4))
                        except Exception:
                            return (15, 15, 26)
                return (15, 15, 26)

            from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip
            # Try different import paths for gaussian_blur (varies by moviepy version)
            try:
                from moviepy.video.fx.all import gaussian_blur
            except ImportError:
                try:
                    from moviepy.video.fx import gaussian_blur
                except ImportError:
                    # Define a simple fallback that just returns the clip unchanged
                    def gaussian_blur(clip, sigma=2):
                        return clip

            video = VideoFileClip(video_path)
            src_aspect = video.w / video.h if video.h else target_w / target_h
            target_aspect = target_w / target_h
            pad_rgb = _parse_color(pad_color)

            if src_aspect >= target_aspect:
                resized = video.resize(width=target_w)
                output_clip = resized.set_audio(video.audio)
                padded = False
            else:
                foreground = video.resize(height=target_h).set_audio(video.audio)
                if foreground.w > target_w:
                    foreground = foreground.resize(width=target_w)

                background = ColorClip((target_w, target_h), color=pad_rgb).set_duration(video.duration)

                if blur_background:
                    try:
                        blurred = video.resize(height=target_h)
                        if blurred.w < target_w:
                            blurred = blurred.resize(width=target_w)
                        blurred = gaussian_blur(blurred, sigma=8)
                        background = blurred.set_position("center")
                    except Exception:
                        # Fall back to solid background if blur fails
                        background = background

                output_clip = CompositeVideoClip(
                    [background, foreground.set_position("center")],
                    size=(target_w, target_h),
                )
                if video.audio:
                    output_clip = output_clip.set_audio(video.audio)
                padded = True

            out_path = output_path or str(
                self.video_output_dir / f"youtube_ready_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{output_format}"
            )

            output_clip.write_videofile(
                out_path,
                codec="libx264",
                audio_codec="aac",
                threads=4,
                preset="medium",
            )

            video.close()
            output_clip.close()

            return {
                "success": True,
                "output_path": out_path,
                "target_resolution": f"{target_w}x{target_h}",
                "padded": padded,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def extract_frame(
        self,
        video_path: str,
        time_seconds: float,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract a single frame from video at specified time."""
        _lazy_import_video_libs()
        _lazy_import_image_libs()
        if not VIDEO_LIBS_AVAILABLE:
            return {"success": False, "error": "moviepy not installed. Run: pip install moviepy"}
        try:
            if not os.path.exists(video_path):
                return {"success": False, "error": f"Video file not found: {video_path}"}
            from moviepy.editor import VideoFileClip
            video = VideoFileClip(video_path)
            if time_seconds > video.duration:
                return {"success": False, "error": f"Time {time_seconds}s exceeds video duration {video.duration}s"}
            frame = video.get_frame(time_seconds)
            out_path = output_path or str(
                self.image_output_dir / f"frame_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            )
            if IMAGE_LIBS_AVAILABLE:
                img = Image.fromarray(frame)
                img.save(out_path)
            else:
                import imageio
                imageio.imwrite(out_path, frame)
            video.close()
            return {"success": True, "output_path": out_path, "time_seconds": time_seconds}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Vehicle Restoration (model-locked | image -> MP4)
    # ------------------------------------------------------------------
    def restore_vehicle_video(
        self,
        image_filename: Optional[str] = None,
        image_path: Optional[str] = None,
        duration: int = 10,
        fps: int = 24,
        model: str = "auto",
        extra_notes: str = "",
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate an "old vehicle restoration" MP4 from a still photo.

        This tool is **model-locked** in intent: it aims to preserve the exact vehicle identity
        (make/model/body silhouette), while producing a cinematic restoration sequence.

        Behavior:
        - First, attempt true image-to-video (cloud) generation when available.
        - If AI motion isn't available/reliable, fall back to a procedural restoration animation
          (filter + wipe reveal + polish) that runs locally and preserves identity.

        Args:
            image_filename: Filename under media_outputs/images (preferred when coming from /media/upload)
            image_path: Absolute/relative path to an image (alternative to image_filename)
            duration: seconds (2-20 recommended)
            fps: output fps (12-30 recommended)
            model: preferred backend model hint ("auto", "pollinations", "wan", "minimax", "ltx", "stability")
            extra_notes: optional extra direction (kept additive; should not change vehicle model)
            output_path: optional custom output path
        """
        # Resolve input image
        resolved: Optional[Path] = None
        if image_filename:
            resolved = (MEDIA_ROOT / "images" / Path(str(image_filename)).name).resolve()
        elif image_path:
            resolved = Path(str(image_path)).expanduser().resolve()

        if not resolved or not resolved.exists():
            return {
                "success": False,
                "error": f"Image not found. Provide image_filename (under media_outputs/images) or image_path. Got: {image_filename or image_path}",
            }

        dur = int(max(2, min(20, duration or 10)))
        out_fps = int(max(10, min(30, fps or 24)))
        output_file = (
            Path(output_path)
            if output_path
            else self.video_output_dir / f"vehicle_restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Parse hints from extra_notes for procedural fallback
        paint_hint = None
        intensity_hint = "medium"
        if extra_notes:
            parts = str(extra_notes).split("|")
            for p in parts:
                p = p.strip()
                if p.lower().startswith("paint:"):
                    paint_hint = p.split(":", 1)[1].strip()
                elif p.lower().startswith("intensity:"):
                    intensity_hint = p.split(":", 1)[1].strip().lower()

        # Build a strongly constrained prompt (kept reasonably short to avoid provider URL limits).
        prompt = self._build_vehicle_restoration_prompt(extra_notes=extra_notes)

        # --- Attempt real image-to-video when available ---
        preferred_model = str(model or "auto").strip().lower()
        try_models = []
        if preferred_model and preferred_model != "auto":
            try_models.append(preferred_model)
        # Try a sensible default order
        # Prioritize local ComfyUI if available (Open Source / Free)
        default_order = ["comfyui", "wan", "minimax", "stability", "pollinations", "seedance", "veo"]
        for m in default_order:
            if m not in try_models:
                try_models.append(m)

        ai_errors: List[str] = []
        for m in try_models:
            try:
                res = {}
                if m == "comfyui":
                    # Use Local ComfyUI (Open Source)
                    res = self.generate_video_local_comfy(
                        image_path=str(resolved),
                        duration=dur,
                        output_path=str(output_file)
                    )
                elif m in {"pollinations", "seedance"}:
                    # Use Pollinations (Free)
                    res = self._generate_video_pollinations_i2v(
                        image_path=str(resolved),
                        motion_prompt=prompt,
                        duration=dur,
                        output_path=str(output_file)
                    )
                else:
                    # Use Replicate (Paid)
                    res = self.generate_ai_video_from_image(
                        image_path=str(resolved),
                        prompt=prompt,
                        duration=dur,
                        output_path=str(output_file),
                        model=m if m in {"wan", "minimax", "stability", "hailuo"} else "wan",
                    )

                # If the underlying pipeline fell back to a Ken Burns effect, prefer our
                # procedural restoration fallback which at least shows progressive change.
                note = str(res.get("note") or "")
                if res.get("success") and str(res.get("video_path") or "").endswith(".mp4") and "ken burns" not in note.lower():
                    vp = Path(res.get("video_path") or "")
                    if vp.exists():
                        name = vp.name
                        res["url"] = f"/media/videos/{name}"
                        res["download_url"] = f"/media/download/videos/{name}"
                        res["tool"] = "restore_vehicle_video"
                        res["locked_prompt"] = True
                        res["used_fallback"] = False
                        return res

                if not res.get("success"):
                    ai_errors.append(f"{m}: {res.get('error', 'unknown')}")
                else:
                    # Ken Burns or partial success: treat as not-good-enough and continue.
                    ai_errors.append(f"{m}: provider returned non-motion fallback")
            except Exception as exc:
                ai_errors.append(f"{m}: {exc}")

        # --- Procedural fallback (always local, identity-preserving) ---
        proc = self._generate_vehicle_restoration_video_procedural(
            image_path=str(resolved),
            duration=dur,
            fps=out_fps,
            output_path=str(output_file),
            paint_hint=paint_hint,
            intensity_hint=intensity_hint,
        )

        if proc.get("success") and proc.get("video_path"):
            proc["tool"] = "restore_vehicle_video"
            proc["locked_prompt"] = True
            proc["used_fallback"] = True
            proc["ai_attempt_errors"] = ai_errors
        return proc

    def _build_vehicle_restoration_prompt(self, extra_notes: str = "") -> str:
        """Short, model-locked prompt for image-to-video services.

        Keep this concise; some free providers have strict URL length limits.
        """
        base = (
            "MODEL-LOCKED VEHICLE RESTORATION, use the provided photo as the exact reference. "
            "Do NOT change the vehicle make/model/body shape, wheelbase, doors, roofline, grille, headlights, or proportions. "
            "Preserve the same car identity and silhouette. "
            "No morphing, no vehicle swaps, no changing the number/placement of windows or doors. "
            "Cinematic restoration sequence: dusty neglected car -> gentle teardown hints -> rust removal -> primer -> paint -> polishing -> final reveal. "
            "Smooth continuous motion, realistic lighting, consistent geometry, no text, no logos, no watermark."
        )
        notes = str(extra_notes or "").strip()
        if notes:
            # Keep notes short to reduce provider failures.
            notes = textwrap.shorten(notes, width=220, placeholder="…")
            return f"{base} Extra notes (do not change model): {notes}"
        return base

    def _generate_vehicle_restoration_video_procedural(
        self,
        image_path: str,
        duration: int,
        fps: int,
        output_path: str,
        target_resolution: str = "1280x720",
        paint_hint: Optional[str] = None,
        intensity_hint: str = "medium",
    ) -> Dict[str, Any]:
        """Procedurally animate a restoration effect from a single photo.

        This produces a visually pleasing before->after restoration illusion using
        color grading, scratch/dust overlays, a wipe reveal, and a final polish pass.
        """
        try:
            _lazy_import_image_libs()
            _lazy_import_video_libs()
            if not IMAGE_LIBS_AVAILABLE or not VIDEO_LIBS_AVAILABLE:
                # Last resort fallback
                res = self.animate_image(
                    image_path=image_path,
                    duration=duration,
                    fps=fps,
                    zoom_factor=1.15,
                    pan_direction="center",
                    output_path=output_path,
                )
                if res.get("success") and res.get("video_path"):
                    name = Path(res["video_path"]).name
                    res["url"] = f"/media/videos/{name}"
                    res["download_url"] = f"/media/download/videos/{name}"
                    res["note"] = (
                        "Procedural restore fallback unavailable (missing Pillow/moviepy). "
                        "Used Ken Burns animation instead. Install Pillow + moviepy for a better restoration simulation."
                    )
                return res

            # Load and fit image
            img0 = Image.open(image_path).convert("RGB")
            tw, th = self._parse_resolution(target_resolution)
            fitted = self._fit_image_letterbox(img0, tw, th)

            # Precompute overlays
            scratches = self._make_scratches_overlay(tw, th)
            vignette = self._make_vignette_mask(tw, th)

            # Prepare "old" and "new" looks
            old_base = self._grade_old_photo(fitted)
            new_base = self._grade_restored_photo(fitted, paint_hint=paint_hint, intensity_hint=intensity_hint)

            total_frames = int(max(12, round(duration * fps)))
            frames = []

            for i in range(total_frames):
                t = 0.0 if total_frames <= 1 else (i / (total_frames - 1))

                # Smooth easing for nicer motion
                ease = self._ease_in_out(t)

                # Fade scratches/dust out over time
                scratch_alpha = int(max(0, min(255, round(220 * (1.0 - ease)))))

                # Build an in-between graded image
                graded = Image.blend(old_base, new_base, alpha=ease)

                # Wipe reveal: left remains older longer, right reveals restored
                wipe_start = 0.18
                wipe_end = 0.82
                wipe_t = 0.0
                if t <= wipe_start:
                    wipe_t = 0.0
                elif t >= wipe_end:
                    wipe_t = 1.0
                else:
                    wipe_t = (t - wipe_start) / (wipe_end - wipe_start)
                wipe_t = self._ease_in_out(wipe_t)
                wipe_x = int(tw * wipe_t)
                wipe_mask = Image.new("L", (tw, th), 0)
                draw = ImageDraw.Draw(wipe_mask)
                draw.rectangle([0, 0, max(0, wipe_x), th], fill=255)
                revealed = Image.composite(new_base, old_base, wipe_mask)
                base_frame = Image.blend(graded, revealed, alpha=0.55)

                # Apply vignette subtly
                base_frame = Image.composite(base_frame, Image.new("RGB", (tw, th), (8, 8, 12)), vignette)

                # Apply scratches overlay
                if scratch_alpha > 0:
                    sc = scratches.copy()
                    sc.putalpha(scratch_alpha)
                    base_frame = Image.alpha_composite(base_frame.convert("RGBA"), sc).convert("RGB")

                # Final polish: slight glow and sharpen near the end
                if t > 0.78:
                    polish = ImageEnhance.Contrast(base_frame).enhance(1.08)
                    polish = ImageEnhance.Color(polish).enhance(1.06)
                    base_frame = polish.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=3))

                frames.append(np.array(base_frame))

            clip = ImageSequenceClip(frames, fps=fps)
            clip.write_videofile(
                str(Path(output_path)),
                fps=fps,
                codec="libx264",
                audio=False,
                preset="medium",
                bitrate="6000k",
                threads=4,
                ffmpeg_params=["-crf", "20"],
                logger=None,
            )
            clip.close()

            outp = Path(output_path)
            name = outp.name
            return {
                "success": True,
                "video_path": str(outp),
                "url": f"/media/videos/{name}",
                "download_url": f"/media/download/videos/{name}",
                "source": "procedural",
                "duration": duration,
                "fps": fps,
                "resolution": f"{tw}x{th}",
                "note": "Procedural restoration simulation (identity-preserving). Configure REPLICATE_API_TOKEN / STABILITY_API_KEY for true AI motion if desired.",
            }
        except Exception as exc:
            import traceback
            return {"success": False, "error": str(exc), "traceback": traceback.format_exc()}

    def _fit_image_letterbox(self, img: "Image.Image", target_w: int, target_h: int) -> "Image.Image":
        """Resize while preserving aspect ratio, letterboxing to target size."""
        _lazy_import_image_libs()
        w, h = img.size
        if w <= 0 or h <= 0:
            return img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        scale = min(target_w / w, target_h / h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (target_w, target_h), (10, 10, 16))
        ox = (target_w - nw) // 2
        oy = (target_h - nh) // 2
        canvas.paste(resized, (ox, oy))
        return canvas

    def _make_vignette_mask(self, w: int, h: int) -> "Image.Image":
        """Create a soft vignette mask (L mode)."""
        _lazy_import_image_libs()
        # Radial gradient approximation: draw concentric ellipses
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        steps = 18
        for i in range(steps):
            # Outer -> inner (darker edges)
            pad_x = int((i / steps) * (w * 0.28))
            pad_y = int((i / steps) * (h * 0.28))
            val = int(255 * (i / steps))
            draw.ellipse([pad_x, pad_y, w - pad_x, h - pad_y], fill=val)
        # Invert so edges are darker when used as composite mask
        return ImageOps.invert(mask).point(lambda p: int(p * 0.6))

    def _make_scratches_overlay(self, w: int, h: int) -> "Image.Image":
        """Create an RGBA scratches/dust overlay."""
        _lazy_import_image_libs()
        # Noise base
        noise = Image.effect_noise((w, h), 40).convert("L")
        noise = noise.point(lambda p: 255 if p > 200 else 0)
        # Thin lines
        lines = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(lines)
        rng = random.Random(1337)
        for _ in range(140):
            x1 = rng.randint(0, w - 1)
            y1 = rng.randint(0, h - 1)
            x2 = min(w - 1, max(0, x1 + rng.randint(-120, 120)))
            y2 = min(h - 1, max(0, y1 + rng.randint(-40, 40)))
            col = rng.randint(140, 255)
            draw.line((x1, y1, x2, y2), fill=col, width=1)
        combined = ImageChops.lighter(noise, lines)
        rgba = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        rgba.putalpha(combined.point(lambda p: int(min(255, p * 0.75))))
        return rgba

    def _grade_old_photo(self, img: "Image.Image") -> "Image.Image":
        _lazy_import_image_libs()
        # Desaturate and warm (sepia-ish)
        x = ImageEnhance.Color(img).enhance(0.55)
        x = ImageEnhance.Contrast(x).enhance(0.92)
        x = ImageEnhance.Brightness(x).enhance(0.95)
        # Warm tint overlay
        tint = Image.new("RGB", img.size, (120, 92, 55))
        x = Image.blend(x, tint, alpha=0.18)
        # Slight blur/softness
        x = x.filter(ImageFilter.GaussianBlur(radius=0.6))
        return x

    def _grade_restored_photo(self, img: "Image.Image", paint_hint: Optional[str] = None, intensity_hint: str = "medium") -> "Image.Image":
        _lazy_import_image_libs()
        
        # Determine intensity multipliers
        sat_mult = 1.0
        con_mult = 1.0
        sharp_mult = 1.0
        
        if intensity_hint == "low":
            sat_mult = 0.9
            con_mult = 0.95
            sharp_mult = 0.9
        elif intensity_hint == "high":
            sat_mult = 1.2
            con_mult = 1.15
            sharp_mult = 1.3
            
        x = ImageEnhance.Color(img).enhance(1.15 * sat_mult)
        x = ImageEnhance.Contrast(x).enhance(1.12 * con_mult)
        x = ImageEnhance.Brightness(x).enhance(1.05)
        x = ImageEnhance.Sharpness(x).enhance(1.25 * sharp_mult)
        
        # Apply paint tint if requested (simple overlay)
        if paint_hint:
            # Map common color names to RGB
            colors = {
                "red": (200, 50, 50),
                "blue": (50, 50, 200),
                "green": (50, 200, 50),
                "yellow": (200, 200, 50),
                "black": (30, 30, 30),
                "white": (240, 240, 240),
                "silver": (192, 192, 192),
                "grey": (128, 128, 128),
                "gray": (128, 128, 128),
                "orange": (200, 100, 50),
                "purple": (128, 0, 128),
                "pink": (255, 192, 203),
                "gold": (255, 215, 0),
            }
            
            # Try to find a matching color
            target_color = None
            paint_lower = paint_hint.lower()
            for name, rgb in colors.items():
                if name in paint_lower:
                    target_color = rgb
                    break
            
            if target_color:
                # Create a solid color layer
                tint = Image.new("RGB", img.size, target_color)
                # Blend it in using a simple alpha blend for a subtle tint
                x = Image.blend(x, tint, alpha=0.15) 
                
        return x

    def _ease_in_out(self, t: float) -> float:
        t = max(0.0, min(1.0, float(t)))
        return t * t * (3.0 - 2.0 * t)

    def list_videos(self, directory: Optional[str] = None) -> Dict[str, Any]:
        """List all video files in a directory (defaults to media_outputs/videos)."""
        try:
            search_dir = Path(directory) if directory else self.video_output_dir
            if not search_dir.exists():
                return {"success": False, "error": f"Directory not found: {search_dir}"}
            
            video_extensions = {".mp4", ".avi", ".webm", ".mov", ".mkv", ".wmv", ".flv"}
            files = []
            for f in search_dir.iterdir():
                if f.suffix.lower() in video_extensions:
                    files.append({
                        "name": f.name,
                        "path": str(f),
                        "size_bytes": f.stat().st_size,
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                    })
            return {"success": True, "directory": str(search_dir), "videos": files, "count": len(files)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def play_media(self, file_path: str) -> Dict[str, Any]:
        """Open a media file with the default system player."""
        try:
            if not os.path.exists(file_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            import platform
            system = platform.system()
            if system == "Windows":
                os.startfile(file_path)
            elif system == "Darwin":
                subprocess.run(["open", file_path])
            else:
                subprocess.run(["xdg-open", file_path])
            return {"success": True, "message": f"Opened {file_path} with default player"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def generate_video_local_comfy(
        self,
        image_path: str,
        duration: int = 4,
        motion_bucket_id: int = 127,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate video using local ComfyUI instance (Open Source).
        Requires ComfyUI to be running on port 8188 and SVD model installed.
        """
        try:
            # Lazy import helpers
            sys.path.append(str(Path(__file__).parent))
            from comfy_client import ComfyClient
            from video_workflows import get_svd_workflow
            
            if not os.path.exists(image_path):
                return {"success": False, "error": f"Image not found: {image_path}"}

            # Check if ComfyUI is running
            client = ComfyClient()
            try:
                client.connect()
                client.close()
            except Exception:
                return {
                    "success": False, 
                    "error": "ComfyUI is not running on 127.0.0.1:8188. Please start it first."
                }

            # Prepare output path
            output_file = (
                Path(output_path)
                if output_path
                else self.video_output_dir / f"comfy_svd_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.webp"
            )
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Get workflow
            # Note: ComfyUI needs absolute path for LoadImage if not in input dir
            # But standard LoadImage only looks in input dir.
            # We should copy image to ComfyUI input folder.
            comfy_root = Path(__file__).parent.parent.parent / "external" / "ComfyUI"
            comfy_input = comfy_root / "input"
            if comfy_input.exists():
                temp_name = f"temp_svd_{uuid.uuid4()}.png"
                temp_input_path = comfy_input / temp_name
                shutil.copy(image_path, temp_input_path)
                image_input_name = temp_name
            else:
                # Fallback to absolute path (might fail on some Comfy setups)
                image_input_name = str(Path(image_path).resolve())

            workflow = get_svd_workflow(
                image_path=image_input_name,
                motion_bucket_id=motion_bucket_id
            )

            print("[MediaTools] Sending workflow to ComfyUI...")
            result = client.generate(workflow)
            
            if not result.get("success"):
                return result

            # Retrieve output
            # ComfyUI saves to its output folder. We need to find it.
            # The client.generate returns 'outputs' which contains filenames.
            outputs = result.get("outputs", {})
            
            # Look for gifs or images (SVD usually saves as webp/gif/mp4)
            found_file = None
            
            # Check for 'images' (SaveAnimatedWEBP outputs as images type usually)
            if 'images' in outputs:
                for img in outputs['images']:
                    fname = img['filename']
                    subfolder = img['subfolder']
                    # Construct path
                    comfy_output = comfy_root / "output" / subfolder / fname
                    if comfy_output.exists():
                        found_file = comfy_output
                        break
            
            if found_file:
                # Move/Copy to our output dir
                shutil.copy(found_file, output_file)
                
                # If it's webp, we might want to convert to mp4
                final_path = str(output_file)
                if str(output_file).endswith(".webp"):
                    mp4_path = str(output_file).replace(".webp", ".mp4")
                    conv_res = self.convert_video(str(output_file), "mp4", mp4_path)
                    if conv_res.get("success"):
                        final_path = conv_res["output_path"]
                
                return {
                    "success": True,
                    "video_path": final_path,
                    "source": "comfyui_local",
                    "model": "svd_xt"
                }
            else:
                return {"success": False, "error": "Could not locate output file from ComfyUI"}

        except Exception as exc:
            return {"success": False, "error": str(exc)}


media = MediaTools()
