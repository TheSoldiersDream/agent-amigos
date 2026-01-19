"""Compatibility wrapper for legacy imports.

Several modules (e.g. `backend/agent_init.py`) historically imported Ollama helpers from
`tools.ollama_tools`. The implementation was later renamed/refactored into
`tools.ollie_tools`.

This module preserves the old import path and exposes a stable API surface.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# The canonical implementation lives in ollie_tools.
from .ollie_tools import (  # noqa: F401
    ollama_service,
    get_ollama_status,
    get_ollama_models,
)


async def ollama_generate(
    prompt: str,
    model: Optional[str] = None,
    task_type: str = "default",
    system: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    stream: bool = False,
) -> Dict[str, Any]:
    """Generate a completion using Ollama.

    This forwards to `ollama_service.generate()` and supports newer kwargs
    (system/temperature/max_tokens/stream).
    """

    return await ollama_service.generate(
        prompt=prompt,
        model=model,
        task_type=task_type,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
    )


async def ollama_chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    task_type: str = "default",
    system: Optional[str] = None,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    """Chat with Ollama using conversation history."""

    return await ollama_service.chat(
        messages=messages,
        model=model,
        task_type=task_type,
        system=system,
        temperature=temperature,
    )


async def amigos_ask_ollie(
    task: str,
    context: Optional[str] = None,
    task_type: str = "default",
    prefer_fast: bool = False,
) -> Dict[str, Any]:
    """Agent Amigos asks Ollie (local LLM) for help."""

    return await ollama_service.amigos_delegate(
        task=task,
        context=context,
        task_type=task_type,
        prefer_fast=prefer_fast,
    )


__all__ = [
    "ollama_service",
    "get_ollama_status",
    "get_ollama_models",
    "ollama_generate",
    "ollama_chat",
    "amigos_ask_ollie",
]
