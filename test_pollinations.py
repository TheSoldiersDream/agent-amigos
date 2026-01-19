import urllib.parse
import urllib.request
import os

def test_pollinations():
    prompt = "a beautiful sunset"
    encoded_prompt = urllib.parse.quote(prompt)
    width = 1024
    height = 1024
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
    print(f"Testing URL: {url}")
    
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=60) as response:
            image_data = response.read()
            print(f"Downloaded {len(image_data)} bytes")
            with open("test_image.png", "wb") as f:
                f.write(image_data)
            print("Saved test_image.png")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_pollinations()
