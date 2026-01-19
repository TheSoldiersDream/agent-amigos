import os
import sys
import urllib.request
import shutil
from pathlib import Path

COMFY_ROOT = Path("external/ComfyUI").resolve()
CHECKPOINTS_DIR = COMFY_ROOT / "models" / "checkpoints"

SVD_URL = "https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/resolve/main/svd_xt.safetensors"
SVD_FILENAME = "svd_xt.safetensors"

def download_file(url, dest_path):
    print(f"Downloading {url} to {dest_path}...")
    try:
        with urllib.request.urlopen(url) as response, open(dest_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print("Download complete.")
        return True
    except Exception as e:
        print(f"Error downloading: {e}")
        return False

def setup_video_engine():
    print("Setting up Open Source Video Engine (ComfyUI + SVD)...")
    
    if not COMFY_ROOT.exists():
        print(f"Error: ComfyUI not found at {COMFY_ROOT}")
        return

    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    target_file = CHECKPOINTS_DIR / SVD_FILENAME
    
    if target_file.exists():
        print(f"Model {SVD_FILENAME} already exists.")
        size_gb = target_file.stat().st_size / (1024**3)
        print(f"Size: {size_gb:.2f} GB")
    else:
        print(f"Model {SVD_FILENAME} not found.")
        print("This is a large download (~9GB).")
        print("Downloading SVD-XT model...")
        # download_file(SVD_URL, target_file) # Uncomment to enable auto-download
        print("Please download 'svd_xt.safetensors' manually and place it in:")
        print(str(CHECKPOINTS_DIR))
        print(f"URL: {SVD_URL}")

    # Install requirements
    print("Installing ComfyUI requirements...")
    venv_python = COMFY_ROOT / "venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        import subprocess
        try:
            subprocess.check_call([str(venv_python), "-m", "pip", "install", "-r", str(COMFY_ROOT / "requirements.txt")])
        except subprocess.CalledProcessError as e:
            print(f"Error installing requirements: {e}")
    else:
        print("ComfyUI venv not found. Please set it up.")

    print("Setup complete.")

if __name__ == "__main__":
    setup_video_engine()
