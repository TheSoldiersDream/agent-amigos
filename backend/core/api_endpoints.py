"""
API Endpoints for Enhanced AI Functionality
Exposes model management, learning statistics, and agent capabilities
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
import logging

# NOTE: This project is commonly launched with cwd=./backend (see VS Code tasks).
# In that mode, imports like `backend.core.*` will fail because there is no
# `backend/` package under the current working directory.
try:
    from core.model_manager import get_model_manager, ModelType
    from core.learning_engine import get_learning_engine
    from core.adaptive_agent import get_or_create_agent, get_agent_registry
except Exception:  # pragma: no cover
    from backend.core.model_manager import get_model_manager, ModelType
    from backend.core.learning_engine import get_learning_engine
    from backend.core.adaptive_agent import get_or_create_agent, get_agent_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

# ===== Model Management Endpoints =====

@router.get("/models/available")
def get_available_models(provider: Optional[str] = None, 
                        model_type: Optional[str] = None) -> Dict[str, Any]:
    """Get list of available models with optional filtering"""
    
    manager = get_model_manager()
    
    # Convert string to ModelType enum if provided
    model_type_enum = None
    if model_type:
        try:
            model_type_enum = ModelType(model_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid model type: {model_type}")
    
    models = manager.list_models(
        provider=provider,
        model_type=model_type_enum
    )
    
    return {
        "total": len(models),
        "models": [model.to_dict() for model in models]
    }


@router.get("/models/config")
def get_models_config() -> Dict[str, Any]:
    """Get complete model configuration and learning statistics"""
    
    manager = get_model_manager()
    
    return manager.export_config()


@router.get("/models/{model_id}")
def get_model_details(model_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific model"""
    
    manager = get_model_manager()
    model = manager.get_model(model_id)
    
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    return {
        "model": model.to_dict(),
        "stats": manager.learning_stats.get(model_id, {})
    }


@router.post("/models/select")
def select_model(model_id: str) -> Dict[str, Any]:
    """Select a model for the current session"""
    
    manager = get_model_manager()
    model = manager.get_model(model_id)
    
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    # In a real implementation, this would update session state
    return {
        "message": f"Selected model: {model.name}",
        "model": model.to_dict()
    }


@router.get("/models/best-for-task")
def get_best_model_for_task(task_type: str, prefer_local: bool = False) -> Dict[str, Any]:
    """Get the best model for a specific task type"""
    
    manager = get_model_manager()
    model = manager.get_best_model_for_task(task_type, prefer_local=prefer_local)
    
    if not model:
        raise HTTPException(status_code=404, detail="No suitable model found")
    
    return {
        "model": model.to_dict(),
        "reasoning": f"Selected for task type: {task_type}"
    }


@router.get("/models/stats")
def get_models_statistics() -> Dict[str, Any]:
    """Get comprehensive learning statistics across all models"""
    
    manager = get_model_manager()
    stats = manager.get_learning_statistics()
    
    return stats


# ===== Agent Capabilities Endpoints =====

@router.get("/capabilities")
def get_all_agents_capabilities() -> Dict[str, Any]:
    """Get capabilities and status of all agents"""
    
    agents_dict = get_agent_registry()
    
    agents_list = []
    for agent_name, agent in agents_dict.items():
        status = agent.get_agent_status()
        agents_list.append({
            "name": agent_name,
            "type": status["type"],
            "total_interactions": status["total_interactions"],
            "success_rate": status["success_rate"],
            "learning_enabled": status["learning_enabled"]
        })
    
    return {
        "total_agents": len(agents_list),
        "agents": agents_list
    }


@router.get("/capabilities/{agent_name}")
def get_agent_capabilities(agent_name: str) -> Dict[str, Any]:
    """Get detailed capabilities for a specific agent"""
    
    agent = get_or_create_agent(agent_name)
    status = agent.get_agent_status()
    
    return status


@router.post("/voice/fix")
async def fix_voice_transcript(transcript: str = Query(...), agent_name: str = "default") -> Dict[str, Any]:
    """Fix common Speech-to-Text errors using LLM context"""
    
    agent = get_or_create_agent(agent_name)
    corrected = await agent.fix_transcript(transcript)
    
    return {
        "original": transcript,
        "corrected": corrected,
        "changed": corrected.lower() != transcript.lower()
    }


