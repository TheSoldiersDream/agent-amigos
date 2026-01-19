import urllib.request
import urllib.parse
import json
import base64
import time

def probe_pollinations():
    # Create a small test image
    from PIL import Image
    img = Image.new('RGB', (100, 100), color = 'blue')
    img.save('test_probe.png')
    
    with open('test_probe.png', "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    data_uri = f"data:image/png;base64,{image_data}"
    
    prompts = [
        "video of a car",
        "animation of a car",
    ]
    
    models = [
        "seedance",
        "flux-video", # Guessing
        "turbo",
    ]
    
    for model in models:
        print(f"\n--- Testing model: {model} ---")
        url = f"https://image.pollinations.ai/prompt/test?model={model}&nologo=true"
        
        # Try GET
        try:
            print("Trying GET...")
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req) as resp:
                ct = resp.headers.get("Content-Type")
                print(f"GET Content-Type: {ct}")
        except Exception as e:
            print(f"GET Error: {e}")
            
        # Try POST with image
        try:
            print("Trying POST with image...")
            payload = {
                "image": data_uri,
                "model": model,
                "prompt": "video of a car",
                "nologo": True
            }
            req = urllib.request.Request(
                url, 
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                ct = resp.headers.get("Content-Type")
                print(f"POST Content-Type: {ct}")
        except Exception as e:
            print(f"POST Error: {e}")

if __name__ == "__main__":
    probe_pollinations()
