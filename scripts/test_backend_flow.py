import urllib.request, time, json

BASE = 'http://127.0.0.1:65252'

def get(path, timeout=5):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return f"ERROR: {e}"

print("P1 (initial status):")
print(json.dumps(get('/horse/providers/status'), indent=2))

print("\nTriggering live schedule (up to 40s)...")
res = get('/horse/live/schedule', timeout=40)
print("Schedule response sample:", str(res)[:200])

time.sleep(1)
print("\nP2 (status after schedule call):")
print(json.dumps(get('/horse/providers/status'), indent=2))
