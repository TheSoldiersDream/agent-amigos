"""Text-to-Speech (TTS) tools for voiceover generation in faceless videos."""
from __future__ import annotations

import os
import subprocess
import json
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class TTSTools:
    """Text-to-Speech generation for high-quality voiceovers."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize TTS tools.
        
        Args:
            output_dir: Directory to save generated audio files
        """
        self.output_dir = output_dir or Path(__file__).parent.parent / "media_outputs" / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_voiceover(
        self,
        script: str,
        voice_style: str = "authoritative",
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate voiceover from script with multiple TTS fallbacks.
        
        Tries in order:
        1. ElevenLabs API (best quality, requires API key)
        2. Google Cloud TTS (good quality, requires credentials)
        3. Edge TTS (free, good quality, no API key required)
        4. Piper TTS (local, fast, no internet required)
        
        Args:
            script: Text to convert to speech
            voice_style: Style of voice (authoritative, friendly, professional, casual)
            output_path: Optional custom output path
            
        Returns:
            Dict with success status, audio_path, and metadata
        """
        if not script or not script.strip():
            return {"success": False, "error": "Script text is required"}
        
        output_file = (
            Path(output_path)
            if output_path
            else self.output_dir / f"voiceover_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp3"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        errors = []
        
        # Try Method 1: ElevenLabs API (premium quality)
        elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
        if elevenlabs_key:
            result = self._generate_with_elevenlabs(script, voice_style, str(output_file), elevenlabs_key)
            if result.get("success"):
                logger.info("[TTS] ✓ ElevenLabs succeeded")
                return result
            errors.append(f"ElevenLabs: {result.get('error', 'Unknown')}")
        
        # Try Method 2: Edge TTS (free, high quality)
        result = self._generate_with_edge_tts(script, voice_style, str(output_file))
        if result.get("success"):
            logger.info("[TTS] ✓ Edge TTS succeeded")
            return result
        errors.append(f"Edge TTS: {result.get('error', 'Unknown')}")
        
        # Try Method 3: Google Cloud TTS (if credentials available)
        google_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if google_creds and Path(google_creds).exists():
            result = self._generate_with_google_tts(script, voice_style, str(output_file))
            if result.get("success"):
                logger.info("[TTS] ✓ Google TTS succeeded")
                return result
            errors.append(f"Google TTS: {result.get('error', 'Unknown')}")
        
        # Try Method 4: Piper TTS (local fallback)
        result = self._generate_with_piper(script, voice_style, str(output_file))
        if result.get("success"):
            logger.info("[TTS] ✓ Piper TTS succeeded")
            return result
        errors.append(f"Piper: {result.get('error', 'Unknown')}")
        
        logger.error(f"[TTS] All methods failed: {errors}")
        return {
            "success": False,
            "error": "All TTS methods failed. Install edge-tts or piper for reliable voiceover generation.",
            "provider_errors": errors,
        }
    
    def _generate_with_elevenlabs(
        self, text: str, voice_style: str, output_path: str, api_key: str
    ) -> Dict[str, Any]:
        """Generate with ElevenLabs API (premium quality)."""
        try:
            import requests
            
            # Map voice styles to ElevenLabs voice IDs
            voice_map = {
                "authoritative": "pNInz6obpgDQGcFmaJgB",  # Adam (deep, authoritative)
                "professional": "21m00Tcm4TlvDq8ikWAM",  # Rachel (professional)
                "friendly": "AZnzlk1XvdvUeBnXmlld",      # Domi (friendly)
                "casual": "EXAVITQu4vr4xnSDxMaL",        # Sarah (casual)
            }
            voice_id = voice_map.get(voice_style, voice_map["authoritative"])
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": api_key
            }
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.75,
                    "similarity_boost": 0.75
                }
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=60)
            
            if response.status_code == 200:
                Path(output_path).write_bytes(response.content)
                return {
                    "success": True,
                    "audio_path": output_path,
                    "provider": "elevenlabs",
                    "voice_id": voice_id,
                    "voice_style": voice_style,
                }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_with_edge_tts(
        self, text: str, voice_style: str, output_path: str
    ) -> Dict[str, Any]:
        """Generate with Edge TTS (free, high quality, no API key required)."""
        try:
            # Check if edge-tts is installed
            result = subprocess.run(["edge-tts", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return {"success": False, "error": "edge-tts not installed. Install: pip install edge-tts"}
            
            # Map voice styles to Edge TTS voices
            voice_map = {
                "authoritative": "en-US-GuyNeural",          # Deep male voice
                "professional": "en-US-JennyNeural",         # Professional female
                "friendly": "en-US-AriaNeural",              # Friendly female
                "casual": "en-US-ChristopherNeural",         # Casual male
            }
            voice = voice_map.get(voice_style, voice_map["authoritative"])
            
            # Run edge-tts command
            cmd = [
                "edge-tts",
                "--voice", voice,
                "--text", text,
                "--write-media", output_path,
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and Path(output_path).exists():
                return {
                    "success": True,
                    "audio_path": output_path,
                    "provider": "edge_tts",
                    "voice": voice,
                    "voice_style": voice_style,
                }
            else:
                return {"success": False, "error": f"edge-tts failed: {result.stderr[:200]}"}
        except FileNotFoundError:
            return {"success": False, "error": "edge-tts not installed. Install: pip install edge-tts"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_with_google_tts(
        self, text: str, voice_style: str, output_path: str
    ) -> Dict[str, Any]:
        """Generate with Google Cloud TTS (requires credentials)."""
        try:
            from google.cloud import texttospeech
            
            client = texttospeech.TextToSpeechClient()
            
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Map voice styles to Google voices
            voice_map = {
                "authoritative": ("en-US-Neural2-D", texttospeech.SsmlVoiceGender.MALE),
                "professional": ("en-US-Neural2-F", texttospeech.SsmlVoiceGender.FEMALE),
                "friendly": ("en-US-Neural2-C", texttospeech.SsmlVoiceGender.FEMALE),
                "casual": ("en-US-Neural2-A", texttospeech.SsmlVoiceGender.MALE),
            }
            voice_name, gender = voice_map.get(voice_style, voice_map["authoritative"])
            
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice_name,
                ssml_gender=gender
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0
            )
            
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            Path(output_path).write_bytes(response.audio_content)
            
            return {
                "success": True,
                "audio_path": output_path,
                "provider": "google_tts",
                "voice_name": voice_name,
                "voice_style": voice_style,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_with_piper(
        self, text: str, voice_style: str, output_path: str
    ) -> Dict[str, Any]:
        """Generate with Piper TTS (local, fast)."""
        try:
            # Check if piper is installed
            result = subprocess.run(["piper", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return {"success": False, "error": "piper not installed. Install from: https://github.com/rhasspy/piper"}
            
            # Piper uses ONNX models - user needs to download them
            # Default model path (user-configurable via env var)
            model_dir = Path(os.environ.get("PIPER_MODELS_DIR", str(Path.home() / ".local/share/piper/models")))
            model_name = "en_US-lessac-medium.onnx"  # High quality English model
            model_path = model_dir / model_name
            
            if not model_path.exists():
                return {
                    "success": False,
                    "error": f"Piper model not found at {model_path}. Download from: https://github.com/rhasspy/piper/releases"
                }
            
            # Generate audio
            cmd = [
                "piper",
                "--model", str(model_path),
                "--output_file", output_path,
            ]
            
            result = subprocess.run(
                cmd,
                input=text.encode('utf-8'),
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0 and Path(output_path).exists():
                return {
                    "success": True,
                    "audio_path": output_path,
                    "provider": "piper",
                    "model": model_name,
                    "voice_style": voice_style,
                }
            else:
                return {"success": False, "error": f"piper failed: {result.stderr.decode('utf-8')[:200]}"}
        except FileNotFoundError:
            return {"success": False, "error": "piper not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def split_audio_by_timings(
        self,
        audio_path: str,
        timings: List[Dict[str, float]],
        output_dir: str
    ) -> List[Dict[str, Any]]:
        """Split audio file into segments based on timing information.
        
        Args:
            audio_path: Path to full voiceover audio file
            timings: List of dicts with 'start' and 'end' times in seconds
            output_dir: Directory to save audio segments
            
        Returns:
            List of dicts with segment paths and metadata
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        segments = []
        
        try:
            for idx, timing in enumerate(timings):
                start = timing.get("start", 0)
                end = timing.get("end", 0)
                duration = end - start
                
                if duration <= 0:
                    continue
                
                segment_path = output_path / f"segment_{idx+1:02d}.mp3"
                
                # Use ffmpeg to extract segment
                cmd = [
                    "ffmpeg",
                    "-i", audio_path,
                    "-ss", str(start),
                    "-t", str(duration),
                    "-c", "copy",
                    "-y",
                    str(segment_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                
                if result.returncode == 0 and segment_path.exists():
                    segments.append({
                        "segment_id": idx + 1,
                        "path": str(segment_path),
                        "start": start,
                        "end": end,
                        "duration": duration
                    })
                else:
                    logger.warning(f"Failed to extract segment {idx+1}: {result.stderr.decode('utf-8')[:100]}")
                    
        except Exception as e:
            logger.error(f"Audio splitting failed: {e}")
        
        return segments


# Global instance
tts_tools = TTSTools()
