from backend.horse_racing_intelligence.web_search_provider import WebSearchProvider

p = WebSearchProvider()
res = p.discover_upcoming_races_from_url('https://www.betr.com.au', limit=15)
print('Result keys:', list(res.keys()))
print('Races count:', len(res.get('races') or []))
if res.get('races'):
    for r in res.get('races')[:10]:
        print(r)
else:
    print('No races found; diagnostic:', res.get('diagnostic') or res.get('error'))
