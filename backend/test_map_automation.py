
import asyncio
import json
from core.adaptive_agent import get_or_create_agent

async def test_map_automation():
    agent = get_or_create_agent("Amigos")
    task = "Show me a map of London"
    
    print(f"Executing task: {task}")
    result = await agent.execute_task(task)
    
    print("\n--- Agent Response ---")
    print(result.get("response"))
    
    print("\n--- Tools Used ---")
    print(result.get("tools_used"))
    
    print("\n--- Map Commands ---")
    print(result.get("map_commands"))
    
    if not result.get("map_commands"):
        print("\n❌ ERROR: No map_commands found in response!")
    else:
        print("\n✅ SUCCESS: map_commands found!")

if __name__ == "__main__":
    asyncio.run(test_map_automation())
