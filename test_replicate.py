import os
import urllib.request
import json
import base64
import time

# Load env var from .env manually since we are running a script
def load_env():
    try:
        with open("backend/.env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
    except Exception as e:
        print(f"Error loading .env: {e}")

load_env()
api_token = os.environ.get("REPLICATE_API_TOKEN")
print(f"Token found: {api_token[:4]}...{api_token[-4:] if api_token else 'None'}")

def test_replicate():
    if not api_token:
        print("No API token found.")
        return

    # Create a small test image
    from PIL import Image
    img = Image.new('RGB', (512, 512), color = 'blue')
    img.save('test_blue.png')
    
    with open('test_blue.png', "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    data_uri = f"data:image/png;base64,{image_data}"

    model_version = "minimax/video-01-live"
    print(f"Testing model: {model_version}")
    
    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "input": {
            "prompt": "a blue square turning into a red circle",
            "first_frame_image": data_uri,
        }
    }
    
    create_url = f"https://api.replicate.com/v1/models/{model_version}/predictions"
    
    try:
        req = urllib.request.Request(
            create_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        
        print("Sending request...")
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            
        print(f"Prediction created: {result.get('id')}")
        print(f"Status: {result.get('status')}")
        
        if result.get('error'):
            print(f"Error from API: {result.get('error')}")
            
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_replicate()
