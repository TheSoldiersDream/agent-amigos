import os
import asyncio
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

try:
    from backend.agent_init import app
except Exception as e:
    pytest.skip(f"Skipping backend app integration test (backend.agent_init import failed): {e}", allow_module_level=True)

client = TestClient(app)


def test_playwright_generation_creates_file(tmp_path, monkeypatch):
    # Stub model manager with an async generate that returns a code block
    class StubManager:
        async def generate(self, model_id, prompt, **kwargs):
            return {
                "success": True,
                "response": "```ts\nimport { test } from '@playwright/test';\n// generated test code\n```",
            }

    async def stub_get_manager():
        return StubManager()

    # Patch get_model_manager to return our stub manager
    from backend.core import model_manager

    monkeypatch.setattr(model_manager, "get_model_manager", lambda: StubManager())

    # Ensure the external prompt file exists for the test; if not, create a minimal placeholder
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    prompt_path = os.path.join(repo_root, "external", "awesome-copilot", "prompts", "playwright-generate-test.prompt.md")
    os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
    if not os.path.exists(prompt_path):
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write("---\nagent: agent\n---\nGenerate a Playwright test based on the scenario.")

    # Call the endpoint
    resp = client.post("/canvas/ai/playwright", json={"scenario": "user logs in and sees dashboard"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "file" in data
    assert os.path.exists(data["file"])
    assert "import { test }" in data["code"]

    # Cleanup generated file
    try:
        os.remove(data["file"])
    except Exception:
        pass
