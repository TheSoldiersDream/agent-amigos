from backend.tools.scraper_tools import scrape_dynamic
import re, json

url = 'https://www.betr.com.au'
# Try clicking the 'Next To Jump' or similar UI and waiting for the racing listing to update
actions = [
    {"type": "wait", "seconds": 2},
    # Try clicking a tab or link that matches text 'Next To Jump' - use common selectors
    {"type": "click", "selector": "text=Next To Jump", "timeout": 10000},
    {"type": "wait", "seconds": 3},
    # Try clicking possible 'View more' to expand lists
    {"type": "click", "selector": "text=View more", "timeout": 10000},
    {"type": "wait", "seconds": 2},
]

print('Running headful scripted probe...')
res = scrape_dynamic(url, wait_for_selector='body', wait_timeout=60.0, actions=actions, headless=False, screenshot=True)
print('Success:', res.get('success'))
print('Screenshot:', res.get('screenshot'))
html = res.get('html') or ''
print('HTML length:', len(html))

# Attempt to find __NEXT_DATA__ in the resulting page
m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
if m:
    s = m.group(1).strip()
    print('__NEXT_DATA__ snippet length:', len(s))
    try:
        payload = json.loads(s)
        print('JSON keys:', list(payload.keys())[:20])
    except Exception as e:
        print('JSON parse failed:', e)
else:
    print('__NEXT_DATA__ not found after actions')

# Save diagnostic
with open('logs/betr_headful_actions.json', 'w', encoding='utf-8') as f:
    json.dump({ 'screenshot': res.get('screenshot'), 'html_len': len(html), 'next_data_found': bool(m) }, f, indent=2)
print('Wrote logs/betr_headful_actions.json')
