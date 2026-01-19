"""FFmpeg helper utilities used by the Music Video pipeline."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple


def which_ffmpeg() -> Optional[str]:
    return shutil.which("ffmpeg")


def ffprobe_duration_seconds(path: str) -> Optional[float]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        p = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if p.returncode != 0:
            return None
        s = (p.stdout or "").strip()
        return float(s) if s else None
    except Exception:
        return None


def transcode_h264(
    input_path: str,
    output_path: str,
    width: int,
    height: int,
    fps: int,
    crf: int = 18,
    preset: str = "medium",
) -> Tuple[bool, str]:
    ffmpeg = which_ffmpeg()
    if not ffmpeg:
        return False, "ffmpeg not found in PATH"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Ensure consistent stream properties for concat.
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        input_path,
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p,fps={fps}",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        output_path,
    ]

    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        err = (p.stderr or p.stdout or "").strip()[-2000:]
        return False, err
    return True, "ok"


def concat_videos(video_paths: List[str], output_path: str) -> Tuple[bool, str]:
    ffmpeg = which_ffmpeg()
    if not ffmpeg:
        return False, "ffmpeg not found in PATH"

    if not video_paths:
        return False, "No video clips provided"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Use concat demuxer
    with tempfile.TemporaryDirectory() as td:
        lst = Path(td) / "concat.txt"
        lines = []
        for vp in video_paths:
            # -safe 0 allows absolute paths
            safe_vp = vp.replace("'", "'\\''")
            lines.append("file '" + safe_vp + "'")
        lst.write_text("\n".join(lines), encoding="utf-8")

        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c",
            "copy",
            output_path,
        ]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            # If stream mismatch, caller should transcode clips first.
            err = (p.stderr or p.stdout or "").strip()[-2000:]
            return False, err

    return True, "ok"


def mux_audio(video_path: str, audio_path: str, output_path: str) -> Tuple[bool, str]:
    ffmpeg = which_ffmpeg()
    if not ffmpeg:
        return False, "ffmpeg not found in PATH"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        video_path,
        "-i",
        audio_path,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        output_path,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        err = (p.stderr or p.stdout or "").strip()[-2000:]
        return False, err
    return True, "ok"
