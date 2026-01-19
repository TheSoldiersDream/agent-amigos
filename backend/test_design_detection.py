#!/usr/bin/env python3
"""Test design detection in agent"""

from agent_init import AgentEngine

agent = AgentEngine()

test_messages = [
    "design a 2 bedroom tropical home",
    "draw a floor plan for an office",
    "sketch a 3 bedroom house",
    "create a modern kitchen layout",
]

print("=" * 70)
print("Testing Canvas Design Detection")
print("=" * 70)

for msg in test_messages:
    result = agent.detect_required_action(msg)
    if result and result.get('tool') == 'canvas_design':
        goal = result.get('args', {}).get('goal', 'N/A')
        print(f"✓ '{msg}'")
        print(f"  → Goal: {goal}")
    else:
        print(f"✗ '{msg}'")
        if result:
            print(f"  Got: {result}")

print("=" * 70)
