"""
Self-Learning Memory Engine for Agent Amigos
Stores experiences, learns from interactions, and adapts to user preferences
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import hashlib
from pathlib import Path

try:
    import chromadb  # type: ignore
    from chromadb.config import Settings  # type: ignore
    CHROMADB_AVAILABLE = True
except ImportError:
    chromadb = None  # type: ignore
    Settings = None  # type: ignore
    CHROMADB_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Represents a single memory entry"""
    id: str
    timestamp: str
    category: str  # "interaction", "success", "failure", "preference", "skill"
    content: str
    metadata: Dict[str, Any]
    relevance_score: float = 1.0
    access_count: int = 0
    last_accessed: Optional[str] = None


class LearningEngine:
    """
    Self-learning memory system that:
    1. Stores successful and failed interactions
    2. Learns user preferences over time
    3. Adapts agent behavior
    4. Provides experience replay
    5. Tracks skill improvement
    """
    
    def __init__(self, db_path: Optional[str] = None):
        # Default to <repo>/backend/memory, regardless of cwd.
        if db_path is None:
            db_path = str((Path(__file__).resolve().parents[1] / "memory").resolve())

        self.db_path = str(Path(db_path).resolve())
        self.chroma_client = None
        self.collections = {}
        self.in_memory_store: Dict[str, List[MemoryEntry]] = {}

        os.makedirs(self.db_path, exist_ok=True)
        
        # Initialize ChromaDB if available
        if CHROMADB_AVAILABLE and chromadb is not None and Settings is not None:
            try:
                settings = Settings(
                    chroma_db_impl="duckdb",
                    persist_directory=self.db_path,
                    anonymized_telemetry=False,
                    allow_reset=True
                )
                self.chroma_client = chromadb.Client(settings)
                self._init_chroma_collections()
                logger.info("ChromaDB initialized for memory storage")
            except Exception as e:
                logger.warning(f"ChromaDB initialization failed: {e}. Using in-memory storage.")
        else:
            logger.warning("ChromaDB not installed. Using in-memory storage only.")
        
        # Initialize in-memory categories
        self.categories = [
            "interaction",
            "success",
            "failure",
            "preference",
            "skill",
            "pattern",
            "insight"
        ]
        
        for cat in self.categories:
            self.in_memory_store[cat] = []
    
    def _init_chroma_collections(self):
        """Initialize ChromaDB collections"""
        if not self.chroma_client:
            return
        
        collection_names = [
            "user_preferences",
            "successful_tasks",
            "failed_tasks",
            "tool_usage",
            "reasoning_patterns",
            "query_embeddings"
        ]
        
        for name in collection_names:
            try:
                # Get or create collection
                collection = self.chroma_client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"}
                )
                self.collections[name] = collection
            except Exception as e:
                logger.warning(f"Failed to create collection {name}: {e}")
    
    def store_interaction(self,
                         agent_name: str,
                         task: str,
                         input_text: str,
                         output_text: str,
                         success: bool,
                         model_used: str,
                         duration_ms: float,
                         tools_used: Optional[List[str]] = None,
                         reasoning_chain: Optional[List[str]] = None) -> str:
        """Store an interaction for learning"""
        
        entry_id = self._generate_id(f"{agent_name}:{task}:{input_text}")
        
        metadata = {
            "agent": agent_name,
            "task": task,
            "model": model_used,
            "duration_ms": duration_ms,
            "success": success,
            "tools_used": tools_used or [],
            "reasoning_chain": reasoning_chain or []
        }
        
        content = f"Task: {task}\nInput: {input_text}\nOutput: {output_text}"
        
        category = "success" if success else "failure"
        
        entry = MemoryEntry(
            id=entry_id,
            timestamp=datetime.now().isoformat(),
            category=category,
            content=content,
            metadata=metadata,
            relevance_score=0.9 if success else 0.8
        )
        
        # Store in memory
        self.in_memory_store[category].append(entry)
        
        # Store in ChromaDB if available
        if self.chroma_client and "successful_tasks" in self.collections:
            try:
                collection = self.collections[
                    "successful_tasks" if success else "failed_tasks"
                ]
                collection.add(
                    ids=[entry_id],
                    documents=[content],
                    metadatas=[metadata]
                )
            except Exception as e:
                logger.warning(f"Failed to store in ChromaDB: {e}")
        
        return entry_id
    
    def store_preference(self, 
                        user_id: str,
                        preference_type: str,
                        value: Any,
                        context: Optional[Dict[str, Any]] = None) -> str:
        """Store user preference for adaptation"""
        
        entry_id = self._generate_id(f"pref:{user_id}:{preference_type}:{value}")
        
        metadata = {
            "user_id": user_id,
            "preference_type": preference_type,
            "context": context or {}
        }
        
        entry = MemoryEntry(
            id=entry_id,
            timestamp=datetime.now().isoformat(),
            category="preference",
            content=f"{preference_type}: {value}",
            metadata=metadata,
            relevance_score=0.95
        )
        
        self.in_memory_store["preference"].append(entry)
        
        # Store in ChromaDB
        if self.chroma_client and "user_preferences" in self.collections:
            try:
                self.collections["user_preferences"].add(
                    ids=[entry_id],
                    documents=[f"{preference_type}: {value}"],
                    metadatas=[metadata]
                )
            except Exception as e:
                logger.warning(f"Failed to store preference: {e}")
        
        return entry_id
    
    def store_skill(self,
                   agent_name: str,
                   skill_name: str,
                   proficiency_level: float,
                   improvement_rate: float) -> str:
        """Store skill proficiency for agent learning"""
        
        entry_id = self._generate_id(f"skill:{agent_name}:{skill_name}")
        
        metadata = {
            "agent": agent_name,
            "skill": skill_name,
            "proficiency": proficiency_level,
            "improvement_rate": improvement_rate
        }
        
        entry = MemoryEntry(
            id=entry_id,
            timestamp=datetime.now().isoformat(),
            category="skill",
            content=f"{agent_name} skill {skill_name}: {proficiency_level:.2%}",
            metadata=metadata,
            relevance_score=proficiency_level
        )
        
        self.in_memory_store["skill"].append(entry)
        return entry_id
    
    def find_similar_interactions(self, 
                                  query: str,
                                  category: str = "success",
                                  limit: int = 5) -> List[MemoryEntry]:
        """Find similar past interactions for retrieval-augmented generation"""
        
        # First try ChromaDB
        if self.chroma_client and "query_embeddings" in self.collections:
            try:
                results = self.collections["query_embeddings"].query(
                    query_texts=[query],
                    n_results=limit
                )
                if results and results.get("ids"):
                    return self._results_to_entries(results, category)
            except Exception as e:
                logger.warning(f"ChromaDB query failed: {e}")
        
        # Fallback to simple text matching
        return self._find_similar_in_memory(query, category, limit)
    
    def _find_similar_in_memory(self,
                               query: str,
                               category: str,
                               limit: int) -> List[MemoryEntry]:
        """Simple text similarity matching in memory"""
        
        entries = self.in_memory_store.get(category, [])
        
        query_words = set(query.lower().split())
        
        scored_entries = []
        for entry in entries:
            entry_words = set(entry.content.lower().split())
            # Simple Jaccard similarity
            intersection = len(query_words & entry_words)
            union = len(query_words | entry_words)
            similarity = intersection / union if union > 0 else 0
            
            if similarity > 0:
                scored_entries.append((entry, similarity))
        
        # Sort by similarity and relevance
        scored_entries.sort(
            key=lambda x: (-x[1], -x[0].relevance_score)
        )
        
        return [entry for entry, _ in scored_entries[:limit]]
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get accumulated user preferences"""
        
        preferences = {}
        
        for entry in self.in_memory_store.get("preference", []):
            if entry.metadata.get("user_id") == user_id:
                pref_type = entry.metadata.get("preference_type")
                value = entry.content.split(": ", 1)[-1]
                
                if pref_type not in preferences:
                    preferences[pref_type] = []
                preferences[pref_type].append({
                    "value": value,
                    "timestamp": entry.timestamp,
                    "access_count": entry.access_count
                })
        
        # Aggregate preferences
        aggregated = {}
        for pref_type, values in preferences.items():
            # Get most recent preference
            sorted_values = sorted(values, key=lambda x: x["timestamp"], reverse=True)
            aggregated[pref_type] = sorted_values[0]["value"] if sorted_values else None
        
        return aggregated
    
    def get_agent_skills(self, agent_name: str) -> Dict[str, float]:
        """Get agent's current skill proficiencies"""
        
        skills = {}
        
        for entry in self.in_memory_store.get("skill", []):
            if entry.metadata.get("agent") == agent_name:
                skill_name = entry.metadata.get("skill")
                proficiency = entry.metadata.get("proficiency", 0.0)
                skills[skill_name] = proficiency
        
        return skills
    
    def get_success_patterns(self, agent_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Extract patterns from successful interactions"""
        
        successes = self.in_memory_store.get("success", [])
        agent_successes = [
            e for e in successes 
            if e.metadata.get("agent") == agent_name
        ]
        
        # Sort by relevance and recency
        agent_successes.sort(
            key=lambda x: (-x.relevance_score, x.timestamp),
            reverse=True
        )
        
        patterns = []
        for entry in agent_successes[:limit]:
            patterns.append({
                "task": entry.metadata.get("task"),
                "tools_used": entry.metadata.get("tools_used", []),
                "model_used": entry.metadata.get("model"),
                "duration_ms": entry.metadata.get("duration_ms"),
                "timestamp": entry.timestamp
            })
        
        return patterns
    
    def learn_from_feedback(self,
                           interaction_id: str,
                           feedback: str,
                           rating: float) -> bool:
        """Learn from user feedback to improve responses"""
        
        entry_id = self._generate_id(f"feedback:{interaction_id}:{rating}")
        
        metadata = {
            "original_interaction": interaction_id,
            "rating": rating,
            "source": "user_feedback"
        }
        
        entry = MemoryEntry(
            id=entry_id,
            timestamp=datetime.now().isoformat(),
            category="insight",
            content=f"Feedback ({rating:.1f}/5): {feedback}",
            metadata=metadata,
            relevance_score=rating / 5.0
        )
        
        self.in_memory_store["insight"].append(entry)
        return True
    
    def export_learning_data(self) -> Dict[str, Any]:
        """Export learning data for analysis"""
        
        return {
            "exported_at": datetime.now().isoformat(),
            "total_entries": sum(len(entries) for entries in self.in_memory_store.values()),
            "by_category": {
                cat: len(entries)
                for cat, entries in self.in_memory_store.items()
            },
            "sample_entries": {
                cat: [asdict(e) for e in entries[:5]]
                for cat, entries in self.in_memory_store.items()
            }
        }
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID from content"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _results_to_entries(self, results: Dict, category: str) -> List[MemoryEntry]:
        """Convert ChromaDB results to MemoryEntry objects"""
        entries = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        
        for id_, doc, metadata in zip(ids, documents, metadatas):
            entry = MemoryEntry(
                id=id_,
                timestamp=metadata.get("timestamp", datetime.now().isoformat()),
                category=category,
                content=doc,
                metadata=metadata
            )
            entries.append(entry)
        
        return entries
    
    def cleanup_old_entries(self, days: int = 30):
        """Remove entries older than specified days"""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_timestamp = cutoff_date.isoformat()
        
        for category in self.in_memory_store:
            initial_count = len(self.in_memory_store[category])
            self.in_memory_store[category] = [
                e for e in self.in_memory_store[category]
                if e.timestamp > cutoff_timestamp
            ]
            removed = initial_count - len(self.in_memory_store[category])
            if removed > 0:
                logger.info(f"Cleaned up {removed} old entries from {category}")


# Global instance
_learning_engine: Optional[LearningEngine] = None


def get_learning_engine() -> LearningEngine:
    """Get or create the global learning engine"""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine()
    return _learning_engine


def reset_learning_engine():
    """Reset the learning engine (for testing)"""
    global _learning_engine
    _learning_engine = None
