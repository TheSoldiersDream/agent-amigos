try:
    import sys
    import os
    from pathlib import Path
    
    # Add workspace root to sys.path
    root = Path(__file__).resolve().parent.parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    
    print(f"Importing backend.agent_init from {root}...")
    from backend.agent_init import TOOLS
    print(f"SUCCESS! TOOLS count: {len(TOOLS)}")
    
    import json
    spec_path = Path(__file__).resolve().parent / "tools.json"
    with open(spec_path, "r") as f:
        specs = json.load(f)
    spec_names = [s["name"] for s in specs]
    print(f"Tools in tools.json: {len(spec_names)}")
    
    missing = [name for name in spec_names if name not in TOOLS]
    print(f"Missing in TOOLS: {len(missing)}")
    if missing:
        print(f"Example missing: {missing[:5]}")

except Exception as e:
    import traceback
    traceback.print_exc()
