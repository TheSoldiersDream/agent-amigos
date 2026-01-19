
import sys
import os

# Add the workspace root to sys.path so we can import from MCP_System
sys.path.append(os.getcwd())

try:
    from MCP_System.agents.web_search_agent import WebSearchAgent
    print("Successfully imported WebSearchAgent")
    
    agent = WebSearchAgent()
    print("Successfully initialized WebSearchAgent")
    
    # Test a simple search (mocking the request if needed, but let's try real first)
    # Note: The actual search might fail if DDG blocks the request, but we want to see if the code runs.
    print("Attempting search...")
    results = agent.perform_duckduckgo_search("Agent Amigos AI")
    
    if results:
        print(f"Found {len(results)} results.")
        print(f"First result: {results[0]}")
    else:
        print("No results found (this might be due to DDG blocking or network, but the code ran).")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
