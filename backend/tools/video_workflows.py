import os
import json
import random

def get_svd_workflow(image_path: str, seed: int = None, motion_bucket_id: int = 127, augmentation_level: float = 0.0):
    if seed is None:
        seed = random.randint(0, 1000000000)
        
    # Normalize path for Windows (ComfyUI expects forward slashes or escaped backslashes)
    image_path = image_path.replace("\\", "/")
    
    workflow = {
        "3": {
            "inputs": {
                "seed": seed,
                "steps": 20,
                "cfg": 2.5,
                "sampler_name": "euler",
                "scheduler": "karras",
                "denoise": 1,
                "model": ["14", 0],
                "positive": ["12", 0],
                "negative": ["12", 1],
                "latent_image": ["12", 2]
            },
            "class_type": "KSampler",
            "_meta": {
                "title": "KSampler"
            }
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["14", 2]
            },
            "class_type": "VAEDecode",
            "_meta": {
                "title": "VAE Decode"
            }
        },
        "12": {
            "inputs": {
                "width": 1024,
                "height": 576,
                "video_frames": 25,
                "motion_bucket_id": motion_bucket_id,
                "fps": 6,
                "augmentation_level": augmentation_level,
                "clip_vision": ["14", 1],
                "init_image": ["23", 0],
                "vae": ["14", 2]
            },
            "class_type": "SVD_img2vid_Conditioning",
            "_meta": {
                "title": "SVD_img2vid_Conditioning"
            }
        },
        "14": {
            "inputs": {
                "ckpt_name": "svd_xt.safetensors"
            },
            "class_type": "ImageOnlyCheckpointLoader",
            "_meta": {
                "title": "Image Only Checkpoint Loader (img2vid model)"
            }
        },
        "23": {
            "inputs": {
                "image": image_path,
                "upload": "image" 
            },
            "class_type": "LoadImage",
            "_meta": {
                "title": "Load Image"
            }
        },
        "26": {
            "inputs": {
                "frame_rate": 8,
                "loop_count": 0,
                "filename_prefix": "SVD_Generation",
                "format": "image/webp",
                "pingpong": False,
                "save_output": True,
                "images": ["8", 0]
            },
            "class_type": "SaveAnimatedWEBP",
            "_meta": {
                "title": "SaveAnimatedWEBP"
            }
        }
    }
    return workflow
