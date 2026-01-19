
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from tools.web_tools import WebTools
    print("Successfully imported WebTools")
    
    web = WebTools()
    print("Successfully initialized WebTools")
    
    print("Testing web_search...")
    result = web.web_search("Agent Amigos AI", max_results=3)
    print(f"Search Result: {result}")
    
    if result.get("success"):
        print("Search SUCCESS")
    else:
        print("Search FAILED")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
