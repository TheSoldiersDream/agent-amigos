import re, json, sys
from backend.tools.scraper_tools import scrape_dynamic

url = 'https://www.betr.com.au'
print('Probing', url)
res = scrape_dynamic(url, wait_for_selector='script#__NEXT_DATA__', wait_timeout=30.0, headless=False, screenshot=False)
print('Result success:', res.get('success'))
html = res.get('html') or ''
print('HTML length:', len(html))
if re.search(r'id="__NEXT_DATA__"', html):
    print('__NEXT_DATA__ present in HTML')
    m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    if m:
        s = m.group(1).strip()
        print('__NEXT_DATA__ snippet len:', len(s))
        try:
            payload = json.loads(s)
            print('Parsed JSON top keys:', list(payload.keys())[:20])
        except Exception as e:
            print('JSON parse failed:', e)
else:
    print('__NEXT_DATA__ not found in HTML')

# Save full HTML for inspection
with open('logs/betr_full.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('Wrote logs/betr_full.html')
