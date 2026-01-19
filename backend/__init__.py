"""Backend package for AgentAmigos.

Creating this file makes the backend importable as a Python package
so `uvicorn backend.agent_init:app` works consistently regardless of working directory.
"""
__all__ = ["agent_init"]
"""
Backend package initializer for AgentAmigos
This file marks the directory as a package to make module imports reliable
when launching the server with `uvicorn backend.agent_init:app`.
"""

__version__ = "2.0.0"
