"""
Intent → Plan Pipeline
======================

Converts natural language goals into structured execution plans.
Uses LLM reasoning to break down complex tasks into atomic steps.
"""

import logging
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)


class MacroPlanner:
    """
    Creates execution plans from natural language intent.
    """
    
    def __init__(self):
        self.plan_templates = self._load_plan_templates()
        logger.info("✓ Macro Planner initialized")
    
    async def create_plan(
        self,
        goal: str,
        domain: Optional[str] = None,
        memory_context: Optional[Dict] = None,
        permission_scope: str = "read"
    ) -> Dict[str, Any]:
        """
        Generate a structured execution plan from natural language.
        
        Args:
            goal: User's natural language intent
            domain: Target website domain
            memory_context: Relevant past executions
            permission_scope: Permission level for safety checks
            
        Returns:
            Structured plan with steps, reasoning, and metadata
        """
        logger.info(f"Planning for goal: {goal}")
        
        # Check for template matches
        template_plan = self._match_template(goal, domain, memory_context)
        if template_plan:
            logger.info(f"✓ Using template: {template_plan['name']}")
            return template_plan
        
        # Generate custom plan using reasoning
        plan = await self._generate_plan(goal, domain, permission_scope, memory_context)
        
        return plan
    
    def _match_template(
        self,
        goal: str,
        domain: Optional[str],
        memory_context: Optional[Dict]
    ) -> Optional[Dict]:
        """Check if goal matches a known template pattern"""
        goal_lower = goal.lower()
        
        # Login patterns
        if any(word in goal_lower for word in ['log in', 'login', 'sign in', 'signin']):
            return self._create_login_plan(domain)
        
        # Form filling patterns
        if any(word in goal_lower for word in ['fill form', 'submit form', 'complete form']):
            return self._create_form_fill_plan(goal, domain)
        
        # Search patterns
        if any(word in goal_lower for word in ['search for', 'find', 'look for']):
            return self._create_search_plan(goal, domain)
        
        # Download patterns
        if 'download' in goal_lower:
            return self._create_download_plan(goal, domain)
        
        return None
    
    async def _generate_plan(
        self,
        goal: str,
        domain: Optional[str],
        permission_scope: str,
        memory_context: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Generate a custom plan using LLM reasoning.
        
        This breaks down the goal into:
        1. Observable conditions (what to look for)
        2. Actions to take
        3. Verification steps
        4. Error recovery strategies
        """
        
        # Parse goal into components
        components = self._parse_goal(goal)
        
        steps = []
        reasoning = []
        
        # Step 1: Navigate to domain (if specified)
        if domain:
            steps.append({
                "action": "navigate",
                "target": domain,
                "description": f"Navigate to {domain}",
                "verification": {
                    "type": "url_contains",
                    "value": domain
                },
                "requires_confirmation": False
            })
            reasoning.append(f"Navigate to target domain: {domain}")
        
        # Step 2: Break down goal into atomic actions
        if "login" in goal.lower() or "sign in" in goal.lower():
            steps.extend(self._generate_login_steps())
            reasoning.append("Detected login requirement - added authentication steps")
        
        if "search" in goal.lower() or "find" in goal.lower():
            search_term = self._extract_search_term(goal)
            steps.extend(self._generate_search_steps(search_term))
            reasoning.append(f"Search for: {search_term}")
        
        if "download" in goal.lower():
            steps.extend(self._generate_download_steps())
            reasoning.append("Added download steps with file verification")
        
        if "submit" in goal.lower() or "send" in goal.lower():
            steps.append({
                "action": "submit_form",
                "description": "Submit form data",
                "verification": {
                    "type": "visual_confirmation",
                    "expected": ["success", "confirmation", "thank you"]
                },
                "requires_confirmation": permission_scope in ["submit", "payment"]
            })
            reasoning.append("Submit form - requires confirmation")
        
        if "screenshot" in goal.lower():
            # Extract filename if possible
            filename = "proof.png"
            if ".png" in goal.lower():
                import re
                match = re.search(r'([\w\-]+\.png)', goal.lower())
                if match:
                    filename = match.group(1)
            
            steps.append({
                "action": "screenshot",
                "path": filename,
                "description": f"Take a screenshot and save to {filename}",
                "requires_confirmation": False
            })
            reasoning.append(f"Take screenshot: {filename}")
        
        # Add verification step at end
        steps.append({
            "action": "verify_completion",
            "description": "Verify task completed successfully",
            "verification": {
                "type": "goal_achieved",
                "goal": goal
            },
            "requires_confirmation": False
        })
        
        return {
            "goal": goal,
            "domain": domain,
            "permission_scope": permission_scope,
            "steps": steps,
            "reasoning": reasoning,
            "estimated_duration": len(steps) * 2,  # seconds
            "recovery_enabled": True
        }
    
    def _create_login_plan(self, domain: Optional[str]) -> Dict[str, Any]:
        """Template plan for login flows"""
        return {
            "name": "login_template",
            "goal": "Log in to website",
            "domain": domain,
            "steps": [
                {
                    "action": "find_element",
                    "target": "username_input",
                    "description": "Locate username/email field",
                    "selectors": {
                        "aria_labels": ["email", "username", "user"],
                        "input_types": ["email", "text"],
                        "visual_hints": ["email", "username", "user id"]
                    }
                },
                {
                    "action": "type_text",
                    "target": "username_input",
                    "description": "Enter username",
                    "requires_confirmation": False
                },
                {
                    "action": "find_element",
                    "target": "password_input",
                    "description": "Locate password field",
                    "selectors": {
                        "input_types": ["password"],
                        "aria_labels": ["password", "pass"],
                        "visual_hints": ["password"]
                    }
                },
                {
                    "action": "type_text",
                    "target": "password_input",
                    "description": "Enter password",
                    "requires_confirmation": False
                },
                {
                    "action": "find_element",
                    "target": "submit_button",
                    "description": "Locate login button",
                    "selectors": {
                        "button_text": ["log in", "sign in", "login", "signin", "submit"],
                        "aria_roles": ["button"],
                        "visual_hints": ["log in", "sign in"]
                    }
                },
                {
                    "action": "click",
                    "target": "submit_button",
                    "description": "Click login button",
                    "verification": {
                        "type": "url_changed",
                        "timeout": 5
                    },
                    "requires_confirmation": False
                }
            ],
            "reasoning": ["Standard login flow with username and password"],
            "recovery_enabled": True
        }
    
    def _create_form_fill_plan(self, goal: str, domain: Optional[str]) -> Dict[str, Any]:
        """Template plan for form filling"""
        return {
            "name": "form_fill_template",
            "goal": goal,
            "domain": domain,
            "steps": [
                {
                    "action": "analyze_form",
                    "description": "Identify all form fields",
                    "requires_confirmation": False
                },
                {
                    "action": "fill_fields",
                    "description": "Fill form fields intelligently",
                    "requires_confirmation": True
                },
                {
                    "action": "submit_form",
                    "description": "Submit the completed form",
                    "requires_confirmation": True
                }
            ],
            "reasoning": ["Detected form filling task - requires field analysis"],
            "recovery_enabled": True
        }
    
    def _create_search_plan(self, goal: str, domain: Optional[str]) -> Dict[str, Any]:
        """Template plan for search operations"""
        search_term = self._extract_search_term(goal)
        
        return {
            "name": "search_template",
            "goal": goal,
            "domain": domain,
            "steps": [
                {
                    "action": "find_element",
                    "target": "search_input",
                    "description": "Locate search field",
                    "selectors": {
                        "input_types": ["search", "text"],
                        "aria_labels": ["search"],
                        "visual_hints": ["search"]
                    }
                },
                {
                    "action": "type_text",
                    "target": "search_input",
                    "value": search_term,
                    "description": f"Type search query: {search_term}",
                    "requires_confirmation": False
                },
                {
                    "action": "press_key",
                    "key": "enter",
                    "description": "Submit search",
                    "requires_confirmation": False
                },
                {
                    "action": "wait_for_results",
                    "description": "Wait for search results to load",
                    "timeout": 5
                }
            ],
            "reasoning": [f"Search for: {search_term}"],
            "recovery_enabled": True
        }
    
    def _create_download_plan(self, goal: str, domain: Optional[str]) -> Dict[str, Any]:
        """Template plan for download operations"""
        return {
            "name": "download_template",
            "goal": goal,
            "domain": domain,
            "steps": [
                {
                    "action": "find_element",
                    "target": "download_link",
                    "description": "Locate download link or button",
                    "selectors": {
                        "link_text": ["download"],
                        "button_text": ["download"],
                        "aria_labels": ["download"],
                        "visual_hints": ["download", "⬇"]
                    }
                },
                {
                    "action": "click",
                    "target": "download_link",
                    "description": "Click download",
                    "requires_confirmation": False
                },
                {
                    "action": "verify_download",
                    "description": "Verify file download started",
                    "timeout": 10
                }
            ],
            "reasoning": ["Download file - verify download completion"],
            "recovery_enabled": True
        }
    
    def _parse_goal(self, goal: str) -> Dict[str, Any]:
        """Extract actionable components from goal"""
        return {
            "raw": goal,
            "keywords": goal.lower().split(),
            "intent": self._classify_intent(goal),
            "entities": self._extract_entities(goal)
        }
    
    def _classify_intent(self, goal: str) -> str:
        """Classify the primary intent of the goal"""
        goal_lower = goal.lower()
        
        if any(word in goal_lower for word in ['login', 'log in', 'sign in']):
            return "authenticate"
        elif any(word in goal_lower for word in ['search', 'find', 'look for']):
            return "search"
        elif 'download' in goal_lower:
            return "download"
        elif any(word in goal_lower for word in ['fill', 'complete', 'submit']):
            return "form_fill"
        elif any(word in goal_lower for word in ['navigate', 'go to', 'open']):
            return "navigate"
        else:
            return "complex"
    
    def _extract_entities(self, goal: str) -> Dict[str, List[str]]:
        """Extract named entities from goal"""
        # Simple keyword extraction (can be enhanced with NER)
        words = goal.split()
        return {
            "actions": [w for w in words if w.lower() in ['click', 'type', 'search', 'download', 'submit']],
            "targets": []  # Would need NER for better extraction
        }
    
    def _extract_search_term(self, goal: str) -> str:
        """Extract search query from goal"""
        goal_lower = goal.lower()
        
        # Look for patterns like "search for X" or "find X"
        for pattern in ['search for ', 'find ', 'look for ']:
            if pattern in goal_lower:
                idx = goal_lower.index(pattern) + len(pattern)
                return goal[idx:].strip()
        
        return goal
    
    def _generate_login_steps(self) -> List[Dict]:
        """Generate standard login steps"""
        return self._create_login_plan(None)["steps"]
    
    def _generate_search_steps(self, search_term: str) -> List[Dict]:
        """Generate search execution steps"""
        return self._create_search_plan(f"search for {search_term}", None)["steps"]
    
    def _generate_download_steps(self) -> List[Dict]:
        """Generate download execution steps"""
        return self._create_download_plan("download file", None)["steps"]
    
    def _load_plan_templates(self) -> Dict[str, Any]:
        """Load pre-built plan templates"""
        return {
            "login": self._create_login_plan(None),
            "search": self._create_search_plan("search", None),
            "download": self._create_download_plan("download", None)
        }
