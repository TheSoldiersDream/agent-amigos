"""
Autonomous Macro Agent - Package Initialization
"""

from .macro_autonomous import AutonomousMacroAgent, macro_autonomous_tool
from .planner import MacroPlanner
from .executor import MacroExecutor
from .perception import PerceptionEngine
from .recovery import RecoveryEngine
from .permissions import PermissionManager
from .memory import MacroMemory

__all__ = [
    'AutonomousMacroAgent',
    'macro_autonomous_tool',
    'MacroPlanner',
    'MacroExecutor',
    'PerceptionEngine',
    'RecoveryEngine',
    'PermissionManager',
    'MacroMemory'
]

__version__ = "1.0.0"
__author__ = "Darrell Buttigieg - Agent Amigos"
