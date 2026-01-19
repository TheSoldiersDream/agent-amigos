"""
Central Tool Registry for Agent Amigos
Allows tools to be registered and accessed by different agent implementations
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Tuple

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Registry for all available tools"""
    
    def __init__(self):
        self.tools: Dict[str, Tuple[Callable, bool, str]] = {}
        self.categories: Dict[str, List[str]] = {}
    
    def register_tool(self, name: str, func: Callable, requires_approval: bool = False, description: str = "", category: str = "UTILITY"):
        """Register a new tool"""
        self.tools[name] = (func, requires_approval, description)
        
        if category not in self.categories:
            self.categories[category] = []
        
        if name not in self.categories[category]:
            self.categories[category].append(name)
            
        logger.debug(f"Registered tool: {name} in category {category}")
    
    def get_tool(self, name: str) -> Optional[Tuple[Callable, bool, str]]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def list_tools(self, category: Optional[str] = None) -> List[str]:
        """List all tool names, optionally filtered by category"""
        if category:
            return self.categories.get(category, [])
        return list(self.tools.keys())
    
    def get_tools_metadata(self) -> Dict[str, Any]:
        """Get metadata for all tools"""
        metadata = {}
        for name, (func, approval, desc) in self.tools.items():
            metadata[name] = {
                "description": desc,
                "requires_approval": approval
            }
        return metadata

# Global instance
_registry = ToolRegistry()

def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry"""
    return _registry
