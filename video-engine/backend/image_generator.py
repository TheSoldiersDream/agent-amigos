"""
Image Generator - Generate keyframe images for video
Uses free/open-source APIs: Pollinations, Replicate, Local SDXL
"""
import os
import base64
import urllib.request
import urllib.parse
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from backend.config import settings, OUTPUT_DIR


class ImageGenerator:
    """Generate keyframe images using various APIs"""
    
    def __init__(self):
        self.output_dir = OUTPUT_DIR / "images"
        self.output_dir.mkdir(exist_ok=True)
    
    async def generate_keyframe(
        self,
        prompt: str,
        style: str = "cinematic",
        resolution: str = "1024x1024",
        model: str = "auto"
    ) -> Dict[str, Any]:
        """
        Generate a keyframe image from a text prompt
        
        Args:
            prompt: Text description of the image
            style: Visual style (cinematic, anime, realistic, etc.)
            resolution: Output resolution (e.g., "1024x1024")
            model: Model to use (auto, pollinations, openai, sdxl)
        """
        # Parse resolution
        try:
            width, height = map(int, resolution.lower().split("x"))
        except:
            width, height = 1024, 1024
        
        # Add style modifiers to prompt
        styled_prompt = self._add_style(prompt, style)
        
        logger.info(f"Generating keyframe: {styled_prompt[:50]}... ({width}x{height})")
        
        # Try different methods based on model preference
        if model == "auto":
            # Try in order of preference
            methods = [
                ("pollinations", self._generate_pollinations),
                ("openai", self._generate_openai),
                ("replicate", self._generate_replicate),
            ]
        else:
            methods = [(model, getattr(self, f"_generate_{model}", None))]
        
        errors = []
        for method_name, method in methods:
            if method is None:
                continue
            
            try:
                result = await method(styled_prompt, width, height)
                if result.get("success"):
                    logger.info(f"Keyframe generated with {method_name}")
                    return result
                errors.append(f"{method_name}: {result.get('error', 'Unknown error')}")
            except Exception as e:
                errors.append(f"{method_name}: {str(e)}")
        
        # Fallback to placeholder
        logger.warning(f"All image APIs failed, using placeholder. Errors: {errors}")
        return await self._generate_placeholder(styled_prompt, width, height)
    
    def _add_style(self, prompt: str, style: str) -> str:
        """Add style modifiers to prompt"""
        style_modifiers = {
            "cinematic": ", cinematic lighting, dramatic, 8k, film grain, professional photography",
            "anime": ", anime style, vibrant colors, studio ghibli, detailed anime art",
            "realistic": ", photorealistic, hyperdetailed, 8k uhd, professional photo",
            "artistic": ", artistic, painterly, digital art, concept art, trending on artstation",
            "3d": ", 3d render, octane render, unreal engine, highly detailed",
            "fantasy": ", fantasy art, magical, ethereal lighting, epic scene",
            "scifi": ", sci-fi, futuristic, neon lights, cyberpunk",
            "military": ", military, tactical, realistic, high detail, dramatic lighting",
            "nature": ", nature photography, golden hour, serene, beautiful landscape",
        }
        
        modifier = style_modifiers.get(style, style_modifiers["cinematic"])
        return prompt.strip() + modifier
    
    async def _generate_pollinations(self, prompt: str, width: int, height: int) -> Dict[str, Any]:
        """Use Pollinations.ai - FREE, no API key needed"""
        import ssl
        import random
        
        # Clamp dimensions to Pollinations limits
        width = min(max(256, width), 2048)
        height = min(max(256, height), 2048)
        
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Use safe URL encoding
                encoded_prompt = urllib.parse.quote(prompt, safe='')
                seed = random.randint(1, 999999)
                url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={seed}"
                
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                filename = self.output_dir / f"keyframe_{timestamp}.png"
                
                # Create SSL context that handles certificate issues
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'image/png,image/*,*/*',
                })
                
                # Download with longer timeout (image generation can take time)
                loop = asyncio.get_event_loop()
                
                def download_image():
                    with urllib.request.urlopen(req, timeout=120, context=ctx) as response:
                        return response.read()
                
                image_data = await loop.run_in_executor(None, download_image)
                
                with open(filename, 'wb') as f:
                    f.write(image_data)
                
                # Verify file size and PNG signature
                file_size = filename.stat().st_size
                if file_size < 1000:
                    filename.unlink()
                    last_error = f"Generated image too small ({file_size} bytes)"
                    continue
                
                # Verify PNG header
                with open(filename, 'rb') as f:
                    if f.read(4) != b'\x89PNG':
                        filename.unlink()
                        last_error = "Response was not a valid PNG"
                        continue
                
                logger.info(f"Pollinations keyframe generated: {filename}")
                return {
                    "success": True,
                    "image_path": str(filename),
                    "method": "pollinations",
                    "resolution": f"{width}x{height}"
                }
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Pollinations attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 * (attempt + 1))
                continue
        
        return {"success": False, "error": last_error or "Unknown error"}
    
    async def _generate_openai(self, prompt: str, width: int, height: int) -> Dict[str, Any]:
        """Use OpenAI DALL-E (requires API key)"""
        if not settings.OPENAI_KEY:
            return {"success": False, "error": "OPENAI_KEY not configured"}
        
        try:
            # Map to supported sizes
            size = "1024x1024"
            if width > height:
                size = "1792x1024"
            elif height > width:
                size = "1024x1792"
            
            headers = {
                "Authorization": f"Bearer {settings.OPENAI_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": size,
                "quality": "standard"
            }
            
            req = urllib.request.Request(
                "https://api.openai.com/v1/images/generations",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=60)
            )
            result = json.loads(response.read().decode("utf-8"))
            
            image_url = result["data"][0]["url"]
            
            # Download image
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = self.output_dir / f"keyframe_{timestamp}.png"
            
            await loop.run_in_executor(
                None,
                lambda: urllib.request.urlretrieve(image_url, str(filename))
            )
            
            return {
                "success": True,
                "image_path": str(filename),
                "method": "openai",
                "resolution": size
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_replicate(self, prompt: str, width: int, height: int) -> Dict[str, Any]:
        """Use Replicate SDXL (requires API key)"""
        if not settings.REPLICATE_API_TOKEN:
            return {"success": False, "error": "REPLICATE_API_TOKEN not configured"}
        
        try:
            headers = {
                "Authorization": f"Token {settings.REPLICATE_API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # SDXL model
            payload = {
                "version": "39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                "input": {
                    "prompt": prompt,
                    "width": min(width, 1024),
                    "height": min(height, 1024),
                    "num_inference_steps": 25,
                    "guidance_scale": 7.5
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
                return {"success": False, "error": "No prediction ID"}
            
            # Poll for completion
            for _ in range(60):
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
                
                if status_result.get("status") == "succeeded":
                    output = status_result.get("output")
                    if output:
                        image_url = output[0] if isinstance(output, list) else output
                        
                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                        filename = self.output_dir / f"keyframe_{timestamp}.png"
                        
                        await loop.run_in_executor(
                            None,
                            lambda: urllib.request.urlretrieve(image_url, str(filename))
                        )
                        
                        return {
                            "success": True,
                            "image_path": str(filename),
                            "method": "replicate",
                            "resolution": f"{width}x{height}"
                        }
                
                elif status_result.get("status") == "failed":
                    return {"success": False, "error": status_result.get("error", "Generation failed")}
            
            return {"success": False, "error": "Timeout waiting for image"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_placeholder(self, prompt: str, width: int, height: int) -> Dict[str, Any]:
        """Generate a placeholder image with text"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import textwrap
            
            # Create gradient background
            img = Image.new('RGB', (width, height), color=(30, 30, 50))
            draw = ImageDraw.Draw(img)
            
            # Add gradient effect
            for y in range(height):
                r = int(30 + (y / height) * 20)
                g = int(30 + (y / height) * 10)
                b = int(50 + (y / height) * 30)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            
            # Add text
            try:
                font = ImageFont.truetype("arial.ttf", 32)
            except:
                font = ImageFont.load_default()
            
            # Wrap text
            wrapped = textwrap.fill(prompt[:100], width=40)
            
            # Center text
            bbox = draw.textbbox((0, 0), wrapped, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            draw.text((x, y), wrapped, fill=(200, 200, 220), font=font)
            
            # Add border
            draw.rectangle([(10, 10), (width-10, height-10)], outline=(100, 100, 150), width=2)
            
            # Add "Agent Amigos" watermark
            draw.text((20, height - 40), "Agent Amigos - Placeholder", fill=(80, 80, 100), font=font)
            
            # Save
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = self.output_dir / f"keyframe_{timestamp}.png"
            img.save(str(filename), quality=95)
            
            return {
                "success": True,
                "image_path": str(filename),
                "method": "placeholder",
                "resolution": f"{width}x{height}",
                "note": "Placeholder image - API keys not configured"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Placeholder generation failed: {e}"}
    
    async def generate_batch(self, prompts: list, style: str = "cinematic", resolution: str = "1024x1024") -> list:
        """Generate multiple keyframes in parallel"""
        tasks = [
            self.generate_keyframe(prompt, style, resolution)
            for prompt in prompts
        ]
        return await asyncio.gather(*tasks)
