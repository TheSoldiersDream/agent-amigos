import requests
url = 'http://127.0.0.1:58884/media/generate'
body = {
    'prompt': 'A majestic dragon flying over a mountain, photorealistic',
    'type': 'image',
    'width': 512,
    'height': 512
}
print('POST', url, body)
try:
    r = requests.post(url, json=body, timeout=240)
    print('status', r.status_code)
    try:
        print(r.json())
    except Exception:
        print('non-json response')
        print(r.text[:400])
except Exception as e:
    print('request failed', e)
