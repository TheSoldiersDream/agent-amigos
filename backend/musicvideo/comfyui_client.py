"""ComfyUI client helpers for local animation generation.

This module is intentionally workflow-agnostic:
- You provide a ComfyUI workflow JSON exported from the UI.
- The workflow can include placeholders like {{PROMPT}}, {{NEG_PROMPT}}, {{WIDTH}}, etc.
- We substitute placeholders and submit to ComfyUI's HTTP API.

Supported placeholders (strings or numbers in JSON will be replaced):
  {{PROMPT}}, {{NEG_PROMPT}}, {{WIDTH}}, {{HEIGHT}}, {{FRAMES}}, {{FPS}},
  {{SEED}}, {{STEPS}}, {{CFG}}, {{SAMPLER}}, {{SCHEDULER}}

Notes:
- This client only talks to a *local* ComfyUI server (default 127.0.0.1).
- It does not assume any specific custom nodes (AnimateDiff/Deforum/etc).
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests


@dataclass
class ComfyResult:
    success: bool
    prompt_id: Optional[str] = None
    output_video_path: Optional[str] = None
    error: Optional[str] = None
    raw_history: Optional[dict] = None


def _deep_replace_placeholders(obj: Any, mapping: Dict[str, Any]) -> Any:
    """Recursively replace placeholder tokens in a JSON-like object."""
    if isinstance(obj, dict):
        return {k: _deep_replace_placeholders(v, mapping) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_replace_placeholders(v, mapping) for v in obj]
    if isinstance(obj, str):
        s = obj
        for key, val in mapping.items():
            token = "{{" + key + "}}"
            if token in s:
                s = s.replace(token, str(val))
        return s
    # numbers/bools/null left as-is
    return obj


def _pick_first_video_from_history(history: dict) -> Optional[Tuple[str, str, str]]:
    """Return (filename, subfolder, type) from a ComfyUI history object."""
    try:
        # history shape is typically: {prompt_id: {"outputs": {...}}}
        # but some proxies return just the inner object.
        inner = None
        if isinstance(history, dict) and len(history) == 1 and next(iter(history.keys())).count("-") >= 1:
            inner = next(iter(history.values()))
        else:
            inner = history

        outputs = inner.get("outputs", {}) if isinstance(inner, dict) else {}
        for _node_id, node_out in outputs.items():
            if not isinstance(node_out, dict):
                continue
            videos = node_out.get("videos")
            if isinstance(videos, list) and videos:
                v0 = videos[0]
                filename = v0.get("filename")
                subfolder = v0.get("subfolder", "")
                vtype = v0.get("type", "output")
                if filename:
                    return str(filename), str(subfolder or ""), str(vtype or "output")
    except Exception:
        return None
    return None


class ComfyUIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8188", timeout_s: int = 30):
        self.base_url = (base_url or "http://127.0.0.1:8188").rstrip("/")
        self.timeout_s = int(timeout_s)
        self.client_id = str(uuid.uuid4())

    def health_check(self) -> Tuple[bool, str]:
        """Returns (ok, message)."""
        try:
            r = requests.get(self.base_url + "/system_stats", timeout=self.timeout_s)
            if r.status_code == 200:
                return True, "ok"
            # ComfyUI versions differ; fallback to root.
            r2 = requests.get(self.base_url + "/", timeout=self.timeout_s)
            return (r2.status_code < 500), f"http {r.status_code}"
        except Exception as exc:
            return False, str(exc)

    def load_workflow(self, workflow_path: str) -> dict:
        p = Path(workflow_path)
        if not p.exists():
            raise FileNotFoundError(f"ComfyUI workflow not found: {workflow_path}")
        return json.loads(p.read_text(encoding="utf-8"))

    def submit_workflow(self, workflow: dict) -> str:
        payload = {"prompt": workflow, "client_id": self.client_id}
        r = requests.post(self.base_url + "/prompt", json=payload, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        pid = data.get("prompt_id") or data.get("promptId")
        if not pid:
            raise RuntimeError(f"ComfyUI did not return prompt_id: {data}")
        return str(pid)

    def wait_for(self, prompt_id: str, max_wait_s: int = 60 * 20, poll_s: float = 1.5) -> dict:
        """Poll /history until ComfyUI reports outputs for the prompt."""
        deadline = time.time() + max_wait_s
        last_err: Optional[str] = None
        while time.time() < deadline:
            try:
                r = requests.get(self.base_url + f"/history/{prompt_id}", timeout=self.timeout_s)
                if r.status_code == 200:
                    data = r.json()
                    # data usually contains the prompt_id key
                    if isinstance(data, dict) and (prompt_id in data or data.get("outputs")):
                        # if completed, outputs present
                        inner = data.get(prompt_id) if prompt_id in data else data
                        if isinstance(inner, dict) and inner.get("outputs"):
                            return data
                else:
                    last_err = f"history http {r.status_code}"
            except Exception as exc:
                last_err = str(exc)
            time.sleep(poll_s)
        raise TimeoutError(f"Timed out waiting for ComfyUI prompt {prompt_id}. Last error: {last_err}")

    def download_video(self, history: dict, dest_path: str) -> str:
        pick = _pick_first_video_from_history(history)
        if not pick:
            raise RuntimeError("ComfyUI completed but no video output was found in history.")
        filename, subfolder, vtype = pick

        params = {
            "filename": filename,
            "type": vtype,
        }
        if subfolder:
            params["subfolder"] = subfolder

        r = requests.get(self.base_url + "/view", params=params, timeout=max(self.timeout_s, 120))
        r.raise_for_status()

        out = Path(dest_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(r.content)
        return str(out)

    def generate_video(
        self,
        workflow_path: str,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        frames: int,
        fps: int,
        seed: int,
        steps: int = 20,
        cfg: float = 6.0,
        sampler: str = "euler",
        scheduler: str = "normal",
        output_path: str = "",
        max_wait_s: int = 60 * 30,
    ) -> ComfyResult:
        try:
            ok, msg = self.health_check()
            if not ok:
                return ComfyResult(success=False, error=f"ComfyUI not reachable at {self.base_url}: {msg}")

            wf = self.load_workflow(workflow_path)
            mapping = {
                "PROMPT": prompt,
                "NEG_PROMPT": negative_prompt,
                "WIDTH": int(width),
                "HEIGHT": int(height),
                "FRAMES": int(frames),
                "FPS": int(fps),
                "SEED": int(seed),
                "STEPS": int(steps),
                "CFG": float(cfg),
                "SAMPLER": sampler,
                "SCHEDULER": scheduler,
            }
            wf2 = _deep_replace_placeholders(wf, mapping)

            prompt_id = self.submit_workflow(wf2)
            history = self.wait_for(prompt_id, max_wait_s=max_wait_s)

            if not output_path:
                output_path = str(Path(".") / f"comfy_{prompt_id}.mp4")

            out = self.download_video(history, output_path)
            return ComfyResult(success=True, prompt_id=prompt_id, output_video_path=out, raw_history=history)
        except Exception as exc:
            return ComfyResult(success=False, error=str(exc)[:800])


def get_default_comfyui_url() -> str:
    return os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
