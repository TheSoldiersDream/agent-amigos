"""Pytest configuration for the AgentAmigos monorepo.

Many tests import backend packages like `horse_racing_intelligence.*` directly.
When running pytest from the repo root, ensure `backend/` is on sys.path.
"""

import os
import sys


_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


def pytest_configure(config):
    """Global pytest configuration.

    Keep the default test run fast and deterministic.

    Live provider scraping and LLM-backed extraction are intentionally disabled
    unless the user explicitly opts in.
    """

    # Explicit opt-in for true live/integration runs.
    if os.environ.get("RUN_LIVE_PROVIDER_TESTS"):
        return

    # Prevent background scraping threads and Playwright from starting.
    os.environ.setdefault("HORSE_DISABLE_BACKGROUND_REFRESH", "1")
    os.environ.setdefault("HORSE_DISABLE_PLAYWRIGHT", "1")

    # Prevent unit tests from attempting LLM calls (e.g. to a local Ollama server).
    # If a developer wants to test extraction, they can set RUN_LIVE_PROVIDER_TESTS=1
    # and provide LLM_API_BASE explicitly.
    os.environ["LLM_API_BASE"] = os.environ.get("LLM_API_BASE", "")
    # Force a small timeout just in case something still calls the extractor.
    os.environ.setdefault("LLM_TIMEOUT", "5")
