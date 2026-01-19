import sys
from pathlib import Path

# Fix: Ensure the PARENT of backend is in sys.path so we can import as 'backend.agent_init'
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent
root_dir = backend_dir.parent

sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(backend_dir)) # Add backend_dir so 'from autonomy' works!

print(f"sys.path: {sys.path[:2]}")
try:
    from backend.agent_init import TOOLS
    print(f"Imported TOOLS. Count: {len(TOOLS)}")
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()
