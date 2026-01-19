#!/usr/bin/env python3
"""Test full chat endpoint with canvas_design"""

import sys
sys.path.insert(0, '.')
import json

from agent_init import agent
from agent_init import ChatMessage

print("=" * 70)
print("Testing Full Chat Endpoint with Design")
print("=" * 70)

# Create a chat message asking for design
messages = [
    ChatMessage(role="system", content="You are a helpful architecture assistant. CRITICAL: You MUST use the 'canvas_design' tool when users ask you to design anything."),
    ChatMessage(role="user", content="Design a 2 bedroom tropical home")
]

# Process through agent
import asyncio
response = asyncio.run(agent.process(messages, require_approval=False))

print(f"\n✓ Chat Response:")
print(f"  Content: {response.content}")
print(f"  Canvas Commands: {len(response.canvas_commands) if response.canvas_commands else 0}")

if response.canvas_commands:
    print(f"\n  First 3 commands:")
    for cmd in response.canvas_commands[:3]:
        print(f"    - {cmd.get('type')} on {cmd.get('layer')}")

if response.actions_taken:
    print(f"\n  Actions Taken: {len(response.actions_taken)}")
    for action in response.actions_taken:
        result = action.get('result', {})
        print(f"    - {action['tool']}: {result.get('success', 'Unknown')}")
        if result.get('canvas_commands'):
            print(f"      Generated {len(result.get('canvas_commands', []))} canvas commands")

print("\n" + "=" * 70)
