"""
Video Editor - Merge clips, add effects, watermarks, and compress
"""
import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from loguru import logger

from backend.config import settings, OUTPUT_DIR, TEMP_DIR


class VideoEditor:
    """Video editing and post-processing"""
    
    def __init__(self):
        self.output_dir = OUTPUT_DIR / "videos"
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir = TEMP_DIR
        self.temp_dir.mkdir(exist_ok=True)
        
        # Check for ffmpeg
        self.ffmpeg_available = shutil.which("ffmpeg") is not None
    
    async def merge_clips(
        self,
        video_paths: List[str],
        transition: str = "crossfade",
        transition_duration: float = 0.5,
        output_name: Optional[str] = None
    ) -> str:
        """
        Merge multiple video clips into one
        
        Args:
            video_paths: List of video file paths
            transition: Transition type (crossfade, fade, cut)
            transition_duration: Duration of transition in seconds
            output_name: Optional output filename
        """
        if len(video_paths) == 1:
            return video_paths[0]
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_name = output_name or f"merged_{timestamp}"
        output_path = self.output_dir / f"{output_name}.mp4"
        
        try:
            if self.ffmpeg_available:
                return await self._merge_with_ffmpeg(video_paths, transition, transition_duration, str(output_path))
            else:
                return await self._merge_with_moviepy(video_paths, transition, transition_duration, str(output_path))
        except Exception as e:
            logger.error(f"Failed to merge clips: {e}")
            # Return first clip as fallback
            return video_paths[0]
    
    async def _merge_with_ffmpeg(
        self,
        video_paths: List[str],
        transition: str,
        transition_duration: float,
        output_path: str
    ) -> str:
        """Merge using ffmpeg (faster)"""
        import asyncio
        
        # Create concat file
        concat_file = self.temp_dir / "concat.txt"
        with open(concat_file, "w") as f:
            for path in video_paths:
                f.write(f"file '{path}'\n")
        
        # Build ffmpeg command
        if transition == "cut":
            # Simple concatenation
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                output_path
            ]
        else:
            # With crossfade (more complex)
            # For now, use simple concat and add fades
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "libx264", "-preset", "medium",
                "-crf", str(settings.VIDEO_CRF),
                output_path
            ]
        
        loop = asyncio.get_event_loop()
        process = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True)
        )
        
        # Cleanup
        concat_file.unlink()
        
        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {process.stderr}")
        
        return output_path
    
    async def _merge_with_moviepy(
        self,
        video_paths: List[str],
        transition: str,
        transition_duration: float,
        output_path: str
    ) -> str:
        """Merge using moviepy"""
        import asyncio
        from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip
        
        loop = asyncio.get_event_loop()
        
        def do_merge():
            clips = [VideoFileClip(path) for path in video_paths]
            
            if transition == "crossfade" and len(clips) > 1:
                # Add crossfade between clips
                final_clips = [clips[0]]
                for i in range(1, len(clips)):
                    # Fade out previous, fade in current
                    final_clips.append(
                        clips[i].crossfadein(transition_duration)
                    )
                
                final = concatenate_videoclips(final_clips, method="compose")
            else:
                final = concatenate_videoclips(clips)
            
            final.write_videofile(
                output_path,
                codec="libx264",
                preset="medium",
                bitrate=settings.VIDEO_BITRATE,
                logger=None
            )
            
            # Cleanup
            for clip in clips:
                clip.close()
            final.close()
            
            return output_path
        
        return await loop.run_in_executor(None, do_merge)
    
    async def add_watermark(
        self,
        video_path: str,
        text: Optional[str] = None,
        image_path: Optional[str] = None,
        position: str = "bottom_right",
        opacity: float = 0.7
    ) -> str:
        """Add watermark to video"""
        text = text or settings.WATERMARK_TEXT
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_path = self.output_dir / f"watermarked_{timestamp}.mp4"
        
        try:
            if self.ffmpeg_available:
                return await self._watermark_ffmpeg(video_path, text, str(output_path), position)
            else:
                return await self._watermark_moviepy(video_path, text, str(output_path), position, opacity)
        except Exception as e:
            logger.warning(f"Failed to add watermark: {e}")
            return video_path  # Return original if watermarking fails
    
    async def _watermark_ffmpeg(self, video_path: str, text: str, output_path: str, position: str) -> str:
        """Add text watermark with ffmpeg"""
        import asyncio
        
        # Position mapping
        positions = {
            "top_left": "x=10:y=10",
            "top_right": "x=w-tw-10:y=10",
            "bottom_left": "x=10:y=h-th-10",
            "bottom_right": "x=w-tw-10:y=h-th-10",
            "center": "x=(w-tw)/2:y=(h-th)/2"
        }
        pos = positions.get(position, positions["bottom_right"])
        
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"drawtext=text='{text}':fontcolor=white@0.7:fontsize=20:{pos}",
            "-codec:a", "copy",
            output_path
        ]
        
        loop = asyncio.get_event_loop()
        process = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True)
        )
        
        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {process.stderr}")
        
        return output_path
    
    async def _watermark_moviepy(
        self,
        video_path: str,
        text: str,
        output_path: str,
        position: str,
        opacity: float
    ) -> str:
        """Add watermark with moviepy"""
        import asyncio
        from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
        
        loop = asyncio.get_event_loop()
        
        def do_watermark():
            video = VideoFileClip(video_path)
            
            # Create text clip
            txt = TextClip(
                text,
                fontsize=20,
                color='white',
                font='Arial'
            ).set_opacity(opacity).set_duration(video.duration)
            
            # Position
            if position == "bottom_right":
                txt = txt.set_position(('right', 'bottom')).margin(right=10, bottom=10)
            elif position == "bottom_left":
                txt = txt.set_position(('left', 'bottom')).margin(left=10, bottom=10)
            elif position == "top_right":
                txt = txt.set_position(('right', 'top')).margin(right=10, top=10)
            elif position == "top_left":
                txt = txt.set_position(('left', 'top')).margin(left=10, top=10)
            else:
                txt = txt.set_position('center')
            
            # Composite
            final = CompositeVideoClip([video, txt])
            final.write_videofile(
                output_path,
                codec="libx264",
                preset="medium",
                logger=None
            )
            
            video.close()
            final.close()
            
            return output_path
        
        return await loop.run_in_executor(None, do_watermark)
    
    async def compress_for_web(
        self,
        video_path: str,
        target_size_mb: Optional[float] = None,
        max_bitrate: str = "5000k"
    ) -> str:
        """Compress video for web delivery"""
        import asyncio
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_path = self.output_dir / f"compressed_{timestamp}.mp4"
        
        if self.ffmpeg_available:
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-maxrate", max_bitrate,
                "-bufsize", "10000k",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",  # Web optimization
                str(output_path)
            ]
            
            loop = asyncio.get_event_loop()
            process = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True)
            )
            
            if process.returncode == 0:
                return str(output_path)
        
        # Fallback: copy original
        shutil.copy(video_path, str(output_path))
        return str(output_path)
    
    async def convert_to_facebook_reel(self, video_path: str) -> str:
        """Convert video to Facebook Reel format (9:16 vertical)"""
        import asyncio
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_path = self.output_dir / f"reel_{timestamp}.mp4"
        
        if self.ffmpeg_available:
            # Crop/pad to 9:16 aspect ratio
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "20",
                "-c:a", "aac",
                str(output_path)
            ]
            
            loop = asyncio.get_event_loop()
            process = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True)
            )
            
            if process.returncode == 0:
                return str(output_path)
        
        return video_path
    
    async def add_intro(self, video_path: str, intro_text: str = "Agent Amigos Presents") -> str:
        """Add intro title card to video"""
        # TODO: Implement intro generation
        return video_path
    
    async def add_outro(self, video_path: str, outro_text: str = "Created with Agent Amigos") -> str:
        """Add outro to video"""
        # TODO: Implement outro generation
        return video_path
    
    async def add_audio(
        self,
        video_path: str,
        audio_path: str,
        volume: float = 0.5
    ) -> str:
        """Add background audio to video"""
        import asyncio
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_path = self.output_dir / f"with_audio_{timestamp}.mp4"
        
        if self.ffmpeg_available:
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-filter_complex", f"[1:a]volume={volume}[a]",
                "-map", "0:v", "-map", "[a]",
                "-c:v", "copy",
                "-shortest",
                str(output_path)
            ]
            
            loop = asyncio.get_event_loop()
            process = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True)
            )
            
            if process.returncode == 0:
                return str(output_path)
        
        return video_path
    
    async def trim(
        self,
        video_path: str,
        start_time: float,
        end_time: float
    ) -> str:
        """Trim video to specified time range"""
        import asyncio
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_path = self.output_dir / f"trimmed_{timestamp}.mp4"
        
        if self.ffmpeg_available:
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-ss", str(start_time),
                "-to", str(end_time),
                "-c", "copy",
                str(output_path)
            ]
            
            loop = asyncio.get_event_loop()
            process = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True)
            )
            
            if process.returncode == 0:
                return str(output_path)
        
        return video_path
    
    async def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Get video metadata"""
        import asyncio
        
        if not os.path.exists(video_path):
            return {"error": "File not found"}
        
        if self.ffmpeg_available:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]
            
            loop = asyncio.get_event_loop()
            process = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True)
            )
            
            if process.returncode == 0:
                import json
                return json.loads(process.stdout)
        
        # Basic info without ffprobe
        return {
            "path": video_path,
            "size": os.path.getsize(video_path),
            "exists": True
        }
