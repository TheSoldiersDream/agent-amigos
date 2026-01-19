import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from tools.weather_tools import resolve_location_name

test_cases = [
    "the gold coast area",
    "Brisbane",
    "Eifell Tower",
    "Manila"
]

for tc in test_cases:
    resolved = resolve_location_name(tc)
    print(f"Input: '{tc}' -> Resolved: '{resolved}'")
