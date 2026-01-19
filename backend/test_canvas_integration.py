"""
Test Canvas Design Tool Integration
"""

import pytest

# This file is a standalone script (prints, sys.exit on import) and is not suitable for pytest.
pytest.skip("Skipping legacy canvas integration script", allow_module_level=True)

import sys
sys.path.insert(0, '.')

print("=" * 60)
print("Testing Canvas Design Tool Integration")
print("=" * 60)

# Test 1: Import
print("\n1. Testing import...")
try:
    from tools.canvas_tools import canvas_design
    print("✓ canvas_design imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Check TOOLS registry
print("\n2. Checking TOOLS registry...")
try:
    from agent_init import TOOLS
    if "canvas_design" in TOOLS:
        print("✓ canvas_design found in TOOLS registry")
        tool_func, requires_approval, description = TOOLS["canvas_design"]
        print(f"  Description: {description}")
        print(f"  Requires approval: {requires_approval}")
    else:
        print("✗ canvas_design NOT in TOOLS registry")
        print(f"Available tools: {list(TOOLS.keys())[:10]}...")
except Exception as e:
    print(f"✗ Failed to check registry: {e}")

# Test 3: Execute simple design
print("\n3. Testing design execution...")
try:
    result = canvas_design(goal="Simple test room", narrate=False)
    print(f"✓ Design executed")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Action: {result.get('action', 'unknown')}")
    if result.get('canvas_commands'):
        print(f"  Canvas commands generated: {len(result['canvas_commands'])}")
    if result.get('error'):
        print(f"  Error: {result['error']}")
except Exception as e:
    print(f"✗ Execution failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Integration test complete")
print("=" * 60)
