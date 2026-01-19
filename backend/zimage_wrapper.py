import sys
import os
import argparse
import time
# Defer torch import until after sys.path manipulation to avoid side effects
from pathlib import Path

# Remove current directory (backend) from sys.path to avoid conflict with backend/config.py
# Z-Image has a 'config' module that conflicts with backend's config.py
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir in sys.path:
    sys.path.remove(script_dir)
# Also remove CWD if it's the backend dir
cwd = os.getcwd()
if cwd == script_dir and cwd in sys.path:
    sys.path.remove(cwd)

# Add Z-Image paths
ZIMAGE_ROOT = Path(r"c:\Users\user\AgentAmigos\external\ComfyUI\custom_nodes\Z-Image")
sys.path.insert(0, str(ZIMAGE_ROOT))
sys.path.insert(0, str(ZIMAGE_ROOT / "src"))

import torch

# Import Z-Image modules while avoiding collision with the backend 'config' module.
# Strategy: temporarily remove any existing 'config' entry from sys.modules, import Z-Image
# (which has its own 'config' package under src/config), then restore the original 'config'.
orig_config_mod = sys.modules.pop("config", None)
try:
    try:
        from utils import AttentionBackend, ensure_model_weights, load_from_local_dir, set_attention_backend
        from zimage import generate
    except ImportError:
        # Fallback if installed as package but names are different or path issues
        try:
            from src.utils import AttentionBackend, ensure_model_weights, load_from_local_dir, set_attention_backend
            from src.zimage import generate
        except ImportError as e:
            print(f"Error importing Z-Image modules: {e}")
            # Restore original config before exiting
            if orig_config_mod is not None:
                sys.modules["config"] = orig_config_mod
            sys.exit(1)
finally:
    # Restore original backend 'config' module to avoid side-effects
    if orig_config_mod is not None:
        sys.modules["config"] = orig_config_mod

def main():
    parser = argparse.ArgumentParser(description="Z-Image Wrapper")
    parser.add_argument("--prompt", type=str, required=True, help="Text prompt")
    parser.add_argument("--output", type=str, required=True, help="Output image path")
    parser.add_argument("--width", type=int, default=1024, help="Image width")
    parser.add_argument("--height", type=int, default=1024, help="Image height")
    parser.add_argument("--steps", type=int, default=8, help="Inference steps")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--model_dir", type=str, default=str(ZIMAGE_ROOT / "ckpts" / "Z-Image-Turbo"), help="Model directory")
    
    args = parser.parse_args()
    
    print(f"Generating image with Z-Image...")
    print(f"Prompt: {args.prompt}")
    print(f"Output: {args.output}")
    
    # Ensure model weights
    model_path = ensure_model_weights(args.model_dir, verify=False)
    
    dtype = torch.bfloat16
    compile = False # Default to False for compatibility
    
    # Device selection
    if torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    print(f"Device: {device}")
    
    # Load models
    components = load_from_local_dir(model_path, device=device, dtype=dtype, compile=compile)
    
    # Set attention backend
    attn_backend = os.environ.get("ZIMAGE_ATTENTION", "_native_flash")
    # Check if flash attn is available, otherwise fallback
    try:
        set_attention_backend(attn_backend)
    except Exception:
        print("Flash attention not available, falling back to default")
        set_attention_backend("default") # or whatever the fallback is
        
    # Generate
    start_time = time.time()
    images = generate(
        prompt=args.prompt,
        **components,
        height=args.height,
        width=args.width,
        num_inference_steps=args.steps,
        guidance_scale=0.0,
        generator=torch.Generator(device).manual_seed(args.seed),
    )
    end_time = time.time()
    print(f"Time taken: {end_time - start_time:.2f} seconds")
    
    # Save
    images[0].save(args.output)
    print(f"Saved to {args.output}")

if __name__ == "__main__":
    main()
