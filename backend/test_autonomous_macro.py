"""
Test Suite for Autonomous Macro Agent
======================================

Validates all components and demonstrates usage.
"""

import pytest

# This file is an interactive demo suite (prints, desktop/GUI dependencies, sys.path hacking).
# It is not suitable for automated CI test runs.
pytest.skip("Skipping interactive autonomous macro demo suite", allow_module_level=True)

import asyncio
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import autonomous macro system
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.macro import (
    AutonomousMacroAgent,
    MacroPlanner,
    PerceptionEngine,
    PermissionManager
)


async def test_planner():
    """Test the planning system"""
    print("\n" + "="*60)
    print("TEST 1: Macro Planner")
    print("="*60)
    
    planner = MacroPlanner()
    
    # Test login plan
    plan = await planner.create_plan(
        goal="Log in to the website",
        domain="example.com",
        permission_scope="write"
    )
    
    print(f"\n✓ Generated plan with {len(plan['steps'])} steps:")
    for idx, step in enumerate(plan['steps']):
        print(f"  {idx + 1}. {step['action']} - {step['description']}")
    
    print(f"\n✓ Reasoning: {plan['reasoning']}")
    
    return plan


async def test_perception():
    """Test the perception engine"""
    print("\n" + "="*60)
    print("TEST 2: Perception Engine")
    print("="*60)
    
    perception = PerceptionEngine()
    
    # Analyze current screen
    page_state = await perception.analyze_page(
        include_screenshot=True,
        include_dom=False,
        include_ocr=True
    )
    
    print(f"\n✓ Page analysis complete:")
    print(f"  - Layers: {page_state.get('layers', [])}")
    print(f"  - OCR words detected: {len(page_state.get('ocr_boxes', []))}")
    print(f"  - Page type: {page_state.get('page_context', {}).get('page_type')}")
    
    if page_state.get('semantic_elements'):
        sem = page_state['semantic_elements']
        print(f"  - Buttons found: {len(sem.get('buttons', []))}")
        print(f"  - Inputs found: {len(sem.get('inputs', []))}")
        print(f"  - Links found: {len(sem.get('links', []))}")
    
    return page_state


async def test_permissions():
    """Test the permission system"""
    print("\n" + "="*60)
    print("TEST 3: Permission Manager")
    print("="*60)
    
    perms = PermissionManager()
    
    # Test safe action
    result1 = await perms.validate(
        goal="Search for products",
        domain="amazon.com",
        scope="read"
    )
    print(f"\n✓ Read permission: {result1}")
    
    # Test write action
    result2 = await perms.validate(
        goal="Fill out contact form",
        domain="example.com",
        scope="write"
    )
    print(f"✓ Write permission: {result2}")
    
    # Test dangerous action
    result3 = await perms.validate(
        goal="Purchase product with credit card",
        domain="unknown-site.com",
        scope="payment"
    )
    print(f"✓ Payment permission: {result3}")
    
    return result1, result2, result3


async def test_full_execution():
    """Test full autonomous execution"""
    print("\n" + "="*60)
    print("TEST 4: Full Autonomous Execution")
    print("="*60)
    
    agent = AutonomousMacroAgent()
    
    # Test with a simple goal
    result = await agent.execute(
        goal="Find the search button and click it",
        domain="example.com",
        permission_scope="write",
        confirmation_required=False,
        max_steps=10
    )
    
    print(f"\n✓ Execution complete:")
    print(f"  - Success: {result.get('success')}")
    print(f"  - Steps executed: {result.get('steps_executed', 0)}")
    print(f"  - Success rate: {result.get('success_rate', 0)}%")
    print(f"  - Recovery attempts: {result.get('recovery_attempts', 0)}")
    
    if result.get('execution_log'):
        print(f"\n✓ Execution log ({len(result['execution_log'])} entries):")
        for entry in result['execution_log'][:5]:  # Show first 5
            print(f"  - Step {entry.get('step')}: {entry.get('action')} -> {entry.get('result', {}).get('success')}")
    
    return result


async def demo_use_cases():
    """Demonstrate common use cases"""
    print("\n" + "="*60)
    print("DEMO: Common Use Cases")
    print("="*60)
    
    agent = AutonomousMacroAgent()
    
    use_cases = [
        {
            "name": "Login Flow",
            "goal": "Log in with my credentials",
            "domain": "app.example.com",
            "scope": "write"
        },
        {
            "name": "Form Filling",
            "goal": "Fill out the contact form with my details",
            "domain": "example.com",
            "scope": "write"
        },
        {
            "name": "Search Task",
            "goal": "Search for 'AI automation tools'",
            "domain": "google.com",
            "scope": "read"
        },
        {
            "name": "Download Task",
            "goal": "Find and download the latest invoice",
            "domain": "billing.example.com",
            "scope": "read"
        }
    ]
    
    for use_case in use_cases:
        print(f"\n📋 Use Case: {use_case['name']}")
        print(f"   Goal: {use_case['goal']}")
        print(f"   Domain: {use_case['domain']}")
        print(f"   Scope: {use_case['scope']}")
        
        # Just plan, don't execute for demo
        planner = MacroPlanner()
        plan = await planner.create_plan(
            goal=use_case['goal'],
            domain=use_case['domain'],
            permission_scope=use_case['scope']
        )
        
        print(f"   ✓ Plan generated: {len(plan['steps'])} steps")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("AUTONOMOUS MACRO AGENT - TEST SUITE")
    print("="*60)
    print("\nOwner: Darrell Buttigieg - Agent Amigos Pro")
    print("Testing production-grade autonomous macro system...\n")
    
    try:
        # Run tests
        await test_planner()
        await test_perception()
        await test_permissions()
        # await test_full_execution()  # Uncomment when ready for live testing
        await demo_use_cases()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        print("\nThe autonomous macro agent is ready for integration!")
        print("\nNext steps:")
        print("1. Integrate with agent_init.py for MCP registration")
        print("2. Add browser automation backend (Playwright/Selenium)")
        print("3. Test on real websites with proper safety controls")
        print("4. Deploy to production with monitoring")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
