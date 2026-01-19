import re, json, sys
from backend.tools.scraper_tools import scrape_dynamic

url = 'https://www.betr.com.au'
print('Probing', url)
res = scrape_dynamic(url, wait_for_selector='script#__NEXT_DATA__', wait_timeout=30.0, headless=False, screenshot=True)
print('Result success:', res.get('success'))
print('Screenshot:', res.get('screenshot'))
text = res.get('text') or res.get('html') or ''
print('Text length:', len(text))
if text:
    m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.DOTALL | re.IGNORECASE)
    if m:
        s = m.group(1).strip()
        print('__NEXT_DATA__ snippet (first 1000 chars):')
        print(s[:1000])
        try:
            payload = json.loads(s)
            print('Parsed JSON top keys:', list(payload.keys())[:10])
        except Exception as e:
            print('JSON parse failed:', e)

# Save diagnostic output to a file for inspection
out = {'success': res.get('success'), 'screenshot': res.get('screenshot'), 'text_sample': (text or '')[:2000]}
with open('logs/betr_diagnostic.json', 'w', encoding='utf-8') as f:
    import json
    json.dump(out, f, ensure_ascii=False, indent=2)
print('Wrote logs/betr_diagnostic.json')
