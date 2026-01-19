import os
import sys
import asyncio
# Ensure repo root is on sys.path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.routes.canvas_ai_routes import generate_playwright_test, PlaywrightRequest
from backend.core import model_manager

# Patch model_manager.get_model_manager to return a stub
class StubManager:
    async def generate(self, model_id, prompt, **kwargs):
        return {
            "success": True,
            "response": "```ts\nimport { test } from '@playwright/test';\n// generated test code\n```",
        }

model_manager.get_model_manager = lambda: StubManager()

async def main():
    req = PlaywrightRequest(scenario="user logs in and sees dashboard")
    res = await generate_playwright_test(req)
    print('Result keys:', res.keys())
    print('Success:', res.get('success'))
    print('File path:', res.get('file'))
    print('Code preview:', (res.get('code') or '')[:200])

    # Cleanup
    fp = res.get('file')
    if fp and os.path.exists(fp):
        print('Removing generated file:', fp)
        os.remove(fp)

if __name__ == '__main__':
    asyncio.run(main())
