"""
Recording Tools Module - Screen and Audio Recording for Social Media Content
Record conversations with Agent Amigos for TikTok, YouTube, Instagram Reels
"""
import os
import subprocess
import time
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Output directories
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_DIR = os.path.join(BACKEND_DIR, "media_outputs")
RECORDINGS_DIR = os.path.join(MEDIA_DIR, "recordings")
AUDIO_DIR = os.path.join(MEDIA_DIR, "audio")

# Ensure directories exist
os.makedirs(RECORDINGS_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)


class RecordingTools:
    """Screen and audio recording for social media content creation"""
    
    def __init__(self):
        self._recording_process = None
        self._audio_process = None
        self._is_recording = False
        self._recording_start_time = None
        self._current_recording_file = None
        self._ffmpeg_path = self._find_ffmpeg()
        self._audio_device = None  # Will be auto-detected
    
    def _find_ffmpeg(self) -> Optional[str]:
        """Find FFmpeg in system PATH or common locations"""
        # Check PATH
        try:
            result = subprocess.run(["where", "ffmpeg"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        # Common Windows locations
        common_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\tools\ffmpeg\bin\ffmpeg.exe",
            os.path.expanduser(r"~\ffmpeg\bin\ffmpeg.exe"),
            # WinGet installed location
            os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # Also search WinGet packages dynamically
        winget_packages = os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages")
        if os.path.exists(winget_packages):
            for root, dirs, files in os.walk(winget_packages):
                if "ffmpeg.exe" in files:
                    return os.path.join(root, "ffmpeg.exe")
        
        return None
    
    def check_ffmpeg(self) -> Dict[str, Any]:
        """Check if FFmpeg is installed and available"""
        if self._ffmpeg_path:
            try:
                result = subprocess.run([self._ffmpeg_path, "-version"], 
                                       capture_output=True, text=True, timeout=5)
                version = result.stdout.split('\n')[0] if result.returncode == 0 else "Unknown"
                return {
                    "success": True,
                    "installed": True,
                    "path": self._ffmpeg_path,
                    "version": version
                }
            except:
                pass
        
        return {
            "success": True,
            "installed": False,
            "message": "FFmpeg not found. Install from https://ffmpeg.org/download.html",
            "install_command": "winget install FFmpeg"
        }
    
    def _get_audio_device(self) -> Optional[str]:
        """Auto-detect the first available audio input device"""
        if self._audio_device:
            return self._audio_device
            
        if not self._ffmpeg_path:
            return None
            
        try:
            # Run ffmpeg to list devices
            result = subprocess.run(
                [self._ffmpeg_path, "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                capture_output=True,
                timeout=10,
                encoding='utf-8',
                errors='replace'
            )
            
            # Parse audio devices from stderr - look for (audio) markers
            stderr = result.stderr
            for line in stderr.split('\n'):
                # Look for lines with (audio) at the end
                if '(audio)' in line and '"' in line:
                    # Extract device name between first and last quote before (audio)
                    audio_pos = line.find('(audio)')
                    line_before_audio = line[:audio_pos]
                    start = line_before_audio.find('"') + 1
                    end = line_before_audio.rfind('"')
                    if start > 0 and end > start:
                        device_name = line_before_audio[start:end]
                        if device_name and len(device_name) > 2:
                            self._audio_device = device_name
                            return device_name
        except Exception as e:
            print(f"Audio device detection error: {e}")
        
        return None
    
    def start_screen_recording(self, 
                               filename: Optional[str] = None,
                               include_audio: bool = True,
                               fps: int = 30,
                               quality: str = "medium") -> Dict[str, Any]:
        """
        Start screen recording using FFmpeg
        
        Args:
            filename: Output filename (auto-generated if not provided)
            include_audio: Include system audio in recording
            fps: Frames per second (15, 24, 30, 60)
            quality: Recording quality (low, medium, high)
        """
        if self._is_recording:
            return {"success": False, "error": "Already recording"}
        
        if not self._ffmpeg_path:
            return {
                "success": False, 
                "error": "FFmpeg not installed",
                "install": "Run: winget install FFmpeg"
            }
        
        # Generate filename
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"amigos_recording_{timestamp}.mp4"
        
        if not filename.endswith('.mp4'):
            filename += '.mp4'
        
        output_path = os.path.join(RECORDINGS_DIR, filename)
        
        # Quality presets
        quality_settings = {
            "low": {"crf": "28", "preset": "ultrafast"},
            "medium": {"crf": "23", "preset": "fast"},
            "high": {"crf": "18", "preset": "medium"}
        }
        settings = quality_settings.get(quality, quality_settings["medium"])
        
        # Build FFmpeg command for Windows screen capture
        cmd = [
            self._ffmpeg_path,
            "-y",  # Overwrite output
            "-f", "gdigrab",  # Windows screen capture
            "-framerate", str(fps),
            "-i", "desktop",  # Capture entire desktop
        ]
        
        # Add audio capture if requested - auto-detect device
        audio_device = None
        if include_audio:
            audio_device = self._get_audio_device()
            if audio_device:
                cmd.extend([
                    "-f", "dshow",
                    "-i", f"audio={audio_device}",
                ])
            else:
                # No audio device found, record without audio
                include_audio = False
        
        # Output settings
        cmd.extend([
            "-c:v", "libx264",
            "-crf", settings["crf"],
            "-preset", settings["preset"],
            "-pix_fmt", "yuv420p",
        ])
        
        if include_audio and audio_device:
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        
        cmd.append(output_path)
        
        try:
            # Start recording in background
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            # Use binary mode for stdin (to send 'q' command)
            self._recording_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo
            )
            
            self._is_recording = True
            self._recording_start_time = time.time()
            self._current_recording_file = output_path
            
            return {
                "success": True,
                "message": "Screen recording started" + (f" with audio ({audio_device})" if audio_device else " (no audio)"),
                "filename": filename,
                "path": output_path,
                "fps": fps,
                "quality": quality,
                "audio": include_audio,
                "audio_device": audio_device
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def stop_screen_recording(self) -> Dict[str, Any]:
        """Stop the current screen recording"""
        if not self._is_recording or not self._recording_process:
            return {"success": False, "error": "No recording in progress"}
        
        try:
            duration = time.time() - self._recording_start_time
            output_file = self._current_recording_file
            
            # Try multiple methods to stop FFmpeg gracefully
            # Method 1: Send 'q' to stdin (graceful stop) - binary mode
            try:
                if self._recording_process.stdin:
                    self._recording_process.stdin.write(b'q')
                    self._recording_process.stdin.flush()
                    self._recording_process.stdin.close()
            except:
                pass
            
            # Wait a bit for graceful shutdown
            try:
                self._recording_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Method 2: Terminate the process
                try:
                    self._recording_process.terminate()
                    self._recording_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # Method 3: Force kill
                    self._recording_process.kill()
                    self._recording_process.wait(timeout=2)
            
            # Reset state
            self._is_recording = False
            self._recording_process = None
            self._recording_start_time = None
            self._current_recording_file = None
            
            # Give filesystem a moment to flush
            time.sleep(0.5)
            
            # Check if file was created
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                if file_size > 0:
                    return {
                        "success": True,
                        "message": "Recording saved",
                        "path": output_file,
                        "filename": os.path.basename(output_file),
                        "duration_seconds": round(duration, 1),
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "url": f"/media/recordings/{os.path.basename(output_file)}"
                    }
                else:
                    return {"success": False, "error": "Recording file is empty"}
            else:
                return {"success": False, "error": "Recording file not created"}
                
        except Exception as e:
            self._is_recording = False
            self._recording_process = None
            return {"success": False, "error": str(e)}
    
    def get_recording_status(self) -> Dict[str, Any]:
        """Get current recording status"""
        if self._is_recording:
            duration = time.time() - self._recording_start_time
            return {
                "success": True,
                "is_recording": True,
                "duration_seconds": round(duration, 1),
                "filename": os.path.basename(self._current_recording_file) if self._current_recording_file else None
            }
        return {
            "success": True,
            "is_recording": False
        }
    
    def start_audio_recording(self, 
                              filename: Optional[str] = None,
                              format: str = "mp3",
                              sample_rate: int = 44100) -> Dict[str, Any]:
        """
        Start audio-only recording (microphone)
        
        Args:
            filename: Output filename
            format: Audio format (mp3, wav)
            sample_rate: Sample rate in Hz
        """
        if not self._ffmpeg_path:
            return {"success": False, "error": "FFmpeg not installed"}
        
        # Auto-detect audio device
        audio_device = self._get_audio_device()
        if not audio_device:
            return {"success": False, "error": "No audio input device found"}
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"voice_recording_{timestamp}.{format}"
        
        output_path = os.path.join(AUDIO_DIR, filename)
        
        # FFmpeg command for microphone recording with auto-detected device
        cmd = [
            self._ffmpeg_path,
            "-y",
            "-f", "dshow",
            "-i", f"audio={audio_device}",
            "-ar", str(sample_rate),
        ]
        
        if format == "mp3":
            cmd.extend(["-c:a", "libmp3lame", "-b:a", "192k"])
        else:
            cmd.extend(["-c:a", "pcm_s16le"])
        
        cmd.append(output_path)
        
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            self._audio_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo
            )
            
            return {
                "success": True,
                "message": "Audio recording started",
                "filename": filename,
                "path": output_path
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def stop_audio_recording(self) -> Dict[str, Any]:
        """Stop audio recording"""
        if not self._audio_process:
            return {"success": False, "error": "No audio recording in progress"}
        
        try:
            # Try graceful shutdown first - binary mode
            try:
                if self._audio_process.stdin:
                    self._audio_process.stdin.write(b'q')
                    self._audio_process.stdin.flush()
                    self._audio_process.stdin.close()
            except:
                pass
            
            try:
                self._audio_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    self._audio_process.terminate()
                    self._audio_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._audio_process.kill()
                    self._audio_process.wait(timeout=1)
            
            self._audio_process = None
            return {"success": True, "message": "Audio recording stopped"}
        except Exception as e:
            self._audio_process = None
            return {"success": False, "error": str(e)}
    
    def list_recordings(self) -> Dict[str, Any]:
        """List all screen recordings"""
        recordings = []
        
        if os.path.exists(RECORDINGS_DIR):
            for f in os.listdir(RECORDINGS_DIR):
                if f.endswith(('.mp4', '.mkv', '.avi', '.webm')):
                    path = os.path.join(RECORDINGS_DIR, f)
                    stat = os.stat(path)
                    recordings.append({
                        "filename": f,
                        "path": path,
                        "url": f"/media/recordings/{f}",
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
                    })
        
        return {
            "success": True,
            "count": len(recordings),
            "recordings": sorted(recordings, key=lambda x: x["created"], reverse=True)
        }
    
    def list_audio_devices(self) -> Dict[str, Any]:
        """List available audio devices"""
        if not self._ffmpeg_path:
            return {"success": False, "error": "FFmpeg not installed"}
        
        try:
            result = subprocess.run(
                [self._ffmpeg_path, "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                capture_output=True,
                timeout=10,
                encoding='utf-8',
                errors='replace'
            )
            
            # Parse device list from stderr - look for (audio) and (video) markers
            devices = {"audio": [], "video": []}
            
            for line in result.stderr.split('\n'):
                if '"' in line and 'Alternative name' not in line:
                    # Check if audio or video device
                    if '(audio)' in line:
                        device_type = 'audio'
                        marker_pos = line.find('(audio)')
                    elif '(video)' in line:
                        device_type = 'video'
                        marker_pos = line.find('(video)')
                    else:
                        continue
                    
                    # Extract device name between quotes before the marker
                    line_before_marker = line[:marker_pos]
                    start = line_before_marker.find('"') + 1
                    end = line_before_marker.rfind('"')
                    if start > 0 and end > start:
                        device_name = line_before_marker[start:end]
                        if device_name:
                            devices[device_type].append(device_name)
            
            return {"success": True, "devices": devices}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def record_window(self, 
                      window_title: str,
                      filename: Optional[str] = None,
                      duration: Optional[int] = None) -> Dict[str, Any]:
        """
        Record a specific window by title
        
        Args:
            window_title: Title of window to record (e.g., "Agent Amigos")
            filename: Output filename
            duration: Recording duration in seconds (None = manual stop)
        """
        if not self._ffmpeg_path:
            return {"success": False, "error": "FFmpeg not installed"}
        
        if not filename:
            safe_title = "".join(c for c in window_title if c.isalnum() or c in "_ -")[:30]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_title}_{timestamp}.mp4"
        
        output_path = os.path.join(RECORDINGS_DIR, filename)
        
        cmd = [
            self._ffmpeg_path,
            "-y",
            "-f", "gdigrab",
            "-framerate", "30",
            "-i", f"title={window_title}",
            "-c:v", "libx264",
            "-crf", "23",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
        ]
        
        if duration:
            cmd.extend(["-t", str(duration)])
        
        cmd.append(output_path)
        
        try:
            if duration:
                # Run with timeout for fixed duration
                result = subprocess.run(cmd, capture_output=True, timeout=duration + 10)
                return {
                    "success": True,
                    "path": output_path,
                    "filename": filename,
                    "duration": duration
                }
            else:
                # Start background recording
                self._recording_process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                self._is_recording = True
                self._recording_start_time = time.time()
                self._current_recording_file = output_path
                
                return {
                    "success": True,
                    "message": f"Recording window: {window_title}",
                    "filename": filename
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
recording = RecordingTools()
