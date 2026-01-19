"""
Voice Tools Module - Audio Recording & Processing
Record, playback, transcribe, and process voice recordings
"""
import os
import wave
import json
import threading
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Audio recording
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

# Audio processing
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

# Speech recognition
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False


class VoiceTools:
    """Voice recording and processing tools"""
    
    def __init__(self):
        self.backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.recordings_dir = os.path.join(self.backend_dir, "media_outputs", "recordings")
        os.makedirs(self.recordings_dir, exist_ok=True)
        
        # Recording state
        self._is_recording = False
        self._recording_thread = None
        self._frames = []
        self._current_recording_path = None
        
        # Audio settings
        self.sample_rate = 44100
        self.channels = 1
        self.chunk_size = 1024
        self.format = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None
        
        # Speech recognizer
        self.recognizer = sr.Recognizer() if SR_AVAILABLE else None
    
    def check_dependencies(self) -> Dict[str, Any]:
        """Check if required audio libraries are installed"""
        return {
            "success": True,
            "dependencies": {
                "pyaudio": PYAUDIO_AVAILABLE,
                "pydub": PYDUB_AVAILABLE,
                "speech_recognition": SR_AVAILABLE
            },
            "missing": [
                dep for dep, available in [
                    ("pyaudio", PYAUDIO_AVAILABLE),
                    ("pydub", PYDUB_AVAILABLE),
                    ("speech_recognition", SR_AVAILABLE)
                ] if not available
            ],
            "install_command": "pip install pyaudio pydub SpeechRecognition"
        }
    
    def start_recording(self, filename: Optional[str] = None, max_duration: int = 300) -> Dict[str, Any]:
        """Start recording audio from microphone
        
        Args:
            filename: Optional filename (auto-generated if not provided)
            max_duration: Maximum recording duration in seconds (default 5 minutes)
        """
        if not PYAUDIO_AVAILABLE:
            return {"success": False, "error": "pyaudio not installed. Run: pip install pyaudio"}
        
        if self._is_recording:
            return {"success": False, "error": "Already recording. Stop current recording first."}
        
        # Generate filename
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"
        
        if not filename.endswith('.wav'):
            filename += '.wav'
        
        self._current_recording_path = os.path.join(self.recordings_dir, filename)
        self._frames = []
        self._is_recording = True
        
        # Start recording in background thread
        self._recording_thread = threading.Thread(
            target=self._record_audio,
            args=(max_duration,),
            daemon=True
        )
        self._recording_thread.start()
        
        return {
            "success": True,
            "message": "Recording started",
            "filename": filename,
            "path": self._current_recording_path,
            "max_duration": max_duration,
            "tip": "Use stop_recording() to stop and save"
        }
    
    def _record_audio(self, max_duration: int):
        """Internal method to record audio in background"""
        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            start_time = time.time()
            while self._is_recording and (time.time() - start_time) < max_duration:
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                self._frames.append(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # Auto-save if stopped due to max duration
            if self._is_recording:
                self._is_recording = False
                self._save_recording()
                
        except Exception as e:
            self._is_recording = False
            print(f"[VOICE] Recording error: {e}")
    
    def _save_recording(self) -> bool:
        """Save recorded frames to WAV file"""
        if not self._frames or not self._current_recording_path:
            return False
        
        try:
            wf = wave.open(self._current_recording_path, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self._frames))
            wf.close()
            return True
        except Exception as e:
            print(f"[VOICE] Save error: {e}")
            return False
    
    def stop_recording(self) -> Dict[str, Any]:
        """Stop recording and save the audio file"""
        if not self._is_recording:
            return {"success": False, "error": "Not currently recording"}
        
        self._is_recording = False
        
        # Wait for recording thread to finish
        if self._recording_thread:
            self._recording_thread.join(timeout=2)
        
        # Save the recording
        if self._save_recording():
            duration = len(self._frames) * self.chunk_size / self.sample_rate
            path = self._current_recording_path
            
            # Convert to MP3 if pydub available
            mp3_path = None
            if PYDUB_AVAILABLE:
                try:
                    mp3_path = path.replace('.wav', '.mp3')
                    audio = AudioSegment.from_wav(path)
                    audio.export(mp3_path, format='mp3')
                except:
                    mp3_path = None
            
            return {
                "success": True,
                "message": "Recording saved",
                "wav_path": path,
                "mp3_path": mp3_path,
                "duration_seconds": round(duration, 2),
                "size_bytes": os.path.getsize(path)
            }
        else:
            return {"success": False, "error": "Failed to save recording"}
    
    def quick_record(self, duration: int = 5, filename: Optional[str] = None) -> Dict[str, Any]:
        """Record audio for a specific duration (blocking)
        
        Args:
            duration: Recording duration in seconds
            filename: Optional filename
        """
        if not PYAUDIO_AVAILABLE:
            return {"success": False, "error": "pyaudio not installed. Run: pip install pyaudio"}
        
        # Generate filename
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quick_recording_{timestamp}.wav"
        
        if not filename.endswith('.wav'):
            filename += '.wav'
        
        output_path = os.path.join(self.recordings_dir, filename)
        
        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            print(f"[VOICE] Recording for {duration} seconds...")
            frames = []
            
            for _ in range(0, int(self.sample_rate / self.chunk_size * duration)):
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # Save WAV
            wf = wave.open(output_path, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            # Convert to MP3
            mp3_path = None
            if PYDUB_AVAILABLE:
                try:
                    mp3_path = output_path.replace('.wav', '.mp3')
                    audio = AudioSegment.from_wav(output_path)
                    audio.export(mp3_path, format='mp3')
                except:
                    mp3_path = None
            
            return {
                "success": True,
                "message": f"Recorded {duration} seconds",
                "wav_path": output_path,
                "mp3_path": mp3_path,
                "duration_seconds": duration,
                "size_bytes": os.path.getsize(output_path)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def transcribe_audio(self, audio_path: str, language: str = "en-US") -> Dict[str, Any]:
        """Transcribe audio file to text using speech recognition
        
        Args:
            audio_path: Path to audio file (WAV format works best)
            language: Language code (default: en-US)
        """
        if not SR_AVAILABLE:
            return {"success": False, "error": "speech_recognition not installed. Run: pip install SpeechRecognition"}
        
        # Resolve path
        if not os.path.isabs(audio_path):
            audio_path = os.path.join(self.recordings_dir, audio_path)
        
        if not os.path.exists(audio_path):
            return {"success": False, "error": f"Audio file not found: {audio_path}"}
        
        try:
            with sr.AudioFile(audio_path) as source:
                audio = self.recognizer.record(source)
            
            # Try Google Speech Recognition (free, no API key needed)
            text = self.recognizer.recognize_google(audio, language=language)
            
            return {
                "success": True,
                "transcription": text,
                "language": language,
                "audio_file": audio_path
            }
            
        except sr.UnknownValueError:
            return {"success": False, "error": "Could not understand audio"}
        except sr.RequestError as e:
            return {"success": False, "error": f"Speech recognition service error: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def record_and_transcribe(self, duration: int = 10, language: str = "en-US") -> Dict[str, Any]:
        """Record audio and immediately transcribe it
        
        Args:
            duration: Recording duration in seconds
            language: Language for transcription
        """
        # Record
        record_result = self.quick_record(duration=duration)
        if not record_result.get("success"):
            return record_result
        
        # Transcribe
        wav_path = record_result.get("wav_path")
        transcribe_result = self.transcribe_audio(wav_path, language)
        
        return {
            "success": transcribe_result.get("success", False),
            "recording": record_result,
            "transcription": transcribe_result.get("transcription", ""),
            "error": transcribe_result.get("error")
        }
    
    def list_recordings(self) -> Dict[str, Any]:
        """List all recorded audio files"""
        try:
            recordings = []
            for f in os.listdir(self.recordings_dir):
                if f.endswith(('.wav', '.mp3', '.ogg', '.m4a')):
                    path = os.path.join(self.recordings_dir, f)
                    stat = os.stat(path)
                    recordings.append({
                        "filename": f,
                        "path": path,
                        "size_bytes": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            recordings.sort(key=lambda x: x["modified"], reverse=True)
            
            return {
                "success": True,
                "count": len(recordings),
                "recordings": recordings,
                "directory": self.recordings_dir
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def play_recording(self, filename: str) -> Dict[str, Any]:
        """Play a recording using the system default player
        
        Args:
            filename: Name of the recording file
        """
        if not os.path.isabs(filename):
            filepath = os.path.join(self.recordings_dir, filename)
        else:
            filepath = filename
        
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        
        try:
            os.startfile(filepath)
            return {"success": True, "message": f"Playing: {filename}", "path": filepath}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_recording(self, filename: str) -> Dict[str, Any]:
        """Delete a recording file
        
        Args:
            filename: Name of the recording to delete
        """
        if not os.path.isabs(filename):
            filepath = os.path.join(self.recordings_dir, filename)
        else:
            filepath = filename
        
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        
        try:
            os.remove(filepath)
            return {"success": True, "message": f"Deleted: {filename}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_recording_info(self, filename: str) -> Dict[str, Any]:
        """Get detailed info about a recording
        
        Args:
            filename: Name of the recording file
        """
        if not os.path.isabs(filename):
            filepath = os.path.join(self.recordings_dir, filename)
        else:
            filepath = filename
        
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        
        try:
            stat = os.stat(filepath)
            info = {
                "success": True,
                "filename": os.path.basename(filepath),
                "path": filepath,
                "size_bytes": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
            
            # Get audio details if WAV
            if filepath.endswith('.wav'):
                try:
                    with wave.open(filepath, 'rb') as wf:
                        info["channels"] = wf.getnchannels()
                        info["sample_rate"] = wf.getframerate()
                        info["sample_width"] = wf.getsampwidth()
                        info["frames"] = wf.getnframes()
                        info["duration_seconds"] = round(wf.getnframes() / wf.getframerate(), 2)
                except Exception:
                    logger.debug("Failed to read WAV metadata", exc_info=True)
            
            # Get duration with pydub if available
            if PYDUB_AVAILABLE:
                try:
                    audio = AudioSegment.from_file(filepath)
                    info["duration_seconds"] = round(len(audio) / 1000, 2)
                    info["duration_formatted"] = f"{int(len(audio)//60000)}:{int((len(audio)%60000)//1000):02d}"
                except Exception:
                    logger.debug("Failed to read audio duration via pydub", exc_info=True)
            
            return info
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def trim_recording(self, filename: str, start_ms: int = 0, end_ms: Optional[int] = None, 
                       output_filename: Optional[str] = None) -> Dict[str, Any]:
        """Trim a recording to specified start/end times
        
        Args:
            filename: Input recording filename
            start_ms: Start time in milliseconds
            end_ms: End time in milliseconds (None = end of file)
            output_filename: Output filename (None = auto-generate)
        """
        if not PYDUB_AVAILABLE:
            return {"success": False, "error": "pydub not installed. Run: pip install pydub"}
        
        if not os.path.isabs(filename):
            filepath = os.path.join(self.recordings_dir, filename)
        else:
            filepath = filename
        
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        
        try:
            audio = AudioSegment.from_file(filepath)
            
            if end_ms is None:
                end_ms = len(audio)
            
            trimmed = audio[start_ms:end_ms]
            
            if not output_filename:
                base = os.path.splitext(os.path.basename(filepath))[0]
                ext = os.path.splitext(filepath)[1]
                output_filename = f"{base}_trimmed{ext}"
            
            output_path = os.path.join(self.recordings_dir, output_filename)
            
            # Determine format from extension
            fmt = os.path.splitext(output_filename)[1].lstrip('.')
            if fmt == 'mp3':
                trimmed.export(output_path, format='mp3')
            else:
                trimmed.export(output_path, format='wav')
            
            return {
                "success": True,
                "message": f"Trimmed recording saved",
                "input": filepath,
                "output": output_path,
                "original_duration_ms": len(audio),
                "trimmed_duration_ms": len(trimmed),
                "start_ms": start_ms,
                "end_ms": end_ms
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def adjust_volume(self, filename: str, db_change: float, 
                      output_filename: Optional[str] = None) -> Dict[str, Any]:
        """Adjust recording volume
        
        Args:
            filename: Input recording filename
            db_change: Volume change in decibels (positive = louder, negative = quieter)
            output_filename: Output filename (None = auto-generate)
        """
        if not PYDUB_AVAILABLE:
            return {"success": False, "error": "pydub not installed. Run: pip install pydub"}
        
        if not os.path.isabs(filename):
            filepath = os.path.join(self.recordings_dir, filename)
        else:
            filepath = filename
        
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        
        try:
            audio = AudioSegment.from_file(filepath)
            adjusted = audio + db_change
            
            if not output_filename:
                base = os.path.splitext(os.path.basename(filepath))[0]
                ext = os.path.splitext(filepath)[1]
                sign = "louder" if db_change > 0 else "quieter"
                output_filename = f"{base}_{sign}{ext}"
            
            output_path = os.path.join(self.recordings_dir, output_filename)
            
            fmt = os.path.splitext(output_filename)[1].lstrip('.')
            adjusted.export(output_path, format=fmt if fmt in ['mp3', 'wav', 'ogg'] else 'wav')
            
            return {
                "success": True,
                "message": f"Volume adjusted by {db_change}dB",
                "input": filepath,
                "output": output_path,
                "db_change": db_change
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def convert_format(self, filename: str, output_format: str = "mp3") -> Dict[str, Any]:
        """Convert recording to different format
        
        Args:
            filename: Input recording filename
            output_format: Output format (mp3, wav, ogg, flac)
        """
        if not PYDUB_AVAILABLE:
            return {"success": False, "error": "pydub not installed. Run: pip install pydub"}
        
        if not os.path.isabs(filename):
            filepath = os.path.join(self.recordings_dir, filename)
        else:
            filepath = filename
        
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        
        try:
            audio = AudioSegment.from_file(filepath)
            
            base = os.path.splitext(os.path.basename(filepath))[0]
            output_filename = f"{base}.{output_format}"
            output_path = os.path.join(self.recordings_dir, output_filename)
            
            audio.export(output_path, format=output_format)
            
            return {
                "success": True,
                "message": f"Converted to {output_format}",
                "input": filepath,
                "output": output_path,
                "format": output_format,
                "size_bytes": os.path.getsize(output_path)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def voice_note(self, duration: int = 30, transcribe: bool = True) -> Dict[str, Any]:
        """Quick voice note - record, transcribe, and return text
        
        Args:
            duration: Max recording duration in seconds
            transcribe: Whether to transcribe the audio
        """
        result = self.quick_record(duration=duration)
        if not result.get("success"):
            return result
        
        response = {
            "success": True,
            "recording": result
        }
        
        if transcribe and SR_AVAILABLE:
            transcription = self.transcribe_audio(result["wav_path"])
            response["transcription"] = transcription.get("transcription", "")
            response["transcription_success"] = transcription.get("success", False)
        
        return response


# Create singleton instance
voice = VoiceTools()
