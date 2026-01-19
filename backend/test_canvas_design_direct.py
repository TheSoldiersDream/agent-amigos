#!/usr/bin/env python3
"""Test canvas_design tool execution"""

import pytest

pytest.skip("Skipping debug-only canvas design script", allow_module_level=True)

import sys
sys.path.insert(0, '.')

from tools.canvas_tools import canvas_design

print("=" * 70)
print("Testing Canvas Design Tool Execution")
print("=" * 70)

# Test the canvas_design function directly
result = canvas_design(goal="2 bedroom tropical home", narrate=True)

print("\n✓ Design result:")
print(f"  Success: {result.get('success')}")
print(f"  Goal: {result.get('goal')}")

if result.get('success'):
    print(f"\n  Canvas Commands: {len(result.get('canvas_commands', []))} commands")
    if result.get('canvas_commands'):
        print("    First 3 commands:")
        for cmd in result['canvas_commands'][:3]:
            print(f"      - {cmd.get('type')} on {cmd.get('layer')}")
    else:
        print("    ⚠️ NO CANVAS COMMANDS GENERATED!")
    
    print(f"\n  Narration ({len(result.get('narration', []))} lines):")
    for line in result.get('narration', [])[:5]:
        print(f"    - {line}")
    
    print(f"\n  Explanation: {result.get('explanation', 'N/A')[:100]}...")
else:
    print(f"\n✗ Error: {result.get('error')}")

print("\n" + "=" * 70)
