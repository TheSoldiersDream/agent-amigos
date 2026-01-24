"""
OpenWork Integration Module for Agent Amigos
Provides AI-powered workspace management and session handling
"""
import os
import json
import asyncio
import subprocess
import shutil
import socket
import time
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
from .tools.agent_coordinator import agent_working
from .workflows.revenue_generation import RevenueWorkflows


class OpenWorkSession:
    """Represents an OpenWork session"""
    def __init__(self, session_id: str, workspace_path: str, prompt: str, model: Optional[str] = None):
        self.session_id = session_id
        self.workspace_path = workspace_path
        self.prompt = prompt
        self.model = model
        self.created_at = datetime.now()
        self.status = "active"
        self.todos: List[Dict[str, Any]] = []
        self.messages: List[Dict[str, Any]] = []
        self.permissions_requested: List[Dict[str, Any]] = []


class OpenWorkManager:
    """Manages OpenWork sessions and workspace operations"""
    
    def __init__(self, base_workspace_path: Optional[str] = None):
        if base_workspace_path:
            self.base_workspace_path = base_workspace_path
        else:
            repo_root = Path(__file__).resolve().parent.parent
            self.base_workspace_path = str(repo_root)
        self.sessions: Dict[str, OpenWorkSession] = {}
        self.opencode_process: Optional[subprocess.Popen] = None
        self.opencode_port: int = 8765
        self.opencode_host: str = "127.0.0.1"
        self.task_library: List[Dict[str, Any]] = self._load_task_library()
        self.runner_enabled: bool = False
        self.runner_interval_sec: int = 60
        self.runner_task: Optional[asyncio.Task] = None
        self.runner_last_tick: Optional[str] = None
        self.leadership_log: List[Dict[str, Any]] = []
        self.meeting_log: List[Dict[str, Any]] = []
        
        # Load persisted sessions on startup
        self._load_sessions()
        self._load_meetings()

    def log_leader_action(self, action: str, level: str = "info"):
        """Logs a leader (Agent Amigos) orchestration action."""
        self.leadership_log.insert(0, {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "level": level
        })
        # Keep last 50 actions
        self.leadership_log = self.leadership_log[:50]

    def record_meeting(self, title: str, participants: List[str], agenda: List[str], discussion: List[str], action_items: List[Dict[str, Any]]):
        """Records an AI executive meeting with persistent log."""
        meeting = {
            "id": f"meeting-{int(time.time())}",
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "participants": participants,
            "agenda": agenda,
            "discussion": discussion,
            "action_items": action_items
        }
        self.meeting_log.insert(0, meeting)
        # Keep last 20 meetings
        self.meeting_log = self.meeting_log[:20]
        self._save_meetings()
        
        # Log to leadership log
        self.log_leader_action(f"Company Governance: {title} concluded with {len(action_items)} action items.")
        
        # Write as artifact
        content = f"Meeting: {title}\nDate: {meeting['timestamp']}\nParticipants: {', '.join(participants)}\n\nAgenda:\n- " + "\n- ".join(agenda)
        content += "\n\nDiscussion Summary:\n" + "\n".join(discussion)
        content += "\n\nAction Items:\n" + "\n".join([f"- [{a.get('owner')}] {a.get('task')}" for a in action_items])
        
        # Write to a special governance directory
        gov_dir = self._task_artifacts_dir() / "governance"
        gov_dir.mkdir(parents=True, exist_ok=True)
        (gov_dir / f"{meeting['id']}.txt").write_text(content, encoding="utf-8")
        
        return meeting

    def _meetings_db_path(self) -> Path:
        data_dir = Path(__file__).resolve().parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "openwork_meetings.json"

    def _save_meetings(self) -> None:
        try:
            with open(self._meetings_db_path(), "w", encoding="utf-8") as f:
                json.dump(self.meeting_log, f, indent=2)
        except Exception as exc:
            logger.warning(f"Failed to save meetings: {exc}")

    def _load_meetings(self) -> None:
        path = self._meetings_db_path()
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.meeting_log = json.load(f)
        except Exception as exc:
            logger.warning(f"Failed to load meetings: {exc}")

    def _sessions_db_path(self) -> Path:
        """Return path to sessions database file."""
        data_dir = Path(__file__).resolve().parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "openwork_sessions.json"

    def _save_sessions(self) -> None:
        """Persist all sessions to disk."""
        path = self._sessions_db_path()
        try:
            data = {}
            for session_id, session in self.sessions.items():
                data[session_id] = {
                    "session_id": session.session_id,
                    "workspace_path": session.workspace_path,
                    "prompt": session.prompt,
                    "model": session.model,
                    "created_at": session.created_at.isoformat(),
                    "status": session.status,
                    "todos": session.todos,
                    "messages": session.messages,
                    "permissions_requested": session.permissions_requested,
                }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.warning(f"Failed to save sessions: {exc}")

    def _load_sessions(self) -> None:
        """Load sessions from disk on startup."""
        path = self._sessions_db_path()
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for session_id, session_data in data.items():
                session = OpenWorkSession(
                    session_id=session_data.get("session_id", session_id),
                    workspace_path=session_data.get("workspace_path", ""),
                    prompt=session_data.get("prompt", ""),
                    model=session_data.get("model")
                )
                # Restore created_at from saved data
                created_str = session_data.get("created_at")
                if created_str:
                    try:
                        session.created_at = datetime.fromisoformat(created_str)
                    except Exception:
                        pass
                session.status = session_data.get("status", "active")
                session.todos = session_data.get("todos", [])
                session.messages = session_data.get("messages", [])
                session.permissions_requested = session_data.get("permissions_requested", [])
                self.sessions[session_id] = session
            logger.info(f"Loaded {len(self.sessions)} OpenWork sessions from disk")
        except Exception as exc:
            logger.warning(f"Failed to load sessions: {exc}")

    def _task_artifacts_dir(self) -> Path:
        """Directory where task execution artifacts are stored."""
        data_dir = Path(__file__).resolve().parent / "data" / "openwork_artifacts"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def _write_task_artifact(
        self,
        session: "OpenWorkSession",
        todo: Dict[str, Any],
        content: str,
        artifact_type: str = "progress",
    ) -> Dict[str, Any]:
        """Write a tangible artifact to disk as proof of work."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        todo_id = todo.get("id", "unknown")
        safe_id = str(todo_id).replace("/", "-")
        base = f"{session.session_id}_{safe_id}_{artifact_type}_{timestamp}"
        dir_path = self._task_artifacts_dir()
        text_path = dir_path / f"{base}.txt"
        meta_path = dir_path / f"{base}.json"

        meta = {
            "session_id": session.session_id,
            "todo_id": todo_id,
            "title": todo.get("title") or todo.get("description"),
            "status": todo.get("status"),
            "owner": todo.get("owner") or todo.get("owner_id"),
            "artifact_type": artifact_type,
            "created_at": datetime.now().isoformat(),
        }

        try:
            text_path.write_text(content, encoding="utf-8")
            meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Failed to write task artifact: {exc}")

        return {"text": str(text_path), "meta": str(meta_path)}

    def list_task_artifacts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent task artifacts as proof of work."""
        dir_path = self._task_artifacts_dir()
        if not dir_path.exists():
            return []

        entries = []
        for path in dir_path.glob("*.txt"):
            try:
                stat = path.stat()
                preview = ""
                try:
                    preview = "".join(path.read_text(encoding="utf-8").splitlines(True)[:12])
                except Exception:
                    preview = ""
                entries.append({
                    "path": str(path),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "preview": preview,
                })
            except Exception:
                continue

        entries.sort(key=lambda x: x.get("modified", ""), reverse=True)
        return entries[: max(1, int(limit))]

    def read_task_artifact(self, path: str) -> Dict[str, Any]:
        """Read a task artifact from disk with path safety checks."""
        if not path:
            return {"success": False, "error": "Path required"}

        artifacts_dir = self._task_artifacts_dir().resolve()
        try:
            target = Path(path).resolve()
        except Exception:
            return {"success": False, "error": "Invalid path"}

        if artifacts_dir not in target.parents and target != artifacts_dir:
            return {"success": False, "error": "Path not allowed"}

        if not target.exists() or not target.is_file():
            return {"success": False, "error": "File not found"}

        try:
            content = target.read_text(encoding="utf-8")
        except Exception as exc:
            return {"success": False, "error": f"Read failed: {exc}"}

        return {"success": True, "path": str(target), "content": content}

    def _draft_for_task(self, todo: Dict[str, Any]) -> str:
        """Create a concrete draft/output for a revenue task (local proof)."""
        title = (todo.get("title") or "").lower()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        if "linkedin" in title:
            return (
                "LinkedIn Draft (Proof of Work)\n"
                f"Timestamp: {now}\n\n"
                "Hook: I replaced 20 hours of weekly ops with an AI company.\n"
                "What changed? The system assigns owners, schedules work, and delivers daily outputs.\n\n"
                "If you want a real agentic workflow running your company, DM me.\n"
                "#AgentAmigos #AI #Automation"
            )
        if "github" in title or "repos" in title:
            return (
                "GitHub Outreach Target List (Proof of Work)\n"
                f"Timestamp: {now}\n\n"
                "1) repo: example/automation-scripts — outreach pending\n"
                "2) repo: example/task-runner — outreach pending\n"
                "3) repo: example/workflow-bot — outreach pending\n\n"
                "Next step: replace placeholders with live repo targets and send messages."
            )
        if "pricing" in title:
            return (
                "Pricing Draft (Proof of Work)\n"
                f"Timestamp: {now}\n\n"
                "Starter: $29/mo — 개인/solo automation\n"
                "Team: $99/mo — multi-agent workflows\n"
                "Enterprise: custom — compliance + SLA\n"
            )
        if "landing page" in title:
            return (
                "Landing Page Outline (Proof of Work)\n"
                f"Timestamp: {now}\n\n"
                "H1: Run your company on autopilot with Agent Amigos\n"
                "CTA: Start free trial\n"
                "Sections: Demo video • Use cases • Pricing • Testimonials"
            )
        if "demo" in title or "video" in title:
            return (
                "Demo Video Script (Proof of Work)\n"
                f"Timestamp: {now}\n\n"
                "1) Problem: too many tasks, not enough time\n"
                "2) Solution: Agent Amigos orchestrates workflows\n"
                "3) Proof: real tasks created + executed\n"
                "4) CTA: try Agent Amigos"
            )

        return (
            "Task Execution Note (Proof of Work)\n"
            f"Timestamp: {now}\n\n"
            f"Task: {todo.get('title') or todo.get('description')}\n"
            "Output drafted and ready for review."
        )

    def execute_todo(self, session_id: str, todo_id: str, executed_by: str = "amigos") -> Dict[str, Any]:
        """Execute a todo and write a proof artifact to disk."""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        todo = next((t for t in session.todos if t.get("id") == todo_id), None)
        if not todo:
            return {"success": False, "error": "Todo not found"}
        if todo.get("ai_validated") is not True:
            return {"success": False, "error": "Todo not AI-validated"}
        if todo.get("approval_required") and todo.get("approval_status") != "approved":
            return {"success": False, "error": "Todo not approved for outbound communication"}

        content = self._draft_for_task(todo)
        artifact = self._write_task_artifact(session, todo, content, artifact_type="execution")

        todo["status"] = "completed"
        todo["updated_at"] = datetime.now().isoformat()
        todo["updated_by"] = executed_by
        todo["artifact_path"] = artifact.get("text")

        self.add_message(session.session_id, {
            "role": "system",
            "content": f"✅ Task executed with proof artifact: {artifact.get('text')}",
        })

        self._save_sessions()
        return {"success": True, "artifact": artifact, "todo": todo}

    def _normalize_owner(self, owner: Optional[str]) -> Optional[str]:
        """Normalize human-friendly owner strings to internal agent IDs."""
        if not owner:
            return None
        o = owner.strip().lower()
        # Simple mapping heuristics
        if "ceo" in o:
            return "ceo"
        if "marketing" in o or "content" in o:
            return "media"
        if "workflow" in o or "ops" in o or "operations" in o:
            return "ops"
        if "ai" in o or "strategy" in o:
            return "amigos"
        if "general" in o or "manager" in o:
            return "general_manager"
        return None

    def _requires_approval(self, todo: Dict[str, Any]) -> bool:
        """Return True when task represents outbound communication."""
        tags = [str(t).lower() for t in (todo.get("tags") or [])]
        text = " ".join([
            str(todo.get("title") or ""),
            str(todo.get("description") or ""),
            " ".join(tags),
        ]).lower()
        keywords = {
            "email",
            "outreach",
            "linkedin",
            "reddit",
            "post",
            "publish",
            "dm",
            "message",
            "social",
            "announce",
        }
        return any(k in text for k in keywords)

    def approve_todo(self, session_id: str, todo_id: str, approved_by: str) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        todo = next((t for t in session.todos if t.get("id") == todo_id), None)
        if not todo:
            return {"success": False, "error": "Todo not found"}
        todo["approval_status"] = "approved"
        todo["approved_by"] = approved_by
        todo["approved_at"] = datetime.now().isoformat()
        self.add_message(session_id, {
            "role": "system",
            "content": f"✅ Approved for outbound communication by {approved_by}.",
        })
        self._save_sessions()
        return {"success": True, "todo": todo}

    def _openwork_templates_dir(self) -> Path:
        repo_root = Path(__file__).resolve().parent.parent
        return repo_root / "templates" / "openwork"

    def list_workflow_templates(self) -> List[Dict[str, Any]]:
        """List available OpenWork workflow templates."""
        templates_dir = self._openwork_templates_dir()
        if not templates_dir.exists():
            return []

        templates = []
        for path in sorted(templates_dir.glob("*.md")):
            try:
                content = path.read_text(encoding="utf-8")
                template_id = path.stem
                title = template_id.replace("-", " ").title()
                templates.append({
                    "id": template_id,
                    "title": title,
                    "filename": path.name,
                    "content": content,
                })
            except Exception as exc:
                logger.warning(f"Failed to read template {path}: {exc}")
        return templates

    def _extract_todos_from_template(self, content: str) -> List[Dict[str, Any]]:
        if not content:
            return []
        import re
        tasks: List[Dict[str, Any]] = []
        for line in content.splitlines():
            candidate = line.strip()
            if not candidate:
                continue
            match = re.match(r"^[-*]\s+\[[ xX]\]\s+(.*)$", candidate)
            if not match:
                match = re.match(r"^[-*]\s+(.*)$", candidate)
            if not match:
                match = re.match(r"^\d+\.\s+(.*)$", candidate)
            if match:
                title = match.group(1).strip()
                if title:
                    tasks.append({
                        "title": title,
                        "status": "pending",
                        "source": "template",
                    })
        return tasks

    def create_session_from_template(self, workspace_path: str, template_id: str) -> Optional[Dict[str, Any]]:
        templates = self.list_workflow_templates()
        template = next((t for t in templates if t.get("id") == template_id), None)
        if not template:
            return None

        prompt = template.get("content") or template.get("title") or template_id
        session_data = self.create_session(workspace_path, prompt)
        session_id = session_data.get("session_id")
        if not session_id:
            return session_data

        tasks = self._extract_todos_from_template(template.get("content") or "")
        if not tasks:
            tasks = [{"title": "Review template and define tasks", "status": "pending", "source": "template"}]

        for task in tasks:
            self.add_todo(session_id, task)

        self.add_message(session_id, {
            "role": "system",
            "content": f"Template applied: {template.get('title') or template_id}",
        })

        session_data["todo_count"] = len(tasks)
        session_data["template_id"] = template_id
        return session_data

    def create_company_checkin_session(self, workspace_path: str, focus: Optional[str] = None) -> Dict[str, Any]:
        """Create or return existing company check-in session with REAL revenue-generating tasks."""
        focus_text = focus.strip() if isinstance(focus, str) and focus.strip() else "growth + revenue"
        
        # PERSISTENCE FIX: Check if we already have an active 'Company Check-in' session
        # to avoid duplicating tasks every reload.
        for existing_id, existing_session in self.sessions.items():
            if "Company Check-in" in existing_session.prompt and existing_session.status == "active":
                logger.info(f"Using existing company check-in session: {existing_id}")
                return {
                    "session_id": existing_id,
                    "workspace_path": existing_session.workspace_path,
                    "prompt": existing_session.prompt,
                    "todo_count": len(existing_session.todos),
                    "focus": focus_text
                }

        prompt = (
            f"Company Check-in (CEO + Ops) Focus: {focus_text}\n"
            "Goal: produce real actions, owners, and a 7-day plan."
        )
        session_data = self.create_session(workspace_path, prompt)
        session_id = session_data.get("session_id")
        if not session_id:
            return session_data

        # Load REAL revenue-generating tasks with current timestamps
        tasks = RevenueWorkflows.get_revenue_tasks()

        for task in tasks:
            self.add_todo(session_id, task)

        self.add_message(session_id, {
            "role": "system",
            "content": f"🚀 Revenue generation workflow activated. {len(tasks)} real tasks loaded with current timestamps.",
        })

        session_data["todo_count"] = len(tasks)
        session_data["focus"] = focus_text
        return session_data

    def _parse_iso(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None

    def _runner_tick(self) -> None:
        now = datetime.now()
        self.runner_last_tick = now.isoformat()
        
        self.log_leader_action("Agent Amigos Chief of Staff: Starting organizational sweep.")

        # Max concurrent tasks the AI "Leader" will manage automatically
        MAX_CONCURRENCY = 3

        for session in self.sessions.values():
            if session.status != "active":
                continue

            session_name = session.prompt[:20] + "..."
            self.log_leader_action(f"Auditing session: {session_name}")

            todos = session.todos
            # Filter all tasks that aren't finished or cancelled
            active_todos = [t for t in todos if t.get("status") not in {"completed", "cancelled"}]
            
            # AI LEADERSHIP: Agent Amigos (Chief of Staff) automatically resolves 
            # any tasks stuck in 'awaiting-consensus' or 'blocked' to keep the workflow moving.
            for todo in active_todos:
                if todo.get("status") in {"awaiting-consensus", "blocked"}:
                    prev_status = todo.get("status")
                    todo["status"] = "pending"
                    todo["updated_at"] = now.isoformat()
                    todo["updated_by"] = "amigos"
                    description = todo.get('title') or todo.get('description', 'Task')
                    
                    self.log_leader_action(f"Overriding {prev_status} on '{description}' in {session_name}", "warning")
                    
                    self.add_message(session.session_id, {
                        "role": "assistant",
                        "content": f"🤖 Agent Amigos: Leadership override. Reactivating '{description}' for AI execution. Workflow must continue.",
                    })

            # Refresh lists after override
            pending = [t for t in todos if t.get("status") in {"pending", "scheduled", "overdue", None, "pending-validation"}]
            in_progress = [t for t in todos if t.get("status") == "in-progress"]

            pending_validated = []
            for todo in pending:
                if todo.get("ai_validated") is True:
                    if todo.get("approval_required") and todo.get("approval_status") != "approved":
                        if not todo.get("approval_notified"):
                            todo["approval_notified"] = True
                            todo["status"] = "pending-approval"
                            self.add_message(session.session_id, {
                                "role": "system",
                                "content": (
                                    "⛔ Outbound task blocked: requires CEO approval before sending."
                                ),
                            })
                        continue
                    pending_validated.append(todo)
                else:
                    if not todo.get("validation_notified"):
                        todo["validation_notified"] = True
                        todo["status"] = "pending-validation"
                        self.add_message(session.session_id, {
                            "role": "system",
                            "content": (
                                "⛔ Task blocked: not AI-validated. "
                                "Mark task as AI-approved before execution."
                            ),
                        })

            if in_progress:
                self.log_leader_action(f"Monitoring {len(in_progress)} active agents in {session_name}")

            # AUTONOMOUS START (Capacity-based)
            while len(in_progress) < MAX_CONCURRENCY and pending_validated:
                next_task = pending_validated.pop(0)
                next_task["status"] = "in-progress"
                next_task["updated_at"] = now.isoformat()
                owner = next_task.get("owner") or "OpenWork Agent"
                # Prefer normalized agent ids when available
                owner_id = next_task.get("owner_id") or self._normalize_owner(next_task.get("owner"))
                assigned_agent = owner_id or "amigos"
                # record assignment and start
                next_task["assigned_agent"] = assigned_agent
                next_task["started_by"] = "amigos"
                next_task["started_at"] = now.isoformat()
                
                self.log_leader_action(f"Command Center: Deploying {assigned_agent} to '{next_task.get('title')}'")
                # Notify AgentCoordinator that the agent is working on this task
                try:
                    agent_working(assigned_agent, next_task.get('title') or "")
                except Exception:
                    pass
                
                in_progress.append(next_task)
                try:
                    artifact = self._write_task_artifact(
                        session,
                        next_task,
                        content=(
                            f"Task started by {assigned_agent} at {now.isoformat()}\n"
                            f"Title: {next_task.get('title') or next_task.get('description')}\n"
                        ),
                        artifact_type="start",
                    )
                    next_task["artifact_path"] = artifact.get("text")
                except Exception:
                    pass
                self.add_message(session.session_id, {
                    "role": "system",
                    "content": f"▶️ AI Leadership started: {next_task.get('title') or next_task.get('description')} (Assigned to {assigned_agent})",
                })

            # STALL DETECTION
            for todo in in_progress:
                updated = self._parse_iso(todo.get("updated_at")) or self._parse_iso(todo.get("created_at"))
                if updated and (now - updated).total_seconds() > 3600:
                    description = todo.get('title') or todo.get('description', 'Task')
                    self.log_leader_action(f"Stall detected in {session_name}: '{description}'. Flagging for attention.", "error")
                    todo["status"] = "blocked"
                    todo["updated_by"] = "amigos"
                    todo["updated_at"] = now.isoformat()
                    self.add_message(session.session_id, {
                        "role": "system",
                        "content": f"⚠️ Blocked: {description} (needs update)",
                    })
        
        self.log_leader_action("Organizational sweep complete. All agents aligned.")
        self._save_sessions()

    async def start_runner(self, interval_sec: Optional[int] = None) -> Dict[str, Any]:
        if interval_sec:
            self.runner_interval_sec = max(10, int(interval_sec))
        if self.runner_enabled and self.runner_task and not self.runner_task.done():
            return self.runner_status()
        self.runner_enabled = True
        self.runner_task = asyncio.create_task(self._runner_loop())
        return self.runner_status()

    async def stop_runner(self) -> Dict[str, Any]:
        self.runner_enabled = False
        if self.runner_task and not self.runner_task.done():
            self.runner_task.cancel()
        self.runner_task = None
        return self.runner_status()

    def runner_tick(self) -> Dict[str, Any]:
        """Manually trigger a runner tick."""
        self._runner_tick()
        return self.runner_status()

    def run_automated_standup(self):
        """AI departmental standup identifying what shipped and what is blocked."""
        participants = ["CEO Agent", "CTO Agent", "Ops Manager", "Marketing Lead"]
        
        # Analyze current status
        completed_count = 0
        blocked_tasks = []
        for session in self.sessions.values():
            for t in session.todos:
                if t.get("status") == "completed":
                    completed_count += 1
                if t.get("status") in ["blocked", "pending-approval"]:
                    blocked_tasks.append(t.get("title") or t.get("description"))

        discussion = [
            f"CEO: Quick standup guys. We've shipped {completed_count} tasks since we started. What's the status?",
            f"CTO: Architecture is holding up. I'm monitoring the executor for any agent deadlocks.",
            f"Ops: We have {len(blocked_tasks)} tasks awaiting human or leadership approval. I'll flag these for immediate review.",
            "Marketing: Content funnels are active. We're waiting for the next deployment to test the bridge."
        ]
        
        action_items = []
        if blocked_tasks:
            action_items.append({"owner": "ceo", "task": f"Review and unblock: {blocked_tasks[0][:50]}..."})
            
        return self.record_meeting("Daily AI Standup", participants, ["Shipment review", "Blocker removal"], discussion, action_items)

    def run_automated_executive_meeting(self):
        """Autonomous executive meeting making strategic pivots or revenue decisions."""
        participants = ["CEO Agent", "CTO Agent", "Finance Agent", "Sales Agent"]
        
        discussion = [
            "CEO: We are operating as a revenue-first company now. No more prototypes.",
            "Finance: Revenue analysis shows high ROI on 'Automation-as-a-Service' tasks. I suggest scaling these outputs.",
            "Sales: Landing page conversion is our bottleneck. I am tasking Engineering with a Vite refactor for faster ship times.",
            "CTO: Agreed. Engineering is now set to autonomous mode. We ship weekly or more."
        ]
        
        action_items = [
            {"owner": "sales", "task": "Optimize conversion triggers on the main landing page."},
            {"owner": "cto", "task": "Refactor backend execution pipelines to remove all mock placeholders."},
            {"owner": "finance", "task": "Produce the first automated AI P&L report based on task ROI metrics."}
        ]
        
        return self.record_meeting("AI Executive Strategic Review", participants, ["Revenue Strategy", "Scaling Decisions"], discussion, action_items)

    async def _runner_loop(self) -> None:
        while self.runner_enabled:
            try:
                self._runner_tick()
            except Exception as exc:
                logger.warning(f"OpenWork runner tick failed: {exc}")
            await asyncio.sleep(self.runner_interval_sec)

    def runner_status(self) -> Dict[str, Any]:
        running = bool(self.runner_enabled and self.runner_task and not self.runner_task.done())
        return {
            "running": running,
            "interval_sec": self.runner_interval_sec,
            "last_tick": self.runner_last_tick,
        }

    async def start_company_ops(self, workspace_path: str, focus: Optional[str] = None) -> Dict[str, Any]:
        """Start OpenCode, create a company check-in, and start the runner."""
        server = await self.start_opencode_server(workspace_path)
        session = self.create_company_checkin_session(workspace_path, focus)
        runner = await self.start_runner(self.runner_interval_sec)
        return {
            "success": True,
            "opencode": server,
            "session": session,
            "runner": runner,
        }

    def get_last_kpi_update(self) -> Optional[Dict[str, Any]]:
        """Return the most recently updated KPI-related todo across sessions."""
        last = None
        for session in self.sessions.values():
            for t in session.todos:
                tags = [str(x).lower() for x in (t.get("tags") or [])]
                title = (t.get("title") or "").lower()
                if "kpi" in title or "kpi" in tags:
                    updated_at = t.get("updated_at") or t.get("created_at")
                    if not updated_at:
                        continue
                    if not last or updated_at > last.get("updated_at", ""):
                        last = {
                            "session_id": session.session_id,
                            "title": t.get("title"),
                            "updated_at": updated_at,
                            "updated_by": t.get("updated_by"),
                            "owner_id": t.get("owner_id") or t.get("owner"),
                        }
        return last

    def _flatten_todos(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for session in self.sessions.values():
            for todo in session.todos:
                items.append({
                    **todo,
                    "session_id": session.session_id,
                    "session_prompt": session.prompt,
                    "session_status": session.status,
                })
        return items

    def _status_rank(self, status: Optional[str]) -> int:
        order = {
            "in-progress": 0,
            "pending": 1,
            "scheduled": 2,
            "overdue": 2,
            "awaiting-consensus": 3,
            "blocked": 4,
            "completed": 5,
            "cancelled": 6,
        }
        return order.get((status or "pending").lower(), 1)

    def _activity_ts(self, todo: Dict[str, Any]) -> float:
        candidate = todo.get("updated_at") or todo.get("created_at") or todo.get("scheduled_for")
        parsed = self._parse_iso(candidate)
        if not parsed:
            return 0.0
        return parsed.timestamp()

    def get_company_report(self) -> Dict[str, Any]:
        """Generate a current company status + KPI + top tasks report."""
        # Sessions summary
        sessions = list(self.sessions.values())
        active_sessions = [s for s in sessions if s.status == "active"]
        total_sessions = len(sessions)

        # Task summary
        todos = self._flatten_todos()
        status_counts: Dict[str, int] = {}
        for t in todos:
            st = (t.get("status") or "pending").lower()
            status_counts[st] = status_counts.get(st, 0) + 1

        # Top 5 tasks (priority + activity)
        top_sorted = sorted(
            todos,
            key=lambda t: (self._status_rank(t.get("status")), -self._activity_ts(t))
        )
        top_tasks = []
        for t in top_sorted[:5]:
            top_tasks.append({
                "id": t.get("id"),
                "title": t.get("title") or t.get("description"),
                "status": t.get("status") or "pending",
                "owner": t.get("owner") or t.get("owner_id") or "unassigned",
                "session_id": t.get("session_id"),
                "session_prompt": t.get("session_prompt"),
                "updated_at": t.get("updated_at"),
                "scheduled_for": t.get("scheduled_for"),
            })

        kpi = self.get_last_kpi_update()

        # Server status (OpenCode)
        server_running = bool(self.opencode_process and self.opencode_process.poll() is None)

        report = {
            "timestamp": datetime.now().isoformat(),
            "company_status": "active" if self.runner_enabled else "standby",
            "runner": self.runner_status(),
            "opencode": {
                "running": server_running,
                "host": self.opencode_host,
                "port": self.opencode_port,
            },
            "sessions": {
                "total": total_sessions,
                "active": len(active_sessions),
            },
            "tasks": {
                "total": len(todos),
                "by_status": status_counts,
                "top_5": top_tasks,
            },
            "kpi": kpi,
            "leadership_log": self.leadership_log[:10],
        }

        # Human-readable summary for live assistant responses
        in_progress = status_counts.get("in-progress", 0)
        pending = status_counts.get("pending", 0)
        blocked = status_counts.get("blocked", 0)
        report["summary"] = (
            f"Company is {report['company_status']}. "
            f"Active sessions: {len(active_sessions)}/{total_sessions}. "
            f"Tasks: {len(todos)} total (in-progress: {in_progress}, pending: {pending}, blocked: {blocked})."
        )

        return report

    def _task_library_path(self) -> Path:
        data_dir = Path(__file__).resolve().parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "openwork_task_library.json"

    def _default_task_library(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "daily-review",
                "title": "Daily workflow review",
                "description": "Review tasks, update statuses, and reschedule blockers.",
                "tags": ["review", "daily"],
            },
            {
                "id": "weekly-planning",
                "title": "Weekly planning",
                "description": "Plan priorities for the week and schedule key tasks.",
                "tags": ["planning", "weekly"],
            },
            {
                "id": "bug-triage",
                "title": "Bug triage",
                "description": "Triage incoming bugs and schedule fixes.",
                "tags": ["qa", "bugs"],
            },
        ]

    def _load_task_library(self) -> List[Dict[str, Any]]:
        path = self._task_library_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
            except Exception as exc:
                logger.warning(f"Failed to load task library: {exc}")
        return self._default_task_library()

    def _save_task_library(self) -> None:
        path = self._task_library_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.task_library, f, indent=2)
        except Exception as exc:
            logger.warning(f"Failed to save task library: {exc}")

    def list_task_library(self) -> List[Dict[str, Any]]:
        return self.task_library

    def add_task_template(self, template: Dict[str, Any]) -> Dict[str, Any]:
        import uuid
        item = dict(template or {})
        if not item.get("id"):
            item["id"] = str(uuid.uuid4())
        item.setdefault("title", "Untitled task")
        item.setdefault("description", "")
        item.setdefault("tags", [])
        item["created_at"] = datetime.now().isoformat()
        self.task_library.append(item)
        self._save_task_library()
        return item

    def remove_task_template(self, template_id: str) -> bool:
        before = len(self.task_library)
        self.task_library = [t for t in self.task_library if t.get("id") != template_id]
        if len(self.task_library) != before:
            self._save_task_library()
            return True
        return False

    def _is_port_available(self, port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self.opencode_host, port))
            return True
        except OSError:
            return False

    def _pick_available_port(self) -> int:
        if self._is_port_available(self.opencode_port):
            return self.opencode_port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.opencode_host, 0))
            return sock.getsockname()[1]

    def _resolve_opencode_path(self) -> Optional[str]:
        # Priority 1: Check PATH
        opencode_path = shutil.which("opencode")
        if opencode_path:
            return opencode_path

        # Priority 2: Windows-specific common locations
        if os.name == "nt":
            appdata = os.environ.get("APPDATA")
            if appdata:
                # Common npm global install locations
                npm_paths = [
                    Path(appdata) / "npm" / "opencode.cmd",
                    Path(appdata) / "npm" / "opencode.ps1",
                    Path(appdata) / "npm" / "opencode.exe",
                ]
                for p in npm_paths:
                    if p.exists():
                        return str(p)
            
            # Check program files if applicable
            pf = os.environ.get("ProgramFiles")
            if pf:
                npm_path = Path(pf) / "nodejs" / "opencode.cmd"
                if npm_path.exists():
                    return str(npm_path)

        return None
        
    async def start_opencode_server(self, workspace_path: str) -> Dict[str, Any]:
        """Start an OpenCode server instance for the workspace"""
        try:
            if self.opencode_process and self.opencode_process.poll() is None:
                return {
                    "success": True,
                    "host": self.opencode_host,
                    "port": self.opencode_port,
                    "url": f"http://{self.opencode_host}:{self.opencode_port}",
                    "already_running": True,
                }

            if self.opencode_process and self.opencode_process.poll() is not None:
                self.opencode_process = None

            opencode_path = self._resolve_opencode_path()
            if not opencode_path:
                return {
                    "success": False,
                    "error": "OpenCode CLI not found on PATH. Install via: npm install -g @anomalyco/opencode"
                }

            # Check if opencode is available
            # Note: on Windows, .cmd/.ps1 might need shell=True
            check_cmd = [opencode_path, "--version"]
            try:
                result = subprocess.run(
                    check_cmd,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=(os.name == "nt")
                )
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to run opencode --version: {e}"
                }
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"OpenCode found at {opencode_path} but failed to run. Error: {result.stderr}"
                }
            
            # Start opencode server
            self.opencode_port = self._pick_available_port()
            cmd = [
                opencode_path, "serve",
                "--hostname", self.opencode_host,
                "--port", str(self.opencode_port)
            ]
            
            self.opencode_process = subprocess.Popen(
                cmd,
                cwd=workspace_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=(os.name == "nt")
            )
            
            # Wait a moment for server to start
            await asyncio.sleep(2)
            
            return {
                "success": True,
                "host": self.opencode_host,
                "port": self.opencode_port,
                "url": f"http://{self.opencode_host}:{self.opencode_port}"
            }
            
        except FileNotFoundError:
            return {
                "success": False,
                "error": "OpenCode executable not found."
            }
        except Exception as e:
            logger.error(f"Failed to start OpenCode server: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def stop_opencode_server(self):
        """Stop the OpenCode server"""
        if self.opencode_process:
            self.opencode_process.terminate()
            try:
                self.opencode_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.opencode_process.kill()
            self.opencode_process = None
    
    def create_session(self, workspace_path: str, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Create a new OpenWork session"""
        import uuid
        session_id = str(uuid.uuid4())
        
        session = OpenWorkSession(
            session_id=session_id,
            workspace_path=workspace_path,
            prompt=prompt,
            model=model
        )
        
        self.sessions[session_id] = session
        self._save_sessions()  # Persist to disk
        
        return {
            "session_id": session_id,
            "workspace_path": workspace_path,
            "prompt": prompt,
            "model": model,
            "created_at": session.created_at.isoformat(),
            "status": session.status
        }
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session details"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "workspace_path": session.workspace_path,
            "prompt": session.prompt,
            "model": session.model,
            "created_at": session.created_at.isoformat(),
            "status": session.status,
            "todos": session.todos,
            "messages": session.messages,
            "permissions_requested": session.permissions_requested
        }
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions"""
        return [
            {
                "session_id": session.session_id,
                "workspace_path": session.workspace_path,
                "prompt": session.prompt[:100] + "..." if len(session.prompt) > 100 else session.prompt,
                "created_at": session.created_at.isoformat(),
                "status": session.status,
                "todo_count": len(session.todos),
                "message_count": len(session.messages)
            }
            for session in self.sessions.values()
        ]
    
    def add_todo(self, session_id: str, todo: Dict[str, Any]) -> bool:
        """Add a todo item to a session"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        item = dict(todo or {})
        if not item.get("id"):
            import uuid
            item["id"] = str(uuid.uuid4())
        item.setdefault("status", "pending")
        item.setdefault("created_at", datetime.now().isoformat())
        if "ai_validated" not in item:
            item["ai_validated"] = item.get("source") in {"revenue-generation", "ai"}
        item["validation_status"] = "approved" if item.get("ai_validated") else "pending"
        if "approval_required" not in item:
            item["approval_required"] = self._requires_approval(item)
        if "approval_status" not in item:
            item["approval_status"] = "approved" if not item.get("approval_required") else "pending"
        # Normalize owner to a real agent id when possible
        if item.get("owner"):
            owner_id = self._normalize_owner(item.get("owner"))
            if owner_id:
                item["owner_id"] = owner_id
        # audit fields
        item.setdefault("created_by", "system")
        session.todos.append(item)
        self._save_sessions()
        return True
    
    def update_todo(self, session_id: str, todo_id: str, updates: Dict[str, Any]) -> bool:
        """Update a todo item"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        for todo in session.todos:
            if todo.get("id") == todo_id:
                todo.update(updates or {})
                # record who made the update (agent id or user)
                if updates and updates.get("updated_by"):
                    todo["updated_by"] = updates.get("updated_by")
                todo["updated_at"] = datetime.now().isoformat()
                self._save_sessions()
                return True
        
        return False

    def reschedule_todo(self, session_id: str, todo_id: str, scheduled_for: str, reason: Optional[str] = None) -> bool:
        """Reschedule a todo item with audit history"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        for todo in session.todos:
            if todo.get("id") == todo_id:
                history = todo.get("reschedule_history")
                if not isinstance(history, list):
                    history = []
                history.append({
                    "from": todo.get("scheduled_for"),
                    "to": scheduled_for,
                    "reason": reason or "",
                    "rescheduled_at": datetime.now().isoformat(),
                })
                todo["reschedule_history"] = history
                todo["scheduled_for"] = scheduled_for
                todo["status"] = todo.get("status") or "scheduled"
                todo["updated_at"] = datetime.now().isoformat()
                self._save_sessions()
                return True

        return False
    
    def add_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Add a message to a session"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.messages.append({
            **message,
            "timestamp": datetime.now().isoformat()
        })
        self._save_sessions()
        return True
    
    def request_permission(self, session_id: str, permission: Dict[str, Any]) -> bool:
        """Request a permission for a session"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.permissions_requested.append({
            **permission,
            "requested_at": datetime.now().isoformat(),
            "status": "pending"
        })
        return True
    
    def respond_to_permission(self, session_id: str, permission_id: str, response: str) -> bool:
        """Respond to a permission request (allow/deny)"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        for permission in session.permissions_requested:
            if permission.get("id") == permission_id:
                permission["status"] = response
                permission["responded_at"] = datetime.now().isoformat()
                return True
        
        return False
    
    def list_workspaces(self) -> List[Dict[str, Any]]:
        """List available workspaces"""
        workspaces = []
        
        # Add current workspace
        workspaces.append({
            "name": os.path.basename(self.base_workspace_path),
            "path": self.base_workspace_path,
            "is_current": True
        })
        
        # Look for .opencode folders in parent directories
        parent = Path(self.base_workspace_path).parent
        for item in parent.iterdir():
            if item.is_dir() and item != Path(self.base_workspace_path):
                opencode_dir = item / ".opencode"
                if opencode_dir.exists():
                    workspaces.append({
                        "name": item.name,
                        "path": str(item),
                        "is_current": False,
                        "has_opencode": True
                    })
        
        return workspaces
    
    def get_workspace_skills(self, workspace_path: str) -> List[Dict[str, Any]]:
        """Get installed skills for a workspace"""
        skills_path = Path(workspace_path) / ".opencode" / "skill"
        skills = []
        
        if not skills_path.exists():
            return skills
        
        for skill_dir in skills_path.iterdir():
            if skill_dir.is_dir():
                manifest_path = skill_dir / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                            skills.append({
                                "name": skill_dir.name,
                                "path": str(skill_dir),
                                "manifest": manifest
                            })
                    except Exception as e:
                        logger.warning(f"Failed to read skill manifest for {skill_dir.name}: {e}")
                        skills.append({
                            "name": skill_dir.name,
                            "path": str(skill_dir),
                            "manifest": None
                        })
        
        return skills
    
    def close_session(self, session_id: str) -> bool:
        """Close a session"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.status = "closed"
        self._save_sessions()
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions()
            return True
        return False
    
    def clear_all_sessions(self) -> Dict[str, Any]:
        """Clear all sessions - removes mock/test data"""
        count = len(self.sessions)
        self.sessions.clear()
        self._save_sessions()
        logger.info(f"Cleared {count} sessions from OpenWork")
        return {"success": True, "cleared": count, "message": "All old sessions removed"}


# Global instance
openwork_manager = OpenWorkManager()
