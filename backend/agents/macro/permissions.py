"""
Permission & Safety Manager
============================

Controls what the autonomous agent is allowed to do.
Implements domain whitelisting and action scope controls.
"""

import logging
from typing import Dict, Any, List, Optional
import json
import os

logger = logging.getLogger(__name__)


class PermissionManager:
    """
    Manages safety policies and permission controls for autonomous macros.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "data/macros/permissions.json"
        self.permissions = self._load_permissions()
        
        # Default permission scopes
        self.scopes = {
            "read": ["navigate", "find_element", "scroll", "screenshot"],
            "write": ["click", "type_text", "press_key", "fill_form"],
            "submit": ["submit_form", "click_submit", "press_enter"],
            "payment": ["submit_payment", "click_buy", "enter_card"]
        }
        
        # Actions requiring explicit confirmation
        self.requires_confirmation = {
            "submit_payment", "click_buy", "delete_account",
            "change_password", "submit_order", "confirm_purchase"
        }
        
        logger.info("✓ Permission Manager initialized")
    
    async def validate(
        self,
        goal: str,
        domain: Optional[str],
        scope: str
    ) -> Dict[str, Any]:
        """
        Validate if the goal is allowed under current permissions.
        
        Args:
            goal: User's stated goal
            domain: Target domain
            scope: Requested permission scope
            
        Returns:
            Dict with "allowed" bool and optional "reason"
        """
        logger.info(f"🔒 Validating permissions...")
        logger.info(f"  Goal: {goal}")
        logger.info(f"  Domain: {domain}")
        logger.info(f"  Scope: {scope}")
        
        # Check domain whitelist
        if domain and not self._is_domain_allowed(domain):
            return {
                "allowed": False,
                "reason": f"Domain not whitelisted: {domain}",
                "suggestion": "Add domain to whitelist in permissions.json"
            }
        
        # Check if scope is valid
        if scope not in self.scopes:
            return {
                "allowed": False,
                "reason": f"Invalid permission scope: {scope}",
                "valid_scopes": list(self.scopes.keys())
            }
        
        # Check for dangerous keywords
        dangerous_keywords = self._check_dangerous_keywords(goal)
        if dangerous_keywords and scope in ["submit", "payment"]:
            return {
                "allowed": False,
                "reason": f"Dangerous action detected: {dangerous_keywords}",
                "requires": "explicit_user_approval"
            }
        
        # All checks passed
        logger.info("  ✓ Permission validated")
        return {
            "allowed": True,
            "scope": scope,
            "allowed_actions": self.scopes[scope]
        }
    
    def _is_domain_allowed(self, domain: str) -> bool:
        """Check if domain is in whitelist"""
        whitelist = self.permissions.get("domain_whitelist", [])
        
        # Allow localhost and common dev domains by default
        if any(dev in domain for dev in ["localhost", "127.0.0.1", "example.com"]):
            return True
        
        # Check whitelist
        for allowed_domain in whitelist:
            if allowed_domain in domain or domain in allowed_domain:
                return True
        
        # If whitelist is empty, allow all (development mode)
        if not whitelist:
            logger.warning(f"  ⚠ Domain whitelist empty - allowing {domain}")
            return True
        
        return False
    
    def _check_dangerous_keywords(self, goal: str) -> Optional[str]:
        """Detect potentially dangerous actions"""
        goal_lower = goal.lower()
        
        dangerous_actions = {
            "payment": ["buy", "purchase", "payment", "credit card", "pay now"],
            "account_change": ["delete account", "close account", "change password"],
            "data_deletion": ["delete all", "remove all", "clear history"],
            "financial": ["transfer money", "send payment", "wire transfer"]
        }
        
        for category, keywords in dangerous_actions.items():
            if any(keyword in goal_lower for keyword in keywords):
                return category
        
        return None
    
    async def request_confirmation(
        self,
        action: str,
        details: Dict[str, Any]
    ) -> bool:
        """
        Request user confirmation for sensitive action.
        
        This would integrate with MCP's confirmation system.
        For now, returns True (auto-approve) in development.
        """
        logger.warning(f"  ⚠ Confirmation required for: {action}")
        logger.info(f"    Details: {details}")
        
        # TODO: Integrate with MCP confirmation UI
        # For now, auto-approve in development
        return True
    
    def add_domain_to_whitelist(self, domain: str):
        """Add a domain to the whitelist"""
        if "domain_whitelist" not in self.permissions:
            self.permissions["domain_whitelist"] = []
        
        if domain not in self.permissions["domain_whitelist"]:
            self.permissions["domain_whitelist"].append(domain)
            self._save_permissions()
            logger.info(f"✓ Added domain to whitelist: {domain}")
    
    def _load_permissions(self) -> Dict[str, Any]:
        """Load permissions from config file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load permissions: {e}")
        
        # Default permissions
        return {
            "domain_whitelist": [],
            "max_steps": 50,
            "require_confirmation": True,
            "allowed_scopes": ["read", "write", "submit"]
        }
    
    def _save_permissions(self):
        """Save permissions to config file"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(self.permissions, f, indent=2)
        
        logger.info(f"✓ Permissions saved to {self.config_path}")
