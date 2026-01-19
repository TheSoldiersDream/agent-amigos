
import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.join(os.getcwd(), 'backend'))
from horse_racing_intelligence.ingestion import discover_active_tracks

print("Discovering active tracks via web search...")
tracks = discover_active_tracks()
print(f"Found {len(tracks)} tracks.")
if tracks:
    print("Tracks:", tracks)
