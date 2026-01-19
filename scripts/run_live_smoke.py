import urllib.request, json, sys, time
import requests

BASE = 'http://127.0.0.1:65252'
FRONTEND = 'http://127.0.0.1:5173'

def get_json(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as r:
            return json.load(r)
    except Exception as e:
        print(f"GET {path} -> ERROR: {e}")
        return None

print('Checking providers status...')
ps = get_json('/horse/providers/status')
print('providers_status ->', json.dumps(ps, indent=2)[:1000])

print('\nChecking live schedule...')
ls = get_json('/horse/live/schedule')
print('live_schedule ->', json.dumps(ls, indent=2)[:1000])

print('\nTesting SSE stream (reading up to 10s)')
try:
    with requests.get(BASE + '/horse/sse/schedules', stream=True, timeout=15) as r:
        if r.status_code != 200:
            print('SSE request failed, status', r.status_code)
        else:
            started = time.time()
            for line in r.iter_lines(decode_unicode=True):
                if line:
                    l = line.strip()
                    if l.startswith('data:'):
                        payload = l[len('data:'):].strip()
                        try:
                            obj = json.loads(payload)
                            print('SSE payload received, keys:', list(obj.keys()))
                            print('Sample schedules count:', len(obj.get('schedules', [])))
                            break
                        except Exception as e:
                            print('Invalid SSE JSON payload:', e)
                if time.time() - started > 10:
                    print('SSE read timeout')
                    break
except Exception as e:
    print('SSE connection error:', e)

print('\nChecking frontend root...')
try:
    r = urllib.request.urlopen(FRONTEND, timeout=5)
    html = r.read(200).decode('utf-8', errors='ignore')
    print('Frontend ok, snippet:', html[:200])
except Exception as e:
    print('Frontend error:', e)

print('\nSMOKE TEST COMPLETE')
