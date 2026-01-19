import os
import sys
# Ensure repo root is on sys.path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from fastapi.testclient import TestClient

from backend.agent_init import app

# Simple smoke test that does not depend on pytest being installed
client = TestClient(app)

# Make sure stub manager is used by temporarily monkeypatching
from backend.core import model_manager

class StubManager:
    async def generate(self, model_id, prompt, **kwargs):
        return {
            "success": True,
            "response": "```ts\nimport { test } from '@playwright/test';\n// generated test code\n```",
        }

# Monkeypatch the get_model_manager function
model_manager.get_model_manager = lambda: StubManager()

resp = client.post("/canvas/ai/playwright", json={"scenario": "user logs in and sees dashboard"})
print('Status:', resp.status_code)
print('Body:', resp.json())

# Cleanup generated file
try:
    data = resp.json()
    if data.get('file') and os.path.exists(data.get('file')):
        print('Removing generated file:', data.get('file'))
        os.remove(data.get('file'))
except Exception as e:
    print('Cleanup failed:', e)
