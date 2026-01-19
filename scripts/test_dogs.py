
import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from tools.scraper_tools import scrape_url
s = scrape_url('https://www.thedogs.com.au')
print(f"Success: {s['success']}")
print(f"Text Snippet: {s.get('text', '')[:200]}")
