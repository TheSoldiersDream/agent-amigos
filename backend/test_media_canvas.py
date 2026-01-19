"""
Test Canvas-Media Integration
"""
import sys
sys.path.insert(0, '.')

print("=" * 70)
print("Testing Canvas-Media Integration")
print("=" * 70)

# Test 1: Check tools registered
print("\n1. Checking tool registration...")
try:
    from agent_init import TOOLS
    if "canvas_design" in TOOLS:
        print("✓ canvas_design tool found")
    if "canvas_design_image" in TOOLS:
        print("✓ canvas_design_image tool found")
    if "generate_image" in TOOLS:
        print("✓ generate_image tool found")
except Exception as e:
    print(f"✗ Failed to check tools: {e}")

# Test 2: Check function import
print("\n2. Checking function imports...")
try:
    from tools.canvas_tools import canvas_design, generate_design_image
    print("✓ Both canvas_design and generate_design_image imported")
except Exception as e:
    print(f"✗ Import failed: {e}")

# Test 3: Test generate_design_image function
print("\n3. Testing generate_design_image function...")
try:
    result = generate_design_image(
        design_description="Modern 3 bedroom house with open kitchen",
        image_type="2d",
        style="minimalist"
    )
    print(f"✓ Function executed")
    print(f"  Success: {result.get('success', False)}")
    if result.get('error'):
        print(f"  Note: {result.get('error')}")
    if result.get('image_path'):
        print(f"  Image generated: {result.get('image_path')}")
except Exception as e:
    print(f"✗ Function failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Check keyword mapping
print("\n4. Checking keyword-to-tool mapping...")
try:
    from agent_init import ACTION_KEYWORDS
    design_keywords = ["design", "draw", "sketch", "3d render", "blueprint"]
    for kw in design_keywords:
        if kw in ACTION_KEYWORDS:
            tools = ACTION_KEYWORDS[kw]
            print(f"  '{kw}' → {tools}")
except Exception as e:
    print(f"✗ Failed to check keywords: {e}")

print("\n" + "=" * 70)
print("Integration test complete")
print("=" * 70)
