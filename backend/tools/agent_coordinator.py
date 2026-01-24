"""
Agent Coordinator - Multi-Agent Awareness System
=================================================
Manages coordination between Agent Amigos and all sub-agents.
Tracks agent status, engagement, and enables collaboration.

Agents:
- Agent Amigos (Main orchestrator - Claude/Groq powered)
- Ollie (Local LLM - Ollama powered)
- Scrapey (Web scraper mini-bot)
- Trainer (Game trainer agent)

Owner: Darrell Buttigieg
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from pathlib import Path
import os
import time

# ═══════════════════════════════════════════════════════════════════════════════
# AGENT STATUS ENUM
# ═══════════════════════════════════════════════════════════════════════════════

class AgentStatus(str, Enum):
    OFFLINE = "offline"      # Agent not available
    IDLE = "idle"            # Agent available but not working
    THINKING = "thinking"    # Agent processing/reasoning
    WORKING = "working"      # Agent executing a task
    WAITING = "waiting"      # Agent waiting for input/response
    ERROR = "error"          # Agent encountered an error
    COLLABORATING = "collaborating"  # Agent working with another agent


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

from config import DEFAULT_LLM_MODEL, get_default_model

def _env_true(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

PROACTIVE_MODE = _env_true(os.environ.get("AGENT_PROACTIVE_MODE", "true"))

PROACTIVE_TASKS = {
    "amigos": [
        "Orchestrating agent tasks and priorities",
        "Reviewing outcomes and next actions",
    ],
    "ceo": [
        "Reviewing KPI dashboard and assigning owners",
        "Scanning revenue pipeline for blockers",
        "Aligning priorities with company mission",
    ],
    "general_manager": [
        "Refreshing roadmap milestones",
        "Unblocking cross-team dependencies",
    ],
    "concierge": [
        "Sorting intake requests and clarifying scope",
        "Routing new tasks to the right agent",
    ],
    "ops": [
        "Executing automation runs and status updates",
        "Monitoring runbooks for completion",
    ],
    "quality": [
        "Validating outputs and regression checks",
        "Reviewing QA checklist for recent work",
    ],
    "scrapey": [
        "Scanning web for trending opportunities",
        "Extracting engagement signals from social feeds",
    ],
    "media": [
        "Preparing media assets for social campaigns",
        "Rendering short-form video snippets",
    ],
    "researcher": [
        "Researching competitor moves and market signals",
        "Synthesizing insights for leadership",
    ],
    "chalkboard": [
        "Sketching workflow diagrams for ops",
        "Drafting funnel visualization updates",
    ],
    "ollie": [
        "Summarizing updates for leadership",
        "Preparing quick briefs from active tasks",
    ],
    "trainer": [
        "Auditing game automation scripts",
        "Monitoring trainer workflows for stability",
    ],
}

DEFAULT_PROACTIVE_TASKS = [
    "Reviewing assigned objectives",
    "Executing proactive task sweep",
    "Logging progress updates",
]

AGENT_REGISTRY = {
    "amigos": {
        "name": "Agent Amigos",
        "emoji": "🤖",
        "color": "#8b5cf6",
        "role": "Master Orchestrator",
        "description": "The central processing unit that coordinates all departmental agents.",
        "capabilities": ["reasoning", "orchestration", "agent_management"],
        "model": get_default_model(),
        "voice_settings": {"provider": "elevenlabs", "voice_id": "Adam", "stability": 0.5, "similarity": 0.75}
    },
    "ceo": {
        "name": "CEO Agent",
        "emoji": "👑",
        "color": "#f59e0b",
        "role": "Chief Executive Officer",
        "description": "Defines vision, strategy, and revenue goals. Runs executive meetings.",
        "capabilities": ["vision", "strategy", "governance", "decision_making"],
        "model": "gpt-4o",
        "voice_settings": {"provider": "elevenlabs", "voice_id": "Josh", "stability": 0.4, "similarity": 0.8}
    },
    "cto": {
        "name": "CTO Agent",
        "emoji": "💻",
        "color": "#3b82f6",
        "role": "Chief Technology Officer",
        "description": "Owns architecture and code quality. Fixes agent deadlocks and inefficiencies.",
        "capabilities": ["architecture", "code_review", "optimization", "debugging"],
        "model": "gpt-4o",
        "voice_settings": {"provider": "elevenlabs", "voice_id": "Sam", "stability": 0.6, "similarity": 0.7}
    },
    "pm": {
        "name": "Product Manager Agent",
        "emoji": "📋",
        "color": "#10b981",
        "role": "Product & Roadmap",
        "description": "Identifies monetizable problems and defines MVPs/roadmaps.",
        "capabilities": ["product_specs", "roadmap", "user_research"],
        "model": "gpt-4o",
        "voice_settings": {"provider": "elevenlabs", "voice_id": "Serena", "stability": 0.5, "similarity": 0.7}
    },
    "engineering": {
        "name": "Engineering Team",
        "emoji": "⚡",
        "color": "#6366f1",
        "role": "Full-stack Engineering",
        "description": "Builds frontend, backend, and implements features autonomously.",
        "capabilities": ["coding", "frontend", "backend", "deployment"],
        "model": "gpt-4o",
        "voice_settings": {"provider": "elevenlabs", "voice_id": "Charlie", "stability": 0.55, "similarity": 0.65}
    },
    "ops": {
        "name": "Operations Agent",
        "emoji": "⚙️",
        "color": "#64748b",
        "role": "Operations & MCP",
        "description": "Schedules tasks, logs actions, and enforces deadlines. Prevents loops.",
        "capabilities": ["scheduling", "mcp_enforcement", "deadlines", "logging"],
        "model": "gpt-4o",
        "voice_settings": {"provider": "elevenlabs", "voice_id": "Antoni", "stability": 0.5, "similarity": 0.8}
    },
    "marketing": {
        "name": "Marketing Agent",
        "emoji": "📢",
        "color": "#ec4899",
        "role": "Traffic & Funnels",
        "description": "Builds traffic funnels, schedules social posts, and tracks conversion.",
        "capabilities": ["seo", "social_media", "content_generation", "analytics"],
        "model": "gpt-4o",
        "voice_settings": {"provider": "elevenlabs", "voice_id": "Gigi", "stability": 0.45, "similarity": 0.75}
    },
    "sales": {
        "name": "Sales Agent",
        "emoji": "💰",
        "color": "#14b8a6",
        "role": "Conversion & Revenue",
        "description": "Designs offers, pricing, and builds landing pages with CTAs.",
        "capabilities": ["pricing", "offers", "sales_funnel", "monetization"],
        "model": "gpt-4o",
        "voice_settings": {"provider": "elevenlabs", "voice_id": "Bill", "stability": 0.4, "similarity": 0.85}
    },
    "finance": {
        "name": "Finance Agent",
        "emoji": "🧾",
        "color": "#f97316",
        "role": "Finance & P&L",
        "description": "Tracks costs vs revenue. Produces weekly P&L reports.",
        "capabilities": ["finance_tracking", "p_and_l", "roi_analysis"],
        "model": "gpt-4o",
        "voice_settings": {"provider": "elevenlabs", "voice_id": "Daniel", "stability": 0.7, "similarity": 0.6}
    },
    "legal": {
        "name": "Legal Agent",
        "emoji": "⚖️",
        "color": "#475569",
        "role": "Compliance & Risk",
        "description": "Flags legal/platform risks and ensures safe monetization.",
        "capabilities": ["compliance", "risk_mitigation", "contracts"],
        "model": "gpt-4o",
        "voice_settings": {"provider": "elevenlabs", "voice_id": "Alice", "stability": 0.8, "similarity": 0.5}
    },
    "ollie": {
        "name": "Ollie",
        "emoji": "🦙",
        "color": "#22c55e",
        "role": "Assistant Agent",
        "description": "Fast local assistant for short tasks and summaries.",
        "capabilities": ["quick_answers", "summarization"],
        "model": "llama3.2:latest",
        "voice_settings": {"provider": "ollama", "model": "llama3.2"}
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT COORDINATOR CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class AgentCoordinator:
    """
    Coordinates multiple agents, tracks their status, and enables collaboration.
    """
    
    def __init__(self):
        self.agents: Dict[str, Dict] = {}
        self.engagement_log: List[Dict] = []
        self.communication_log: List[Dict] = []
        self.active_collaborations: List[Dict] = []
        self.active_tools: Dict[str, Dict] = {}  # Track active tools per agent
        self.demo_progress: Dict = {}  # Track demo progress
        self.proactive_enabled = PROACTIVE_MODE
        
        # Initialize all agents
        for agent_id, agent_info in AGENT_REGISTRY.items():
            self.agents[agent_id] = {
                **agent_info,
                "id": agent_id,
                "status": AgentStatus.IDLE if agent_id == "amigos" else AgentStatus.OFFLINE,
                "last_activity": None,
                "current_task": None,
                "current_tool": None,  # Track current tool
                "todo_list": [],       # Track to-do tasks for progress
                "tasks_completed": 0,
                "errors": 0,
                "uptime_start": datetime.now().isoformat() if agent_id == "amigos" else None,
                "auto_task": False,
                "auto_task_index": 0,
                "auto_last_tick": 0.0,
            }
    
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get agent info by ID."""
        return self.agents.get(agent_id)
    
    def get_all_agents(self) -> Dict[str, Dict]:
        """Get all registered agents."""
        return self.agents
    
    def get_agent_status(self, agent_id: str) -> AgentStatus:
        """Get current status of an agent."""
        agent = self.agents.get(agent_id)
        if agent:
            return agent["status"]
        return AgentStatus.OFFLINE
    
    def set_agent_status(self, agent_id: str, status: AgentStatus, task: str = None, progress: int = None):
        """Update agent status."""
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = status
            self.agents[agent_id]["last_activity"] = datetime.now().isoformat()
            if task:
                self.agents[agent_id]["current_task"] = task
            elif status in [AgentStatus.IDLE, AgentStatus.OFFLINE]:
                self.agents[agent_id]["current_task"] = None
            
            # Update progress if provided
            # PRIORITY: If agent has a todo_list, use that progress unless forced
            todo_list = self.agents[agent_id].get("todo_list", [])
            if todo_list and progress is not None and progress < 100:
                # Calculate progress from todo_list
                completed = sum(1 for item in todo_list if item.get("status") == "completed")
                total = len(todo_list)
                todo_progress = int((completed / total) * 100)
                
                # If we are in the middle of a task, add a small offset based on the 'progress' arg
                # e.g. if 1/2 tasks done (50%) and current task is 40% done, total is 50 + (40/2) = 70%
                task_weight = 100 / total
                offset = (progress / 100) * task_weight
                self.agents[agent_id]["progress"] = min(99, int(todo_progress + offset))
            elif progress is not None:
                self.agents[agent_id]["progress"] = max(0, min(100, progress))
            elif status == AgentStatus.IDLE:
                # Keep progress at 100% if it was high, otherwise 0
                if self.agents[agent_id].get("progress", 0) > 90:
                    self.agents[agent_id]["progress"] = 100
                else:
                    self.agents[agent_id]["progress"] = 0
            elif status == AgentStatus.OFFLINE:
                self.agents[agent_id]["progress"] = 0
                self.agents[agent_id]["todo_list"] = []
            
            # Clear todo list only when starting a NEW task (Thinking/Working with 0 progress)
            if status in [AgentStatus.THINKING, AgentStatus.WORKING] and progress is not None and progress < 20:
                if not self.agents[agent_id].get("todo_list"):
                    self.agents[agent_id]["todo_list"] = []
            
            # Log engagement
            self.engagement_log.append({
                "agent": agent_id,
                "status": status,
                "task": task,
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep log size manageable
            if len(self.engagement_log) > 1000:
                self.engagement_log = self.engagement_log[-500:]
    
    def start_collaboration(self, primary_agent: str, helper_agents: List[str], task: str) -> str:
        """Start a multi-agent collaboration."""
        collab_id = f"collab_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        collaboration = {
            "id": collab_id,
            "primary": primary_agent,
            "helpers": helper_agents,
            "task": task,
            "started_at": datetime.now().isoformat(),
            "status": "active",
            "messages": []
        }
        
        self.active_collaborations.append(collaboration)

        # Log communications for collaboration start
        for helper in helper_agents:
            self.log_communication(
                primary_agent,
                helper,
                channel="collaboration_start",
                summary=task,
                payload={"collab_id": collab_id},
            )
        
        # Update agent statuses
        self.set_agent_status(primary_agent, AgentStatus.COLLABORATING, task)
        for helper in helper_agents:
            self.set_agent_status(helper, AgentStatus.COLLABORATING, f"Helping with: {task[:50]}")
        
        return collab_id
    
    def end_collaboration(self, collab_id: str, success: bool = True):
        """End a collaboration and reset agent statuses."""
        for i, collab in enumerate(self.active_collaborations):
            if collab["id"] == collab_id:
                collab["status"] = "completed" if success else "failed"
                collab["ended_at"] = datetime.now().isoformat()

                # Log collaboration end
                for helper in collab.get("helpers", []):
                    self.log_communication(
                        collab.get("primary"),
                        helper,
                        channel="collaboration_end",
                        summary=collab.get("task"),
                        payload={"collab_id": collab_id, "success": success},
                    )
                
                # Reset agent statuses
                self.set_agent_status(collab["primary"], AgentStatus.IDLE)
                for helper in collab["helpers"]:
                    self.set_agent_status(helper, AgentStatus.IDLE)
                
                # Move to history
                self.active_collaborations.pop(i)
                break
    
    def agent_working(self, agent_id: str, task: str, progress: int = None):
        """Mark an agent as working on a task."""
        self.set_agent_status(agent_id, AgentStatus.WORKING, task, progress)
    
    def agent_thinking(self, agent_id: str, task: str = None, progress: int = None):
        """Mark an agent as thinking/processing."""
        self.set_agent_status(agent_id, AgentStatus.THINKING, task, progress)
    
    def agent_idle(self, agent_id: str):
        """Mark an agent as idle."""
        self.set_agent_status(agent_id, AgentStatus.IDLE)
        if agent_id in self.agents:
            self.agents[agent_id]["tasks_completed"] += 1
    
    def agent_error(self, agent_id: str, error: str = None):
        """Mark an agent as having an error."""
        self.set_agent_status(agent_id, AgentStatus.ERROR, error)
        if agent_id in self.agents:
            self.agents[agent_id]["errors"] += 1
    
    def agent_online(self, agent_id: str):
        """Mark an agent as online/available."""
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = AgentStatus.IDLE
            self.agents[agent_id]["uptime_start"] = datetime.now().isoformat()
    
    def agent_offline(self, agent_id: str):
        """Mark an agent as offline."""
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = AgentStatus.OFFLINE
            self.agents[agent_id]["uptime_start"] = None
    
    def get_team_status(self) -> Dict:
        """Get full team status summary."""
        self._ensure_proactive_assignments()
        online_count = sum(1 for a in self.agents.values() if a["status"] != AgentStatus.OFFLINE)
        working_count = sum(1 for a in self.agents.values() if a["status"] in [AgentStatus.WORKING, AgentStatus.THINKING, AgentStatus.COLLABORATING])
        
        return {
            "agents": {aid: {
                "name": a["name"],
                "emoji": a["emoji"],
                "color": a["color"],
                "status": a["status"],
                "current_task": a["current_task"],
                "progress": a.get("progress", 0),
                "todo_list": a.get("todo_list", []),
                "current_tool": a.get("current_tool"),
                "tasks_completed": a.get("tasks_completed", 0),
                "type": a.get("type", "assistant"),
                "role": a.get("role"),
                "parent": a.get("parent"),
            } for aid, a in self.agents.items()},
            "summary": {
                "total_agents": len(self.agents),
                "online": online_count,
                "working": working_count,
                "active_collaborations": len(self.active_collaborations),
            },
            "collaborations": self.active_collaborations,
            "active_tools": self.active_tools,
            "demo_progress": self.demo_progress,
        }

    def _next_proactive_task(self, agent_id: str) -> str:
        task_pool = PROACTIVE_TASKS.get(agent_id, DEFAULT_PROACTIVE_TASKS)
        if not task_pool:
            return ""
        agent = self.agents.get(agent_id, {})
        idx = agent.get("auto_task_index", 0) % len(task_pool)
        task = task_pool[idx]
        agent["auto_task_index"] = (idx + 1) % len(task_pool)
        return task

    def _ensure_proactive_assignments(self):
        if not self.proactive_enabled:
            return

        now = time.monotonic()
        for agent_id, agent in self.agents.items():
            if agent.get("status") == AgentStatus.OFFLINE:
                agent["status"] = AgentStatus.IDLE
                agent["uptime_start"] = agent.get("uptime_start") or datetime.now().isoformat()

            status = agent.get("status")
            if status in [AgentStatus.IDLE, AgentStatus.WAITING] or not agent.get("current_task"):
                task = self._next_proactive_task(agent_id)
                if task:
                    agent["auto_task"] = True
                    agent["auto_last_tick"] = now
                    agent["current_task"] = task
                    agent["status"] = AgentStatus.WORKING
                    agent["progress"] = max(10, agent.get("progress", 0))

            if agent.get("auto_task") and agent.get("status") in [
                AgentStatus.WORKING,
                AgentStatus.THINKING,
                AgentStatus.COLLABORATING,
            ]:
                if now - agent.get("auto_last_tick", 0.0) >= 6:
                    agent["auto_last_tick"] = now
                    progress = int(agent.get("progress", 0)) + 8
                    if progress >= 100:
                        agent["progress"] = 100
                        agent["status"] = AgentStatus.IDLE
                        agent["current_task"] = None
                        agent["auto_task"] = False
                    else:
                        agent["progress"] = progress
    
    def set_agent_tool(self, agent_id: str, tool_name: str, tool_emoji: str = "🔧"):
        """Set the current tool an agent is using."""
        if agent_id in self.agents:
            self.agents[agent_id]["current_tool"] = {
                "name": tool_name,
                "emoji": tool_emoji,
                "started_at": datetime.now().isoformat()
            }
            self.active_tools[agent_id] = {
                "agent": agent_id,
                "tool": tool_name,
                "emoji": tool_emoji,
                "started_at": datetime.now().isoformat()
            }
    
    def clear_agent_tool(self, agent_id: str):
        """Clear the current tool for an agent."""
        if agent_id in self.agents:
            self.agents[agent_id]["current_tool"] = None
        if agent_id in self.active_tools:
            del self.active_tools[agent_id]

    def manage_todo_list(self, agent_id: str, operation: str, todo_list: List[Dict] = None) -> Dict:
        """
        Manage a structured todo list for an agent and update progress.
        
        Operations:
        - write: Replace entire todo list
        - read: Retrieve current todo list
        """
        if agent_id not in self.agents:
            return {"success": False, "error": f"Agent {agent_id} not found"}
            
        if operation == "read":
            return {
                "success": True, 
                "todoList": self.agents[agent_id].get("todo_list", []),
                "progress": self.agents[agent_id].get("progress", 0)
            }
            
        if operation == "write" and todo_list is not None:
            self.agents[agent_id]["todo_list"] = todo_list
            
            # Calculate progress based on completed tasks
            if not todo_list:
                self.agents[agent_id]["progress"] = 0
            else:
                completed = sum(1 for item in todo_list if item.get("status") == "completed")
                total = len(todo_list)
                progress = int((completed / total) * 100)
                self.agents[agent_id]["progress"] = progress
                
                # If all tasks are completed, we might want to set status to idle
                # but usually the agent will do that itself.
                if progress > 0 and progress < 100:
                    self.agents[agent_id]["status"] = AgentStatus.WORKING
                    # Set current task to the first in-progress item
                    in_progress = next((item for item in todo_list if item.get("status") == "in-progress"), None)
                    if in_progress:
                        self.agents[agent_id]["current_task"] = in_progress.get("title")
            
            return {
                "success": True,
                "progress": self.agents[agent_id]["progress"],
                "todoList": todo_list
            }
            
        return {"success": False, "error": "Invalid operation or missing todo_list"}

    def log_communication(
        self,
        source: str,
        target: str,
        channel: str = "message",
        summary: Optional[str] = None,
        payload: Optional[Dict] = None,
    ) -> Dict:
        """Log a communication event between agents."""
        entry = {
            "from": source,
            "to": target,
            "channel": channel,
            "summary": summary,
            "payload": payload or {},
            "timestamp": datetime.now().isoformat(),
        }
        self.communication_log.append(entry)
        if len(self.communication_log) > 2000:
            self.communication_log = self.communication_log[-1000:]
        return entry

    def get_communications(self, limit: int = 50) -> List[Dict]:
        """Get recent communication events."""
        if limit <= 0:
            return []
        return self.communication_log[-limit:]

    def get_top_contacts(self, agent_id: str, limit: int = 5) -> List[Dict]:
        """Get top communication partners for an agent."""
        counts: Dict[str, int] = {}
        for entry in self.communication_log:
            if entry.get("from") == agent_id:
                other = entry.get("to")
            elif entry.get("to") == agent_id:
                other = entry.get("from")
            else:
                continue
            if not other:
                continue
            counts[other] = counts.get(other, 0) + 1

        ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        return [
            {"agent": agent, "count": count}
            for agent, count in ranked[: max(0, limit)]
        ]
    
    def get_agent_capabilities_prompt(self) -> str:
        """Generate a prompt describing all available agents for Amigos."""
        prompt = """
## YOUR TEAM - Agent Coordination System

You are **Agent Amigos**, the **MASTER AGENT** and **LEAD ORCHESTRATOR** of a multi-agent team. 
You are the authority in this system. You work WITH these agents, but you are the one in charge:

"""
        for agent_id, agent in self.agents.items():
            if agent_id == "amigos":
                continue
            status_emoji = "🟢" if agent["status"] != AgentStatus.OFFLINE else "🔴"
            role_str = f" - **Role**: {agent.get('role').capitalize()}" if agent.get('role') else ""
            prompt += f"""
### {agent['emoji']} {agent['name']} ({agent_id.upper()}) {status_emoji}{role_str}
- **Status**: {agent['status'].value}
- **Type**: {agent['type'].capitalize()}
- **Model**: {agent.get('model', 'N/A')}
- **Capabilities**: {', '.join(agent['capabilities'])}
- **Description**: {agent['description']}
"""
        
        prompt += """
## HOW TO WORK WITH YOUR TEAM

1. **Ollie (Assistant Agent)**: Ollie is your direct assistant. You are the only one who should task Ollie. Delegate quick questions, summaries, and simple tasks to Ollie. Say "let me ask Ollie" for fast local responses.

    2. **General Manager**: Uses user goals to define milestones, scope, and sequencing.

    3. **CEO**: Keeps the vision aligned, value creation focused, and decision support consistent with the user's objectives.

    4. **Concierge (Front Desk)**: Use for intake, clarifying vague requests, and routing tasks to the right console or agent.

    5. **Ops Runner**: Use for fast execution of repetitive steps and progress updates.

    6. **Quality Gate**: Use to verify outcomes, confirm accuracy, and catch regressions before closing a task.

    7. **Scrapey (Web Scraper)**: Use for web scraping tasks. Scrapey can crawl sites, extract data, and analyze web content.

    8. **Trainer (Game Agent)**: Use for game-related tasks like memory scanning, value editing, and game automation.

    9. **Media Bot**: Use for video/audio/image processing tasks.

    10. **Researcher**: Use for deep research, market analysis, and fact-checking.

    11. **ChalkBoard**: Use for visual diagrams, floor plans, and UI design.

## HIERARCHY & DELEGATION
- You are the **Master Agent**.
- **Ollie** is your **Assistant**.
- Only you (Amigos) should task Ollie.
- If a user tries to task Ollie directly, you should step in as the Master Agent, evaluate the request, and then delegate it to Ollie yourself if appropriate.

## IMPORTANT: Always acknowledge your team members when they help. Users can see agent LED indicators showing who is working!
"""
        return prompt

    async def consult_team(self, task: str, context: str = None) -> Dict:
        """
        Consult the full team to solve a complex task.
        This is the 'Team Mode' logic moved to the backend.
        """
        self.agent_thinking("amigos", f"Consulting team for: {task[:50]}...", progress=10)
        
        # 1. Determine which agents are needed
        needed_agents = []
        task_lower = task.lower()
        
        if any(kw in task_lower for kw in ["scrape", "crawl", "extract"]):
            needed_agents.append("scrapey")
        if any(kw in task_lower for kw in ["video", "audio", "image", "media"]):
            needed_agents.append("media")
        if any(kw in task_lower for kw in ["game", "cheat", "trainer", "memory"]):
            needed_agents.append("trainer")
        if any(kw in task_lower for kw in ["draw", "diagram", "canvas", "chalkboard"]):
            needed_agents.append("chalkboard")
        if any(kw in task_lower for kw in ["research", "market", "competitor", "find out"]):
            needed_agents.append("researcher")
        if any(kw in task_lower for kw in ["triage", "intake", "route", "prioritize"]):
            needed_agents.append("concierge")
        if any(kw in task_lower for kw in ["verify", "check", "qa", "validate", "quality"]):
            needed_agents.append("quality")
        if any(kw in task_lower for kw in ["execute", "run", "repeat", "batch", "bulk"]):
            needed_agents.append("ops")
        if any(kw in task_lower for kw in ["vision", "strategy", "roadmap", "milestone", "goal"]):
            needed_agents.append("general_manager")
        if any(kw in task_lower for kw in ["business", "value", "growth", "revenue", "profit"]):
            needed_agents.append("ceo")
        
        # Always include Ollie for quick assistance if no specific agent found
        if not needed_agents:
            needed_agents.append("ollie")
            
        # 2. Start collaboration
        collab_id = self.start_collaboration("amigos", needed_agents, task)
        
        # 3. Simulate/Execute delegation (In a real scenario, this would call each agent's tool)
        results = []
        for agent_id in needed_agents:
            self.agent_working(agent_id, f"Processing sub-task for: {task[:30]}...", progress=30)
            await asyncio.sleep(1) # Simulate work
            self.agent_working(agent_id, "Finalizing results...", progress=80)
            results.append(f"{self.agents[agent_id]['name']} has processed their part.")
            await asyncio.sleep(0.5)
            self.agent_idle(agent_id)
            
        # 4. Finalize
        self.agent_working("amigos", "Synthesizing team results", progress=90)
        await asyncio.sleep(1)
        self.end_collaboration(collab_id, success=True)
        
        return {
            "success": True,
            "task": task,
            "team_results": results,
            "agents_involved": needed_agents,
            "message": f"The team has collaborated to solve your request. {', '.join([self.agents[a]['name'] for a in needed_agents])} all contributed."
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

coordinator = AgentCoordinator()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_team_status() -> Dict:
    """Get full team status."""
    return coordinator.get_team_status()

def agent_working(agent_id: str, task: str, progress: int = None):
    """Mark agent as working."""
    coordinator.agent_working(agent_id, task, progress)

def agent_thinking(agent_id: str, task: str = None, progress: int = None):
    """Mark agent as thinking."""
    coordinator.agent_thinking(agent_id, task, progress)

def agent_idle(agent_id: str):
    """Mark agent as idle."""
    coordinator.agent_idle(agent_id)

def agent_error(agent_id: str, error: str = None):
    """Mark agent as error."""
    coordinator.agent_error(agent_id, error)

def agent_online(agent_id: str):
    """Mark agent as online."""
    coordinator.agent_online(agent_id)

def agent_offline(agent_id: str):
    """Mark agent as offline."""
    coordinator.agent_offline(agent_id)

def start_collaboration(primary: str, helpers: List[str], task: str) -> str:
    """Start a collaboration."""
    return coordinator.start_collaboration(primary, helpers, task)

def end_collaboration(collab_id: str, success: bool = True):
    """End a collaboration."""
    coordinator.end_collaboration(collab_id, success)

def get_agent_prompt() -> str:
    """Get agent capabilities prompt for Amigos."""
    return coordinator.get_agent_capabilities_prompt()

def set_agent_tool(agent_id: str, tool_name: str, tool_emoji: str = "🔧"):
    """Set the tool an agent is using."""
    coordinator.set_agent_tool(agent_id, tool_name, tool_emoji)

def clear_agent_tool(agent_id: str):
    """Clear the tool for an agent."""
    coordinator.clear_agent_tool(agent_id)

def manage_todo_list(agent_id: str, operation: str, todo_list: List[Dict] = None) -> Dict:
    """Manage agent todo list."""
    return coordinator.manage_todo_list(agent_id, operation, todo_list)

def log_communication(
    source: str,
    target: str,
    channel: str = "message",
    summary: Optional[str] = None,
    payload: Optional[Dict] = None,
) -> Dict:
    """Log a communication event between agents."""
    return coordinator.log_communication(source, target, channel, summary, payload)

def get_communications(limit: int = 50) -> List[Dict]:
    """Get recent communication events."""
    return coordinator.get_communications(limit)

def get_top_contacts(agent_id: str, limit: int = 5) -> List[Dict]:
    """Get top communication partners for an agent."""
    return coordinator.get_top_contacts(agent_id, limit)


async def run_facebook_post_demo():
    """
    Run a demo that creates a Facebook post about a trending topic.
    Shows each agent doing their part with tools lit up.
    """
    import asyncio
    
    coordinator.demo_progress = {
        "status": "running",
        "current_step": 0,
        "total_steps": 8,
        "steps": [],
        "result": None
    }
    
    try:
        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Amigos analyzes the request
        # ═══════════════════════════════════════════════════════════════
        coordinator.demo_progress["current_step"] = 1
        coordinator.agent_online("amigos")
        coordinator.agent_thinking("amigos", "Analyzing request: Create Facebook post about trending topic")
        coordinator.set_agent_tool("amigos", "task_planner", "📋")
        coordinator.demo_progress["steps"].append({
            "step": 1,
            "agent": "amigos",
            "task": "Planning the multi-agent workflow",
            "tool": "task_planner",
            "status": "complete"
        })
        await asyncio.sleep(2)
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Scrapey searches for trending topics
        # ═══════════════════════════════════════════════════════════════
        coordinator.demo_progress["current_step"] = 2
        coordinator.agent_online("scrapey")
        coordinator.agent_working("scrapey", "Searching for trending topics online")
        coordinator.set_agent_tool("scrapey", "web_search", "🔍")
        coordinator.agent_working("amigos", "Coordinating Scrapey for trend search")
        coordinator.set_agent_tool("amigos", "agent_coordinator", "🎯")
        coordinator.demo_progress["steps"].append({
            "step": 2,
            "agent": "scrapey",
            "task": "Searching trending topics on social media",
            "tool": "web_search",
            "status": "complete"
        })
        await asyncio.sleep(2.5)
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 3: Scrapey scrapes trend data
        # ═══════════════════════════════════════════════════════════════
        coordinator.demo_progress["current_step"] = 3
        coordinator.agent_working("scrapey", "Extracting trend data from Twitter/X")
        coordinator.set_agent_tool("scrapey", "content_scraper", "🕷️")
        coordinator.demo_progress["steps"].append({
            "step": 3,
            "agent": "scrapey",
            "task": "Scraping trend details and hashtags",
            "tool": "content_scraper",
            "status": "complete"
        })
        await asyncio.sleep(2)
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 4: Ollie analyzes the trend
        # ═══════════════════════════════════════════════════════════════
        coordinator.demo_progress["current_step"] = 4
        coordinator.agent_online("ollie")
        coordinator.agent_thinking("ollie", "Analyzing trend: AI Technology Breakthroughs 2025")
        coordinator.set_agent_tool("ollie", "text_analysis", "📊")
        coordinator.agent_idle("scrapey")
        coordinator.clear_agent_tool("scrapey")
        coordinator.demo_progress["steps"].append({
            "step": 4,
            "agent": "ollie",
            "task": "Analyzing trend sentiment and key points",
            "tool": "text_analysis",
            "status": "complete"
        })
        await asyncio.sleep(2)
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 5: Ollie generates post content
        # ═══════════════════════════════════════════════════════════════
        coordinator.demo_progress["current_step"] = 5
        coordinator.agent_working("ollie", "Generating engaging Facebook post content")
        coordinator.set_agent_tool("ollie", "text_generator", "✍️")
        coordinator.demo_progress["steps"].append({
            "step": 5,
            "agent": "ollie",
            "task": "Writing viral post with hashtags",
            "tool": "text_generator",
            "status": "complete"
        })
        await asyncio.sleep(2.5)
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 6: Media Bot creates an image
        # ═══════════════════════════════════════════════════════════════
        coordinator.demo_progress["current_step"] = 6
        coordinator.agent_online("media")
        coordinator.agent_working("media", "Generating eye-catching post image")
        coordinator.set_agent_tool("media", "image_generator", "🎨")
        coordinator.agent_idle("ollie")
        coordinator.clear_agent_tool("ollie")
        coordinator.demo_progress["steps"].append({
            "step": 6,
            "agent": "media",
            "task": "Creating AI-themed post image",
            "tool": "image_generator",
            "status": "complete"
        })
        await asyncio.sleep(2.5)
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 7: Amigos reviews and optimizes
        # ═══════════════════════════════════════════════════════════════
        coordinator.demo_progress["current_step"] = 7
        coordinator.agent_thinking("amigos", "Reviewing and optimizing post for engagement")
        coordinator.set_agent_tool("amigos", "seo_optimizer", "📈")
        coordinator.agent_idle("media")
        coordinator.clear_agent_tool("media")
        coordinator.demo_progress["steps"].append({
            "step": 7,
            "agent": "amigos",
            "task": "Optimizing post for maximum engagement",
            "tool": "seo_optimizer",
            "status": "complete"
        })
        await asyncio.sleep(2)
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 8: Final collaboration and delivery
        # ═══════════════════════════════════════════════════════════════
        coordinator.demo_progress["current_step"] = 8
        coordinator.set_agent_status("amigos", AgentStatus.COLLABORATING, "Final review complete!")
        coordinator.set_agent_tool("amigos", "post_publisher", "📱")
        coordinator.demo_progress["steps"].append({
            "step": 8,
            "agent": "amigos",
            "task": "Post ready for publishing!",
            "tool": "post_publisher",
            "status": "complete"
        })
        await asyncio.sleep(1.5)
        
        # Generate the demo result
        demo_post = """🚀 **AI Technology Breakthroughs 2025** 🚀

The future is HERE! 🤖 From autonomous agents to local LLMs, 2025 is shaping up to be the year AI becomes truly personal.

💡 Key Trends:
• Local AI assistants running on YOUR machine
• Multi-agent collaboration (like our team!)
• Privacy-first AI solutions
• Real-time automation

What excites YOU most about AI in 2025? Drop a comment! 👇

#AI2025 #TechTrends #ArtificialIntelligence #FutureTech #Innovation #AgentAmigos

🤖 Created by Agent Amigos Team:
• 🕷️ Scrapey found the trend
• 🦙 Ollie wrote the content  
• 🎬 Media Bot designed the image
• 🤖 Amigos coordinated & optimized"""

        coordinator.demo_progress["status"] = "complete"
        coordinator.demo_progress["result"] = {
            "post_content": demo_post,
            "trending_topic": "AI Technology Breakthroughs 2025",
            "hashtags": ["#AI2025", "#TechTrends", "#ArtificialIntelligence", "#FutureTech", "#Innovation", "#AgentAmigos"],
            "agents_used": ["amigos", "scrapey", "ollie", "media"],
            "tools_used": ["task_planner", "web_search", "content_scraper", "text_analysis", "text_generator", "image_generator", "seo_optimizer", "post_publisher"]
        }
        
        # Clear all tools after demo
        await asyncio.sleep(2)
        coordinator.clear_agent_tool("amigos")
        coordinator.agent_idle("amigos")
        
        return {
            "success": True,
            "message": "Facebook post demo complete!",
            "demo_progress": coordinator.demo_progress,
            "post": demo_post
        }
        
    except Exception as e:
        coordinator.demo_progress["status"] = "error"
        coordinator.demo_progress["error"] = str(e)
        return {
            "success": False,
            "error": str(e)
        }


async def reset_team_demo():
    """Reset all agents to idle/offline state after demo."""
    coordinator.agent_idle("amigos")
    coordinator.clear_agent_tool("amigos")
    coordinator.agent_offline("ollie")
    coordinator.clear_agent_tool("ollie")
    coordinator.agent_offline("scrapey")
    coordinator.clear_agent_tool("scrapey")
    coordinator.agent_offline("trainer")
    coordinator.clear_agent_tool("trainer")
    coordinator.agent_offline("media")
    coordinator.clear_agent_tool("media")
    coordinator.demo_progress = {}
    coordinator.active_tools = {}
    
    return {
        "success": True,
        "message": "Team demo reset. Agents returned to normal state."
    }


async def get_demo_progress():
    """Get current demo progress."""
    return coordinator.demo_progress
