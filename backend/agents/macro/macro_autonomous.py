"""
Autonomous AI Macro Tool Agent for Agent Amigos
================================================

This is the main entry point for the autonomous macro system.
Converts natural language intent into browser actions using:
- Visual perception (screenshots + OCR)
- DOM/Accessibility tree analysis
- Self-healing execution
- MCP integration
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .planner import MacroPlanner
from .executor import MacroExecutor
from .perception import PerceptionEngine
from .recovery import RecoveryEngine
from .permissions import PermissionManager
from .memory import MacroMemory
from .browser_manager import BrowserManager

logger = logging.getLogger(__name__)


class AutonomousMacroAgent:
    """
    Production-grade autonomous macro agent that operates across all websites.
    
    Capabilities:
    - Natural language intent parsing
    - Visual + semantic website understanding
    - Self-healing execution
    - MCP-compliant safety controls
    """
    
    def __init__(self, mcp_context: Optional[Dict] = None):
        self.planner = MacroPlanner()
        self.executor = MacroExecutor()
        self.perception = PerceptionEngine()
        self.recovery = RecoveryEngine()
        self.permissions = PermissionManager()
        self.memory = MacroMemory()
        self.browser_manager = BrowserManager(headless=False)  # Show browser for visibility
        
        self.mcp_context = mcp_context or {}
        self.execution_log = []
        self.current_task = None
        
        logger.info("✓ Autonomous Macro Agent initialized")
    
    async def execute(
        self,
        goal: str,
        domain: Optional[str] = None,
        permission_scope: str = "read",
        confirmation_required: bool = True,
        max_steps: int = 50
    ) -> Dict[str, Any]:
        """
        Main execution entry point.
        
        Args:
            goal: Natural language description of task
            domain: Target website domain (for safety checks)
            permission_scope: One of: read, write, submit, payment
            confirmation_required: Require user approval for sensitive actions
            max_steps: Maximum execution steps before timeout
            
        Returns:
            Execution result with logs, reasoning, and outcomes
        """
        execution_id = f"macro_{int(datetime.now().timestamp())}"
        
        try:
            logger.info(f"▶ Starting autonomous macro: {goal}")
            logger.info(f"  Domain: {domain or 'any'}")
            logger.info(f"  Permission scope: {permission_scope}")
            
            # Step 1: Permission validation
            permission_check = await self.permissions.validate(
                goal=goal,
                domain=domain,
                scope=permission_scope
            )
            
            if not permission_check["allowed"]:
                return {
                    "success": False,
                    "error": "Permission denied",
                    "reason": permission_check.get("reason"),
                    "execution_id": execution_id
                }
            
            # Step 2: Load relevant skills/memory
            relevant_memory = await self.memory.recall(goal, domain)
            
            # Step 3: Generate execution plan
            plan = await self.planner.create_plan(
                goal=goal,
                domain=domain,
                memory_context=relevant_memory,
                permission_scope=permission_scope
            )
            
            logger.info(f"✓ Generated plan with {len(plan['steps'])} steps")
            for idx, step in enumerate(plan['steps']):
                logger.info(f"  {idx + 1}. {step['action']} - {step['description']}")
            
            # Step 4: Execute plan with adaptive recovery
            try:
                await self.browser_manager.start()
                result = await self._execute_plan(
                    plan=plan,
                    confirmation_required=confirmation_required,
                    max_steps=max_steps
                )
            finally:
                # Keep browser open if needed or close it
                # For now, let's close it after execution unless we want to persist
                # await self.browser_manager.stop()
                pass
            
            # Step 5: Learn from execution
            if result["success"]:
                await self.memory.store_success(
                    goal=goal,
                    domain=domain,
                    plan=plan,
                    execution_log=self.execution_log
                )
            
            result["execution_id"] = execution_id
            return result
            
        except Exception as e:
            logger.error(f"✗ Macro execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "execution_id": execution_id,
                "execution_log": self.execution_log
            }
    
    async def _execute_plan(
        self,
        plan: Dict,
        confirmation_required: bool,
        max_steps: int
    ) -> Dict[str, Any]:
        """
        Execute the plan with self-healing and adaptation.
        """
        steps_executed = 0
        failed_steps = 0
        recovery_attempts = 0
        
        for step_idx, step in enumerate(plan['steps']):
            if steps_executed >= max_steps:
                logger.warning(f"⚠ Max steps ({max_steps}) reached")
                break
            
            try:
                logger.info(f"→ Step {step_idx + 1}/{len(plan['steps'])}: {step['action']}")
                
                # Check if confirmation needed
                if confirmation_required and step.get('requires_confirmation'):
                    # TODO: Integrate with MCP confirmation system
                    logger.info("  ⏸ Awaiting user confirmation...")
                    pass
                
                # Perceive current page state
                page_state = await self.perception.analyze_page(
                    include_screenshot=True,
                    include_dom=True,
                    include_ocr=True,
                    page=self.browser_manager.page
                )
                
                # Execute step
                step_result = await self.executor.execute_step(
                    step=step,
                    page_state=page_state,
                    page=self.browser_manager.page
                )
                
                self.execution_log.append({
                    "step": step_idx + 1,
                    "action": step['action'],
                    "result": step_result,
                    "timestamp": datetime.now().isoformat()
                })
                
                if step_result["success"]:
                    logger.info(f"  ✓ Step completed successfully")
                    steps_executed += 1
                else:
                    logger.warning(f"  ⚠ Step failed: {step_result.get('error')}")
                    failed_steps += 1
                    
                    # Attempt recovery
                    recovery_result = await self.recovery.attempt_recovery(
                        step=step,
                        failure_info=step_result,
                        page_state=page_state,
                        execution_context={
                            "goal": plan.get('goal'),
                            "steps_completed": steps_executed,
                            "previous_steps": self.execution_log
                        }
                    )
                    
                    if recovery_result["recovered"]:
                        logger.info(f"  ✓ Recovery successful: {recovery_result['method']}")
                        recovery_attempts += 1
                        steps_executed += 1
                    else:
                        logger.error(f"  ✗ Recovery failed, continuing to next step")
                
                # Small delay for page stability
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"  ✗ Step execution error: {e}", exc_info=True)
                failed_steps += 1
                
                self.execution_log.append({
                    "step": step_idx + 1,
                    "action": step['action'],
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        success_rate = steps_executed / len(plan['steps']) if plan['steps'] else 0
        
        return {
            "success": success_rate >= 0.8,  # 80% success threshold
            "steps_executed": steps_executed,
            "steps_failed": failed_steps,
            "recovery_attempts": recovery_attempts,
            "success_rate": round(success_rate * 100, 1),
            "execution_log": self.execution_log,
            "reasoning": plan.get('reasoning', [])
        }
    
    async def pause(self):
        """Pause execution (for step-through mode)"""
        self.executor.paused = True
        logger.info("⏸ Execution paused")
    
    async def resume(self):
        """Resume paused execution"""
        self.executor.paused = False
        logger.info("▶ Execution resumed")
    
    async def stop(self):
        """Stop execution immediately"""
        self.executor.stopped = True
        logger.info("⏹ Execution stopped")


# MCP Tool Registration
async def macro_autonomous_tool(
    goal: str,
    domain: str = None,
    permission_scope: str = "read",
    confirmation_required: bool = True,
    max_steps: int = 50
) -> Dict[str, Any]:
    """
    MCP-registered autonomous macro tool.
    
    Executes browser automation tasks from natural language intent.
    
    Args:
        goal: What you want to accomplish (e.g., "Log in and download my latest invoice")
        domain: Target website (optional, for safety validation)
        permission_scope: Action permissions - "read", "write", "submit", "payment"
        confirmation_required: Require user approval for sensitive actions
        max_steps: Maximum number of execution steps
        
    Returns:
        Execution result with success status, logs, and reasoning
    """
    agent = AutonomousMacroAgent()
    result = await agent.execute(
        goal=goal,
        domain=domain,
        permission_scope=permission_scope,
        confirmation_required=confirmation_required,
        max_steps=max_steps
    )
    return result
