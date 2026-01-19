import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.agents.macro.macro_autonomous import AutonomousMacroAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_macro():
    agent = AutonomousMacroAgent()
    
    goal = "Go to https://www.google.com and search for 'Agent Amigos'"
    
    print(f"Executing macro: {goal}")
    
    result = await agent.execute(
        goal=goal,
        domain="google.com",
        permission_scope="write",
        confirmation_required=False
    )
    
    print("\n--- Execution Result ---")
    print(f"Success: {result['success']}")
    print(f"Steps Executed: {result['steps_executed']}")
    print(f"Success Rate: {result['success_rate']}%")
    
    if "error" in result:
        print(f"Error: {result['error']}")
        
    print("\n--- Logs ---")
    for log in result.get('execution_log', []):
        print(f"Step {log['step']}: {log['action']} -> {log['result'].get('success', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(test_macro())
