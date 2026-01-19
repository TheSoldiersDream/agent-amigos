#!/usr/bin/env python3
"""Test canvas_design tool execution - debug narration"""

import pytest

pytest.skip("Skipping debug-only canvas design script", allow_module_level=True)

import sys
sys.path.insert(0, '.')

from tools.canvas_tools import canvas_design

print("=" * 70)
print("Testing Canvas Design Tool Execution - Debug")
print("=" * 70)

# Test the canvas_design function directly
result = canvas_design(goal="2 bedroom tropical home", narrate=True)

print("\n✓ Design result:")
print(f"  Success: {result.get('success')}")
print(f"  Narration type: {type(result.get('narration'))}")
print(f"  Narration: {repr(result.get('narration')[:100])}")

if isinstance(result.get('narration'), str):
    print(f"\n  Narration is a STRING of {len(result['narration'])} characters")
    print(f"  First line: {result['narration'].split(chr(10))[0]}")
elif isinstance(result.get('narration'), list):
    print(f"\n  Narration is a LIST of {len(result['narration'])} items")
    print(f"  First 3 items: {result['narration'][:3]}")
else:
    print(f"\n  Narration is a {type(result['narration'])}: {result['narration']}")

print("\n" + "=" * 70)
