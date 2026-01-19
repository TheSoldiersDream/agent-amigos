"""
Shared Memory System for Agent Amigos
======================================
Local persistent memory shared between Amigos and Ollie (Ollama).
Enables self-learning, context sharing, and knowledge accumulation.

All data stays LOCAL - nothing is sent externally.
Owner: Darrell Buttigieg
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import hashlib
import re

# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY STORAGE PATHS
# ═══════════════════════════════════════════════════════════════════════════════

MEMORY_DIR = Path(__file__).parent.parent / "memory"
MEMORY_DIR.mkdir(exist_ok=True)

# Memory files
CONVERSATIONS_FILE = MEMORY_DIR / "conversations.json"
LEARNED_FACTS_FILE = MEMORY_DIR / "learned_facts.json"
USER_PREFERENCES_FILE = MEMORY_DIR / "user_preferences.json"
TASK_HISTORY_FILE = MEMORY_DIR / "task_history.json"
KNOWLEDGE_BASE_FILE = MEMORY_DIR / "knowledge_base.json"
TOOL_RESULTS_FILE = MEMORY_DIR / "tool_results_cache.json"


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED MEMORY CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class SharedMemory:
    """
    Shared memory system for Agent Amigos and Ollie.
    Persists locally, enables learning and context sharing.
    """
    
    def __init__(self):
        self._ensure_files_exist()
        self._cache = {}
        self._load_cache()
    
    def _ensure_files_exist(self):
        """Create memory files if they don't exist."""
        default_structures = {
            CONVERSATIONS_FILE: {"conversations": [], "summary": ""},
            LEARNED_FACTS_FILE: {"facts": [], "categories": {}},
            USER_PREFERENCES_FILE: {"preferences": {}, "patterns": []},
            TASK_HISTORY_FILE: {"tasks": [], "success_patterns": []},
            KNOWLEDGE_BASE_FILE: {"entries": {}, "topics": []},
            TOOL_RESULTS_FILE: {"cache": {}, "frequent_tools": []}
        }
        
        for file_path, default_data in default_structures.items():
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, indent=2)
    
    def _load_cache(self):
        """Load all memory files into cache."""
        files = {
            "conversations": CONVERSATIONS_FILE,
            "facts": LEARNED_FACTS_FILE,
            "preferences": USER_PREFERENCES_FILE,
            "tasks": TASK_HISTORY_FILE,
            "knowledge": KNOWLEDGE_BASE_FILE,
            "tool_cache": TOOL_RESULTS_FILE
        }
        
        for key, file_path in files.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self._cache[key] = json.load(f)
            except Exception as e:
                print(f"Error loading {key}: {e}")
                self._cache[key] = {}
    
    def _save(self, key: str, file_path: Path):
        """Save a specific cache to file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._cache.get(key, {}), f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving {key}: {e}")
    
    # ───────────────────────────────────────────────────────────────────────────
    # CONVERSATION MEMORY
    # ───────────────────────────────────────────────────────────────────────────
    
    def add_conversation(self, role: str, content: str, agent: str = "amigos"):
        """
        Add a conversation message to memory.
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
            agent: 'amigos' or 'ollie'
        """
        conversation = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content[:2000],  # Limit size
            "agent": agent
        }
        
        if "conversations" not in self._cache:
            self._cache["conversations"] = {"conversations": [], "summary": ""}
        
        self._cache["conversations"]["conversations"].append(conversation)
        
        # Keep last 500 messages
        if len(self._cache["conversations"]["conversations"]) > 500:
            self._cache["conversations"]["conversations"] = \
                self._cache["conversations"]["conversations"][-500:]
        
        self._save("conversations", CONVERSATIONS_FILE)
    
    def get_recent_conversations(self, limit: int = 20) -> List[Dict]:
        """Get recent conversation history."""
        convos = self._cache.get("conversations", {}).get("conversations", [])
        return convos[-limit:]
    
    def get_conversation_context(self, limit: int = 10) -> str:
        """Get formatted conversation context for prompts."""
        recent = self.get_recent_conversations(limit)
        if not recent:
            return ""
        
        context_parts = []
        for msg in recent:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:500]
            agent = msg.get("agent", "amigos")
            context_parts.append(f"[{agent}] {role}: {content}")
        
        return "\n".join(context_parts)
    
    # ───────────────────────────────────────────────────────────────────────────
    # LEARNED FACTS (Self-Learning)
    # ───────────────────────────────────────────────────────────────────────────
    
    def learn_fact(self, fact: str, category: str = "general", source: str = "conversation"):
        """
        Learn and store a new fact.
        
        Args:
            fact: The fact to remember
            category: Category (general, user, technical, preference)
            source: Where this was learned from
        """
        fact_id = hashlib.md5(fact.lower().encode()).hexdigest()[:12]
        
        fact_entry = {
            "id": fact_id,
            "fact": fact,
            "category": category,
            "source": source,
            "learned_at": datetime.now().isoformat(),
            "recall_count": 0,
            "confidence": 1.0
        }
        
        if "facts" not in self._cache:
            self._cache["facts"] = {"facts": [], "categories": {}}
        
        # Check if fact already exists
        existing_ids = [f.get("id") for f in self._cache["facts"]["facts"]]
        if fact_id not in existing_ids:
            self._cache["facts"]["facts"].append(fact_entry)
            
            # Update categories
            if category not in self._cache["facts"]["categories"]:
                self._cache["facts"]["categories"][category] = []
            self._cache["facts"]["categories"][category].append(fact_id)
            
            self._save("facts", LEARNED_FACTS_FILE)
            return True
        return False
    
    def recall_facts(self, query: Optional[str] = None, category: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Recall learned facts, optionally filtered.
        
        Args:
            query: Search query to filter facts
            category: Category filter
            limit: Max facts to return
        """
        facts = self._cache.get("facts", {}).get("facts", [])
        
        if category:
            category_ids = self._cache.get("facts", {}).get("categories", {}).get(category, [])
            facts = [f for f in facts if f.get("id") in category_ids]
        
        if query:
            query_lower = query.lower()
            facts = [f for f in facts if query_lower in f.get("fact", "").lower()]
        
        # Sort by recall count and recency
        facts.sort(key=lambda x: (x.get("recall_count", 0), x.get("learned_at", "")), reverse=True)
        
        # Update recall count for returned facts
        for fact in facts[:limit]:
            fact["recall_count"] = fact.get("recall_count", 0) + 1
        
        self._save("facts", LEARNED_FACTS_FILE)
        return facts[:limit]
    
    def get_facts_for_context(self, query: str, limit: int = 5) -> str:
        """Get relevant facts formatted for prompt context."""
        facts = self.recall_facts(query=query, limit=limit)
        if not facts:
            return ""
        
        fact_strings = [f"• {f.get('fact', '')}" for f in facts]
        return "Relevant knowledge:\n" + "\n".join(fact_strings)
    
    # ───────────────────────────────────────────────────────────────────────────
    # USER PREFERENCES
    # ───────────────────────────────────────────────────────────────────────────
    
    def set_preference(self, key: str, value: Any):
        """Set a user preference."""
        if "preferences" not in self._cache:
            self._cache["preferences"] = {"preferences": {}, "patterns": []}
        
        self._cache["preferences"]["preferences"][key] = {
            "value": value,
            "updated_at": datetime.now().isoformat()
        }
        self._save("preferences", USER_PREFERENCES_FILE)
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        prefs = self._cache.get("preferences", {}).get("preferences", {})
        pref = prefs.get(key, {})
        return pref.get("value", default)
    
    def get_all_preferences(self) -> Dict:
        """Get all user preferences."""
        return self._cache.get("preferences", {}).get("preferences", {})
    
    # ───────────────────────────────────────────────────────────────────────────
    # TASK HISTORY & PATTERNS
    # ───────────────────────────────────────────────────────────────────────────
    
    def log_task(self, task: str, tools_used: List[str], success: bool, result_summary: str = ""):
        """
        Log a completed task for learning.
        
        Args:
            task: Task description
            tools_used: List of tools used
            success: Whether task succeeded
            result_summary: Brief result summary
        """
        task_entry = {
            "timestamp": datetime.now().isoformat(),
            "task": task[:500],
            "tools_used": tools_used,
            "success": success,
            "result_summary": result_summary[:500]
        }
        
        if "tasks" not in self._cache:
            self._cache["tasks"] = {"tasks": [], "success_patterns": []}
        
        self._cache["tasks"]["tasks"].append(task_entry)
        
        # Keep last 200 tasks
        if len(self._cache["tasks"]["tasks"]) > 200:
            self._cache["tasks"]["tasks"] = self._cache["tasks"]["tasks"][-200:]
        
        # Learn success pattern
        if success and tools_used:
            pattern = {"task_keywords": self._extract_keywords(task), "tools": tools_used}
            if pattern not in self._cache["tasks"]["success_patterns"]:
                self._cache["tasks"]["success_patterns"].append(pattern)
                if len(self._cache["tasks"]["success_patterns"]) > 50:
                    self._cache["tasks"]["success_patterns"] = \
                        self._cache["tasks"]["success_patterns"][-50:]
        
        self._save("tasks", TASK_HISTORY_FILE)
    
    def suggest_tools_for_task(self, task: str) -> List[str]:
        """Suggest tools based on similar past tasks."""
        keywords = self._extract_keywords(task)
        patterns = self._cache.get("tasks", {}).get("success_patterns", [])
        
        tool_scores = {}
        for pattern in patterns:
            pattern_keywords = set(pattern.get("task_keywords", []))
            overlap = len(keywords & pattern_keywords)
            if overlap > 0:
                for tool in pattern.get("tools", []):
                    tool_scores[tool] = tool_scores.get(tool, 0) + overlap
        
        # Sort by score
        sorted_tools = sorted(tool_scores.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_tools[:5]]
    
    def _extract_keywords(self, text: str) -> set:
        """Extract keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        # Filter common words
        stopwords = {'the', 'and', 'for', 'that', 'this', 'with', 'you', 'are', 'was', 'have', 'has'}
        return set(w for w in words if w not in stopwords)
    
    # ───────────────────────────────────────────────────────────────────────────
    # KNOWLEDGE BASE
    # ───────────────────────────────────────────────────────────────────────────
    
    def add_knowledge(self, topic: str, content: str, source: str = "learned"):
        """
        Add knowledge to the knowledge base.
        
        Args:
            topic: Topic/title
            content: Knowledge content
            source: Source of knowledge
        """
        topic_key = topic.lower().replace(" ", "_")
        
        if "knowledge" not in self._cache:
            self._cache["knowledge"] = {"entries": {}, "topics": []}
        
        self._cache["knowledge"]["entries"][topic_key] = {
            "topic": topic,
            "content": content[:5000],
            "source": source,
            "added_at": datetime.now().isoformat(),
            "access_count": 0
        }
        
        if topic_key not in self._cache["knowledge"]["topics"]:
            self._cache["knowledge"]["topics"].append(topic_key)
        
        self._save("knowledge", KNOWLEDGE_BASE_FILE)
    
    def get_knowledge(self, topic: str) -> Optional[Dict]:
        """Get knowledge by topic."""
        topic_key = topic.lower().replace(" ", "_")
        entries = self._cache.get("knowledge", {}).get("entries", {})
        
        entry = entries.get(topic_key)
        if entry:
            entry["access_count"] = entry.get("access_count", 0) + 1
            self._save("knowledge", KNOWLEDGE_BASE_FILE)
        
        return entry
    
    def search_knowledge(self, query: str, limit: int = 5) -> List[Dict]:
        """Search knowledge base."""
        query_lower = query.lower()
        entries = self._cache.get("knowledge", {}).get("entries", {})
        
        results = []
        for key, entry in entries.items():
            if query_lower in entry.get("topic", "").lower() or \
               query_lower in entry.get("content", "").lower():
                results.append(entry)
        
        results.sort(key=lambda x: x.get("access_count", 0), reverse=True)
        return results[:limit]
    
    # ───────────────────────────────────────────────────────────────────────────
    # TOOL RESULTS CACHE
    # ───────────────────────────────────────────────────────────────────────────
    
    def cache_tool_result(self, tool_name: str, args_hash: str, result: Any, ttl_minutes: int = 60):
        """
        Cache a tool result for reuse.
        
        Args:
            tool_name: Name of the tool
            args_hash: Hash of arguments
            result: Result to cache
            ttl_minutes: Time to live in minutes
        """
        if "tool_cache" not in self._cache:
            self._cache["tool_cache"] = {"cache": {}, "frequent_tools": []}
        
        cache_key = f"{tool_name}:{args_hash}"
        self._cache["tool_cache"]["cache"][cache_key] = {
            "result": result,
            "cached_at": datetime.now().isoformat(),
            "ttl_minutes": ttl_minutes
        }
        
        # Track frequent tools
        freq = self._cache["tool_cache"].get("frequent_tools", [])
        if tool_name not in freq:
            freq.append(tool_name)
        
        self._save("tool_cache", TOOL_RESULTS_FILE)
    
    def get_cached_result(self, tool_name: str, args_hash: str) -> Optional[Any]:
        """Get cached tool result if still valid."""
        cache_key = f"{tool_name}:{args_hash}"
        cache = self._cache.get("tool_cache", {}).get("cache", {})
        
        entry = cache.get(cache_key)
        if entry:
            cached_at = datetime.fromisoformat(entry.get("cached_at", "2000-01-01"))
            ttl = entry.get("ttl_minutes", 60)
            age_minutes = (datetime.now() - cached_at).total_seconds() / 60
            
            if age_minutes < ttl:
                return entry.get("result")
        
        return None
    
    # ───────────────────────────────────────────────────────────────────────────
    # CONTEXT BUILDING FOR AGENTS
    # ───────────────────────────────────────────────────────────────────────────
    
    def build_context_for_agent(self, query: str, agent: str = "both") -> str:
        """
        Build a context string for agents including relevant memories.
        
        Args:
            query: Current query/task
            agent: 'amigos', 'ollie', or 'both'
            
        Returns:
            Context string to include in prompts
        """
        context_parts = []
        
        # Recent conversation context
        conv_context = self.get_conversation_context(limit=5)
        if conv_context:
            context_parts.append(f"Recent conversation:\n{conv_context}")
        
        # Relevant facts
        facts_context = self.get_facts_for_context(query, limit=3)
        if facts_context:
            context_parts.append(facts_context)
        
        # Relevant knowledge
        knowledge = self.search_knowledge(query, limit=2)
        if knowledge:
            kb_parts = [f"• {k.get('topic', '')}: {k.get('content', '')[:200]}" for k in knowledge]
            context_parts.append("Related knowledge:\n" + "\n".join(kb_parts))
        
        # User preferences
        prefs = self.get_all_preferences()
        if prefs:
            pref_parts = [f"• {k}: {v.get('value', '')}" for k, v in list(prefs.items())[:5]]
            context_parts.append("User preferences:\n" + "\n".join(pref_parts))
        
        # Tool suggestions
        suggested_tools = self.suggest_tools_for_task(query)
        if suggested_tools:
            context_parts.append(f"Suggested tools: {', '.join(suggested_tools)}")
        
        return "\n\n".join(context_parts)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory system."""
        return {
            "conversations": len(self._cache.get("conversations", {}).get("conversations", [])),
            "learned_facts": len(self._cache.get("facts", {}).get("facts", [])),
            "preferences": len(self._cache.get("preferences", {}).get("preferences", {})),
            "tasks_logged": len(self._cache.get("tasks", {}).get("tasks", [])),
            "knowledge_entries": len(self._cache.get("knowledge", {}).get("entries", {})),
            "cached_results": len(self._cache.get("tool_cache", {}).get("cache", {})),
            "memory_dir": str(MEMORY_DIR)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

shared_memory = SharedMemory()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def remember_conversation(role: str, content: str, agent: str = "amigos"):
    """Quick helper to log a conversation."""
    shared_memory.add_conversation(role, content, agent)

def learn(fact: str, category: str = "general"):
    """Quick helper to learn a fact."""
    return shared_memory.learn_fact(fact, category)

def recall(query: Optional[str] = None, limit: int = 10):
    """Quick helper to recall facts."""
    return shared_memory.recall_facts(query, limit=limit)

def get_context(query: str) -> str:
    """Quick helper to get context for a query."""
    return shared_memory.build_context_for_agent(query)

def log_task_completion(task: str, tools: List[str], success: bool, summary: str = ""):
    """Quick helper to log task completion."""
    shared_memory.log_task(task, tools, success, summary)

def get_memory_info() -> Dict:
    """Get memory system info."""
    return shared_memory.get_memory_stats()
