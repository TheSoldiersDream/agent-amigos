
import os
import sys

# Load .env
from dotenv import load_dotenv
load_dotenv()

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from tools.scraper_tools import extract_data

text = "Flemington Race 1 at 12:30. Randwick Race 2 at 13:00."
schema = '{"races": [{"track": "string", "race_number": "integer", "start_time": "string"}]}'

print("Testing extract_data with Ollama...")
try:
    data = extract_data(text, schema)
    print("Success:", data)
except Exception as e:
    print("Error:", e)
