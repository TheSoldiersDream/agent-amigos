#!/usr/bin/env python3
"""Test with skill system message like frontend sends"""

import sys
sys.path.insert(0, '.')

from agent_init import agent, ChatMessage

print("=" * 70)
print("Testing with Architect Skill System Message")
print("=" * 70)

architect_prompt = """You are a professional architect with expertise in building design, structural planning, blueprints, and construction. **CRITICAL TOOL USAGE: You MUST use the 'canvas_design' tool when users ask you to design, draw, sketch, show, create, or plan any layout, floor plan, building, room, or structure.** DO NOT just describe designs in words - ALWAYS call canvas_design tool with the design goal."""

messages = [
    ChatMessage(role="system", content=architect_prompt),
    ChatMessage(role="user", content="design a two bedroom tropical home")
]

import asyncio
response = asyncio.run(agent.process(messages, require_approval=False))

print(f"\nResponse Content: {response.content}")
print(f"Canvas Commands: {len(response.canvas_commands) if response.canvas_commands else 0}")
print(f"Actions Taken: {len(response.actions_taken) if response.actions_taken else 0}")

if response.actions_taken:
    for action in response.actions_taken:
        print(f"  - {action['tool']}: {action['result'].get('success', 'Unknown')}")

print("\n" + "=" * 70)
