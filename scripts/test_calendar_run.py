
import os
import sys

# Load .env for LLM config
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.join(os.getcwd(), 'backend'))
from horse_racing_intelligence.ingestion import get_official_calendar

print("Fetching official calendar...")
# Debug: check the scrape content first
from tools.scraper_tools import scrape_url
s = scrape_url("https://racingaustralia.horse/FreeFields/GroupAndListedRaces.aspx")
print(f"Scrape success: {s['success']}")
if s['success']:
    print(f"Text length: {len(s.get('text',''))}")
    print("Snippet:", s.get('text', '')[:500])

res = get_official_calendar()
print(f"Found {len(res)} races.")
if res:
    print("First item:", res[0])