@router.post("/agent/{agent_name}/execute")
async def execute_agent_task(agent_name: str,
                            task: str,
                            reasoning_strategy: Optional[str] = None) -> Dict[str, Any]:
    """Execute a task using a specific agent"""

    try:
        from core.adaptive_agent import ReasoningStrategy
    except Exception:  # pragma: no cover
        from backend.core.adaptive_agent import ReasoningStrategy
    
    agent = get_or_create_agent(agent_name)
    
    strategy = ReasoningStrategy.ADAPTIVE
    if reasoning_strategy:
        try:
            strategy = ReasoningStrategy[reasoning_strategy.upper()]
        except KeyError:
            strategy = ReasoningStrategy.ADAPTIVE
    
    result = await agent.execute_task(
        task=task,
        reasoning_strategy=strategy
    )
    
    return result


@router.get("/agent/{agent_name}/skills")
def get_agent_skills(agent_name: str) -> Dict[str, Any]:
    """Get learned skills for an agent"""
    
    engine = get_learning_engine()
    skills = engine.get_agent_skills(agent_name)
    
    return {
        "agent": agent_name,
        "skills": skills,
        "total_skills": len(skills),
        "proficiency_average": (
            sum(skills.values()) / len(skills)
            if skills else 0
        )
    }


@router.get("/agent/{agent_name}/patterns")
def get_success_patterns(agent_name: str,
                        limit: int = Query(10, ge=1, le=50)) -> Dict[str, Any]:
    """Get successful interaction patterns for an agent"""
    
    engine = get_learning_engine()
    patterns = engine.get_success_patterns(agent_name, limit=limit)
    
    return {
        "agent": agent_name,
        "patterns": patterns,
        "total_patterns": len(patterns)
    }


# ===== Learning & Feedback Endpoints =====

@router.post("/learning/feedback")
def submit_feedback(interaction_id: str,
                   feedback: str,
                   rating: float) -> Dict[str, Any]:
    """Submit feedback for an interaction to improve learning"""
    
    if not 0 <= rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 0 and 5")
    
    engine = get_learning_engine()
    success = engine.learn_from_feedback(interaction_id, feedback, rating)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to store feedback")
    
    return {
        "message": "Feedback recorded successfully",
        "interaction_id": interaction_id,
        "rating": rating
    }


@router.get("/learning/stats")
def get_learning_statistics() -> Dict[str, Any]:
    """Get comprehensive learning statistics"""
    
    engine = get_learning_engine()
    
    return {
        "learning_data": engine.export_learning_data()
    }


@router.get("/learning/preferences/{user_id}")
def get_user_preferences(user_id: str) -> Dict[str, Any]:
    """Get learned user preferences"""
    
    engine = get_learning_engine()
    preferences = engine.get_user_preferences(user_id)
    
    return {
        "user_id": user_id,
        "preferences": preferences
    }


@router.post("/learning/preference")
def store_user_preference(user_id: str,
                         preference_type: str,
                         value: str,
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Store a user preference for adaptation"""
    
    engine = get_learning_engine()
    preference_id = engine.store_preference(user_id, preference_type, value, context)
    
    return {
        "message": "Preference stored successfully",
        "preference_id": preference_id,
        "user_id": user_id,
        "preference_type": preference_type
    }


# ===== Model Recording Endpoints =====

@router.post("/models/record-interaction")
def record_model_interaction(model_id: str,
                            task_type: str,
                            success: bool,
                            response_time_ms: float,
                            tokens_used: int) -> Dict[str, Any]:
    """Record a model interaction for learning"""
    
    manager = get_model_manager()
    manager.record_interaction(
        model_id=model_id,
        task_type=task_type,
        success=success,
        response_time_ms=response_time_ms,
        tokens_used=tokens_used
    )
    
    return {
        "message": "Interaction recorded",
        "model_id": model_id,
        "success": success
    }


# ===== Health & Info Endpoints =====

@router.get("/models/health")
def check_models_health() -> Dict[str, Any]:
    """Check health of available models"""
    
    manager = get_model_manager()
    models = manager.list_models()
    
    health_status = {
        "total_models": len(models),
        "local_models": len([m for m in models if m.local]),
        "remote_models": len([m for m in models if not m.local]),
        "models": [
            {
                "name": m.name,
                "provider": m.provider,
                "local": m.local,
                "success_rate": m.success_rate,
                "available": True  # In real impl, check actual availability
            }
            for m in models
        ]
    }
    
    return health_status


@router.get("/agents/health")
def check_agents_health() -> Dict[str, Any]:
    """Check health of all agents"""
    
    agents_dict = get_agent_registry()
    
    health_status = {
        "total_agents": len(agents_dict),
        "agents": {}
    }
    
    for agent_name, agent in agents_dict.items():
        status = agent.get_agent_status()
        health_status["agents"][agent_name] = {
            "type": status["type"],
            "total_interactions": status["total_interactions"],
            "success_rate": status["success_rate"],
            "learning_enabled": status["learning_enabled"],
            "status": "healthy" if status["success_rate"] > 0.6 else "needs_training"
        }
    
    return health_status
