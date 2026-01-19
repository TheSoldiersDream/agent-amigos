"""DeepFaceLab installer helper.

This script exists so the FastAPI server can launch a background install job that:
- does NOT depend on PowerShell glue
- can fall back to zip download/extract when git is missing
- writes a machine-readable result JSON containing exit_code/error

It is intentionally dependency-free (stdlib only) so it can run in fresh envs.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional


DEFAULT_ZIP_URL = "https://github.com/iperov/DeepFaceLab/archive/refs/heads/master.zip"


def _log_line(log_path: Optional[str], message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}\n"
    if not log_path:
        return
    try:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:
        # avoid failing the installer due to logging issues
        pass


def _write_result(result_path: str, payload: dict) -> None:
    try:
        Path(result_path).parent.mkdir(parents=True, exist_ok=True)
        with open(result_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
    except Exception:
        pass


def _which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def _run(cmd: list[str], cwd: Optional[Path], log_path: Optional[str]) -> int:
    _log_line(log_path, f"RUN: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=False,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        _log_line(log_path, line.rstrip("\n"))
    return proc.wait()


def _find_main_py(root: Path) -> Optional[Path]:
    # Find a main.py that looks like DeepFaceLab's entrypoint.
    candidates = list(root.rglob("main.py"))
    if not candidates:
        return None
    # Prefer a shallower path.
    candidates.sort(key=lambda p: (len(p.parts), str(p)))
    return candidates[0]


def _normalize_extracted_layout(extract_root: Path, log_path: Optional[str]) -> Path:
    """Return the directory that should be treated as the DeepFaceLab root."""
    main_py = _find_main_py(extract_root)
    if main_py is None:
        return extract_root
    dfl_root = main_py.parent
    # Heuristic: if main.py is nested inside exactly one directory level, use that.
    _log_line(log_path, f"Detected DeepFaceLab root at: {dfl_root}")
    return dfl_root


def _copy_tree(src: Path, dst: Path, log_path: Optional[str]) -> None:
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    _log_line(log_path, f"Copying {src} -> {dst}")
    try:
        shutil.copytree(src, dst)
        return
    except Exception as exc:
        # Windows can hit MAX_PATH issues when copying into deeper directories.
        # If that happens, fall back to a junction (doesn't require admin).
        if os.name == 'nt':
            msg = str(exc)
            winerror = getattr(exc, 'winerror', None)
            if winerror == 206 or 'File name too long' in msg or 'filename too long' in msg:
                _log_line(log_path, f"Copy failed due to path length; creating junction instead: {msg}")
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists():
                    shutil.rmtree(dst, ignore_errors=True)
                rc = _run([
                    'cmd.exe',
                    '/c',
                    'mklink',
                    '/J',
                    str(dst),
                    str(src),
                ], cwd=None, log_path=log_path)
                if rc == 0 and dst.exists():
                    return
        raise


def _ensure_sources(target_dir: Path, project_root: Path, repo: str, log_path: Optional[str]) -> None:
    # If already installed, keep it.
    if (target_dir / "main.py").exists():
        _log_line(log_path, "DeepFaceLab already present (main.py found).")
        return

    target_dir.parent.mkdir(parents=True, exist_ok=True)

    git = _which("git")
    if git:
        _log_line(log_path, f"git found at {git}; cloning {repo}")
        # Clean the target if it exists but incomplete.
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        rc = _run([git, "clone", "--depth", "1", repo, str(target_dir)], cwd=project_root, log_path=log_path)
        if rc != 0:
            raise RuntimeError(f"git clone failed (exit {rc})")
        if not (target_dir / "main.py").exists():
            # Sometimes repo structure changes; fall through to check.
            _log_line(log_path, "Clone finished but main.py not found at root; will attempt normalization.")
    else:
        _log_line(log_path, "git not found; using zip fallback")

        # Offline/local fallback: if the user already has an extracted DeepFaceLab folder
        # in the repo, prefer copying it rather than downloading.
        local_dir_candidates = [
            project_root / "DeepFaceLab",
            project_root / "DeepFaceLab" / "DeepFaceLab-master",
            project_root / "external" / "DeepFaceLab",
            project_root / "backend" / "external" / "DeepFaceLab",
        ]
        for cand in local_dir_candidates:
            try:
                if not cand.exists() or not cand.is_dir():
                    continue
                main_py = _find_main_py(cand)
                if main_py is None:
                    continue
                dfl_root = main_py.parent
                _log_line(log_path, f"Found local DeepFaceLab checkout at {dfl_root}; copying")
                _copy_tree(dfl_root, target_dir, log_path=log_path)
                return
            except Exception:
                # continue searching
                pass

        zip_candidates = [
            project_root / "external" / "DeepFaceLab-master.zip",
            project_root / "backend" / "external" / "DeepFaceLab-master.zip",
        ]
        zip_path = next((p for p in zip_candidates if p.exists()), None)

        # Validate any existing zip (failed/partial downloads are common on Windows).
        if zip_path is not None:
            try:
                if zip_path.stat().st_size < 1024:
                    raise RuntimeError(f"Zip file too small ({zip_path.stat().st_size} bytes)")
                with zipfile.ZipFile(zip_path, "r") as zf:
                    # Touch the central directory
                    zf.namelist()
            except Exception as exc:
                _log_line(log_path, f"Existing zip appears invalid ({zip_path}): {exc}; will re-download")
                zip_path = None

        if zip_path is None:
            # Download to backend/external by default.
            zip_path = project_root / "backend" / "external" / "DeepFaceLab-master.zip"
            zip_path.parent.mkdir(parents=True, exist_ok=True)
            _log_line(log_path, f"Downloading {DEFAULT_ZIP_URL} -> {zip_path}")
            # Download to a temp file first then atomically replace.
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_fh:
                tmp_name = tmp_fh.name
            try:
                urllib.request.urlretrieve(DEFAULT_ZIP_URL, tmp_name)  # nosec - intended
                Path(tmp_name).replace(zip_path)
            finally:
                try:
                    Path(tmp_name).unlink(missing_ok=True)
                except Exception:
                    pass

        with tempfile.TemporaryDirectory(prefix="dfl_zip_") as tmp:
            tmp_dir = Path(tmp)
            _log_line(log_path, f"Extracting {zip_path} -> {tmp_dir}")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp_dir)

            dfl_root = _normalize_extracted_layout(tmp_dir, log_path=log_path)
            _copy_tree(dfl_root, target_dir, log_path=log_path)

    # Final sanity: attempt normalization if main.py still not at root
    if not (target_dir / "main.py").exists():
        nested_main = _find_main_py(target_dir)
        if nested_main is None:
            raise RuntimeError("DeepFaceLab install incomplete: main.py not found")
        nested_root = nested_main.parent
        if nested_root != target_dir:
            _log_line(log_path, f"Normalizing nested layout {nested_root} -> {target_dir}")
            with tempfile.TemporaryDirectory(prefix="dfl_norm_") as tmp:
                tmp_target = Path(tmp) / "DeepFaceLab"
                _copy_tree(nested_root, tmp_target, log_path=log_path)
                shutil.rmtree(target_dir, ignore_errors=True)
                shutil.copytree(tmp_target, target_dir)


def _install_requirements(target_dir: Path, python_exe: Path, log_path: Optional[str]) -> None:
    req_cuda = target_dir / "requirements-cuda.txt"
    req_plain = target_dir / "requirements.txt"

    if req_cuda.exists():
        req = req_cuda
    elif req_plain.exists():
        req = req_plain
    else:
        _log_line(log_path, "No requirements file found; skipping pip install")
        return

    _log_line(log_path, f"Installing requirements from {req}")
    rc = _run([str(python_exe), "-m", "pip", "install", "-r", str(req)], cwd=target_dir, log_path=log_path)
    if rc != 0:
        raise RuntimeError(f"pip install failed (exit {rc})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--repo", default="https://github.com/iperov/DeepFaceLab.git")
    parser.add_argument("--python", dest="python_exe", default=sys.executable)
    parser.add_argument("--log", default="")
    parser.add_argument("--result", required=True)
    parser.add_argument(
        "--skip-pip",
        action="store_true",
        help="Skip installing requirements with pip (recommended on modern Python; use the API 'Ensure Requirements' button separately).",
    )
    args = parser.parse_args()

    target_dir = Path(args.target).resolve()
    project_root = Path(args.project_root).resolve()
    python_exe = Path(args.python_exe).resolve()
    log_path = args.log or None

    started = time.time()
    try:
        _log_line(log_path, f"Starting DeepFaceLab install into {target_dir}")
        _log_line(log_path, f"Using python: {python_exe}")
        _ensure_sources(target_dir=target_dir, project_root=project_root, repo=args.repo, log_path=log_path)
        if args.skip_pip:
            _log_line(log_path, "Skipping pip install step (--skip-pip)")
        else:
            _install_requirements(target_dir=target_dir, python_exe=python_exe, log_path=log_path)
        elapsed = time.time() - started
        _log_line(log_path, f"DeepFaceLab install completed in {elapsed:.1f}s")
        _write_result(args.result, {"exit_code": 0, "error": "", "elapsed_s": elapsed})
        return 0
    except Exception as exc:
        elapsed = time.time() - started
        msg = str(exc)
        _log_line(log_path, f"ERROR: {msg}")
        _write_result(args.result, {"exit_code": 1, "error": msg[:500], "elapsed_s": elapsed})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
