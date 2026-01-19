import urllib.request
import urllib.parse
import json
import base64
import os

def test_pollinations_post():
    # Create a small red image
    from PIL import Image
    img = Image.new('RGB', (100, 100), color = 'red')
    img.save('test_red.png')
    
    with open('test_red.png', "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    
    data_uri = f"data:image/png;base64,{image_data}"
    
    url = "https://image.pollinations.ai/prompt/test%20video?model=seedance&nologo=true"
    
    # Try sending image in body
    payload = {
        "image": data_uri,
        "model": "seedance",
        "prompt": "test video"
    }
    
    print("Testing POST to Pollinations...")
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method="POST"
        )
        
        with urllib.request.urlopen(req) as resp:
            print(f"Status: {resp.status}")
            print(f"Headers: {resp.headers}")
            content = resp.read()
            print(f"Content length: {len(content)}")
            with open("test_pollinations_result.mp4", "wb") as f:
                f.write(content)
            print("Saved to test_pollinations_result.mp4")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_pollinations_post()
