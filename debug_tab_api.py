import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_tab():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    })

    url = "https://api.beta.tab.com.au/v1/tab-info-service/racing/dates/today/meetings?jurisdiction=NSW"
    print(f"Fetching {url}")
    resp = session.get(url)
    if resp.status_code != 200:
        print(f"Failed: {resp.status_code}")
        return

    data = resp.json()
    meetings = data.get('meetings', [])
    print(f"Found {len(meetings)} meetings.")

    # Find one with active races
    for m in meetings:
        races = m.get('races', [])
        if races:
            print(f"\nChecking Meeting: {m.get('meetingName')} ({m.get('venueMnemonic')}) Location: {m.get('location')}")
            # PRINT THE WHOLE RACE OBJECT FOR THE FIRST RACE
            print("Full Race 1 Object:")
            print(json.dumps(races[0], indent=2))
            
            # Check race 1 or next active
            race = races[0]

            print(f"  Race {race.get('raceNumber')}: {race.get('_links', 'No Links')}")
            
            # Try to fetch runners using the constructed URL logic
            meeting_date = m.get('meetingDate')
            venue_code = m.get('venueMnemonic')
            race_num = race.get('raceNumber')
            
            test_urls = [
                f"https://api.beta.tab.com.au/v1/tab-info-service/racing/dates/{meeting_date}/meetings/{venue_code}/races/{race_num}?jurisdiction=NSW",
                f"https://api.beta.tab.com.au/v1/tab-info-service/racing/dates/{meeting_date}/meetings/{venue_code}/races/{race_num}?jurisdiction=VIC"
            ]
            
            for u in test_urls:
                print(f"  Testing URL: {u}")
                r = session.get(u)
                print(f"    Status: {r.status_code}")
            
            # If there's a link in the race object, print it
            if '_links' in race:
                print(f"  Race Links: {race['_links']}")

            # Only check a couple
            if m.get('location') == 'NSW' or m.get('location') == 'VIC':
                break
    
if __name__ == "__main__":
    debug_tab()
