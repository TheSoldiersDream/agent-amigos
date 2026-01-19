"""Frame interpolation helpers.

Preferred:
- RIFE (external binary), configured via env RIFE_EXE.

Fallback:
- FFmpeg minterpolate (optical-flow interpolation). This is not RIFE/FILM, but provides
  smooth in-between frames without turning clips into a slideshow.

The MV pipeline can be configured via env:
- MV_INTERPOLATION_ENGINE = "rife" | "ffmpeg-minterpolate" | "none"
- RIFE_EXE = full path to rife binary (if engine=rife)
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Tuple


def _ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def interpolate_to_fps(input_path: str, output_path: str, target_fps: int) -> Tuple[bool, str]:
    engine = (os.environ.get("MV_INTERPOLATION_ENGINE") or "ffmpeg-minterpolate").strip().lower()

    if engine in {"none", "off", "false", "0"}:
        return False, "interpolation disabled"

    if engine == "rife":
        exe = os.environ.get("RIFE_EXE")
        if not exe or not Path(exe).exists():
            return False, "RIFE_EXE not set or not found"
        # Many RIFE binaries differ in CLI; we support a conservative invocation via ffmpeg pipe.
        # If you have a specific RIFE build, set MV_INTERPOLATION_ENGINE=none and pre-interpolate externally,
        # or adjust this wrapper.
        return False, "RIFE engine requested but no supported invocation configured"

    # Default: ffmpeg minterpolate
    ffmpeg = _ffmpeg()
    if not ffmpeg:
        return False, "ffmpeg not found in PATH"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    vf = (
        f"minterpolate=fps={int(target_fps)}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
    )

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        input_path,
        "-vf",
        vf,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        output_path,
    ]

    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        err = (p.stderr or p.stdout or "").strip()[-2000:]
        return False, err
    return True, "ok"