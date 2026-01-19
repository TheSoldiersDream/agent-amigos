"""
Macro Memory & Learning System
===============================

Stores and recalls successful workflows, user preferences, and learned patterns.
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class MacroMemory:
    """
    Multi-layer memory system for autonomous macro learning.
    """
    
    def __init__(self, data_dir: str = "data/macros/memory"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Memory layers
        self.short_term = {}  # Current session
        self.skills = self._load_skills()  # Reusable workflows
        self.preferences = self._load_preferences()  # User habits
        self.success_log = self._load_success_log()  # Historical successes
        
        logger.info("✓ Macro Memory initialized")
    
    async def recall(
        self,
        goal: str,
        domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recall relevant memory for a goal.
        
        Args:
            goal: User's stated goal
            domain: Target domain
            
        Returns:
            Relevant memory context including:
            - Similar past successes
            - Learned skills for this domain
            - User preferences
        """
        logger.info(f"🧠 Recalling memory for: {goal}")
        
        memory_context = {
            "similar_tasks": [],
            "domain_skills": [],
            "preferences": {},
            "success_patterns": []
        }
        
        # Find similar past successes
        for success in self.success_log:
            if self._is_similar_goal(goal, success.get("goal", "")):
                memory_context["similar_tasks"].append({
                    "goal": success["goal"],
                    "steps": len(success.get("plan", {}).get("steps", [])),
                    "success_rate": success.get("success_rate", 0),
                    "timestamp": success.get("timestamp")
                })
        
        # Find domain-specific skills
        if domain:
            for skill_name, skill_data in self.skills.items():
                if skill_data.get("domain") == domain:
                    memory_context["domain_skills"].append({
                        "name": skill_name,
                        "description": skill_data.get("description"),
                        "success_rate": skill_data.get("success_rate", 0)
                    })
        
        # Add user preferences
        memory_context["preferences"] = self.preferences.copy()
        
        logger.info(f"  ✓ Found {len(memory_context['similar_tasks'])} similar tasks")
        logger.info(f"  ✓ Found {len(memory_context['domain_skills'])} domain skills")
        
        return memory_context
    
    async def store_success(
        self,
        goal: str,
        domain: Optional[str],
        plan: Dict[str, Any],
        execution_log: List[Dict]
    ):
        """
        Store a successful execution for future learning.
        """
        success_entry = {
            "goal": goal,
            "domain": domain,
            "plan": plan,
            "execution_log": execution_log,
            "timestamp": datetime.now().isoformat(),
            "success_rate": self._calculate_success_rate(execution_log)
        }
        
        self.success_log.append(success_entry)
        
        # Keep only last 100 successes
        if len(self.success_log) > 100:
            self.success_log = self.success_log[-100:]
        
        self._save_success_log()
        
        # Extract and store reusable skill if pattern detected
        await self._extract_skill(success_entry)
        
        logger.info(f"✓ Success stored to memory: {goal}")
    
    async def _extract_skill(self, success_entry: Dict):
        """
        Extract reusable workflow pattern as a skill.
        """
        goal = success_entry["goal"]
        domain = success_entry["domain"]
        
        # Check if this is a common pattern
        similar_count = sum(
            1 for s in self.success_log
            if self._is_similar_goal(goal, s.get("goal", ""))
        )
        
        # If we've done this 3+ times, save as skill
        if similar_count >= 3:
            skill_name = self._generate_skill_name(goal, domain)
            
            if skill_name not in self.skills:
                self.skills[skill_name] = {
                    "name": skill_name,
                    "description": goal,
                    "domain": domain,
                    "plan_template": success_entry["plan"],
                    "success_rate": success_entry["success_rate"],
                    "times_used": similar_count,
                    "created_at": datetime.now().isoformat()
                }
                
                self._save_skills()
                logger.info(f"✓ New skill learned: {skill_name}")
    
    def _is_similar_goal(self, goal1: str, goal2: str) -> bool:
        """Check if two goals are similar"""
        # Simple keyword matching (can be enhanced with embeddings)
        words1 = set(goal1.lower().split())
        words2 = set(goal2.lower().split())
        
        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        similarity = intersection / union if union > 0 else 0
        
        return similarity > 0.5  # 50% similarity threshold
    
    def _calculate_success_rate(self, execution_log: List[Dict]) -> float:
        """Calculate success rate from execution log"""
        if not execution_log:
            return 0.0
        
        successful = sum(1 for entry in execution_log if entry.get("result", {}).get("success"))
        total = len(execution_log)
        
        return round(successful / total, 2) if total > 0 else 0.0
    
    def _generate_skill_name(self, goal: str, domain: Optional[str]) -> str:
        """Generate a skill name from goal and domain"""
        # Extract key action words
        words = goal.lower().split()
        action_words = [w for w in words if w in [
            'login', 'search', 'download', 'submit', 'fill', 'find', 'navigate'
        ]]
        
        if action_words:
            skill_name = "_".join(action_words)
        else:
            skill_name = "_".join(words[:3])
        
        if domain:
            domain_short = domain.split('.')[0]
            skill_name = f"{domain_short}_{skill_name}"
        
        return skill_name
    
    def _load_skills(self) -> Dict[str, Any]:
        """Load learned skills from disk"""
        skills_file = os.path.join(self.data_dir, "skills.json")
        
        if os.path.exists(skills_file):
            try:
                with open(skills_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load skills: {e}")
        
        return {}
    
    def _save_skills(self):
        """Save skills to disk"""
        skills_file = os.path.join(self.data_dir, "skills.json")
        
        with open(skills_file, 'w') as f:
            json.dump(self.skills, f, indent=2)
    
    def _load_preferences(self) -> Dict[str, Any]:
        """Load user preferences"""
        prefs_file = os.path.join(self.data_dir, "preferences.json")
        
        if os.path.exists(prefs_file):
            try:
                with open(prefs_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load preferences: {e}")
        
        return {
            "typing_speed": "normal",
            "mouse_speed": "normal",
            "confirmation_level": "standard"
        }
    
    def _load_success_log(self) -> List[Dict]:
        """Load historical success log"""
        log_file = os.path.join(self.data_dir, "success_log.json")
        
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load success log: {e}")
        
        return []
    
    def _save_success_log(self):
        """Save success log to disk"""
        log_file = os.path.join(self.data_dir, "success_log.json")
        
        with open(log_file, 'w') as f:
            json.dump(self.success_log, f, indent=2)
