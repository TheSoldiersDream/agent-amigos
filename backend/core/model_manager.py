"""
Enhanced Model Manager for Agent Amigos
Supports Ollama, HuggingFace, OpenAI, DeepSeek, Grok, Groq, and OpenRouter
Implements intelligent multi-model routing and self-learning
"""

import os
import json
import httpx
import logging
import asyncio
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime

# Prefer local models by default to avoid hitting external provider rate limits.
# Default is FALSE to keep existing behavior unchanged; set env PREFER_LOCAL_MODELS=true to opt-in.
PREFER_LOCAL_MODELS = os.getenv("PREFER_LOCAL_MODELS", "false").lower() in ("1", "true", "yes")
# Retry settings for handling transient provider rate limits (429)
MAX_PROVIDER_RETRIES = int(os.getenv("MAX_PROVIDER_RETRIES", "3"))
INITIAL_RETRY_BACKOFF = float(os.getenv("INITIAL_RETRY_BACKOFF", "0.5"))  # seconds

logger = logging.getLogger(__name__)

class ModelType(str, Enum):
    """Model capability types"""
    REASONING = "reasoning"  # Complex problem solving
    CODING = "coding"        # Code generation & understanding
    GENERAL = "general"      # General conversation
    FAST = "fast"            # Quick responses
    MULTIMODAL = "multimodal"  # Image/video understanding
    SEARCH = "search"        # Information retrieval
    EMBEDDING = "embedding"  # Vector embeddings


class ModelCapability:
    """Represents a model's capabilities and metadata"""
    
    def __init__(
        self,
        name: str,
        provider: str,
        model_id: str,
        types: List[ModelType],
        context_window: int = 4096,
        cost_per_1k_input: float = 0.0,
        cost_per_1k_output: float = 0.0,
        supports_function_calling: bool = False,
        supports_vision: bool = False,
        local: bool = False,
        description: str = "",
        last_used: Optional[datetime] = None,
        success_rate: float = 0.95,
        avg_latency_ms: float = 0.0
    ):
        self.name = name
        self.provider = provider
        self.model_id = model_id
        self.types = types
        self.context_window = context_window
        self.cost_per_1k_input = cost_per_1k_input
        self.cost_per_1k_output = cost_per_1k_output
        self.supports_function_calling = supports_function_calling
        self.supports_vision = supports_vision
        self.local = local
        self.description = description
        self.last_used = last_used
        self.success_rate = success_rate
        self.avg_latency_ms = avg_latency_ms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "provider": self.provider,
            "model_id": self.model_id,
            "types": [t.value for t in self.types],
            "context_window": self.context_window,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "supports_function_calling": self.supports_function_calling,
            "supports_vision": self.supports_vision,
            "local": self.local,
            "description": self.description,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "success_rate": self.success_rate,
            "avg_latency_ms": self.avg_latency_ms
        }


class ModelManager:
    """Manages available models, routing, and learning statistics"""
    
    def __init__(self):
        self.models: Dict[str, ModelCapability] = {}
        self.learning_stats: Dict[str, Dict[str, Any]] = {}
        self.interaction_history: List[Dict[str, Any]] = []
        self.provider_health: Dict[str, Dict[str, Any]] = {}
        self._initialize_models()

        # Best-effort discovery of locally installed Ollama models.
        # Never fail startup if Ollama isn't running.
        try:
            self.refresh_ollama_models()
        except Exception:
            pass

    def _ollama_base_url(self) -> str:
        # Support both env var names seen across this repo and common setups.
        return (
            os.getenv("OLLAMA_BASE_URL")
            or os.getenv("OLLAMA_ENDPOINT")
            or "http://localhost:11434"
        ).rstrip("/")

    def refresh_ollama_models(self, timeout_s: float = 1.5) -> Dict[str, Any]:
        """Discover locally installed Ollama models and merge into registry.

        Uses Ollama's REST API: GET /api/tags
        """

        base_url = self._ollama_base_url()
        url = f"{base_url}/api/tags"

        health: Dict[str, Any] = {
            "provider": "ollama",
            "base_url": base_url,
            "reachable": False,
            "error": None,
            "model_count": 0,
            "checked_at": datetime.now().isoformat(),
        }

        try:
            with httpx.Client(timeout=timeout_s) as client:
                resp = client.get(url)
                resp.raise_for_status()
                payload = resp.json()

            models = payload.get("models", []) if isinstance(payload, dict) else []
            discovered_ids: List[str] = []

            for m in models:
                model_id = str(m.get("name") or "").strip()
                if not model_id:
                    continue
                discovered_ids.append(model_id)

                if model_id not in self.models:
                    inferred = self._infer_ollama_capability(model_id)
                    self.register_model(inferred)

            health["reachable"] = True
            health["model_count"] = len(discovered_ids)
            health["models"] = discovered_ids
        except Exception as exc:
            health["error"] = str(exc)[:200]

        self.provider_health["ollama"] = health
        return health

    def _infer_ollama_capability(self, model_id: str) -> ModelCapability:
        """Heuristic capability inference for Ollama-discovered models."""

        mid = model_id.lower()
        name = model_id
        types: List[ModelType] = [ModelType.GENERAL]
        ctx = 4096
        supports_tools = True
        supports_vision = False

        # Embeddings
        if "embed" in mid or "embedding" in mid:
            types = [ModelType.EMBEDDING, ModelType.SEARCH]
            supports_tools = False
            ctx = 2048

        # Vision
        if "vision" in mid or "vl" in mid or mid.startswith("llava"):
            supports_vision = True
            if ModelType.MULTIMODAL not in types:
                types.append(ModelType.MULTIMODAL)

        # Coder models
        if "coder" in mid or "code" in mid or "devstral" in mid or "codestral" in mid:
            if ModelType.CODING not in types:
                types.append(ModelType.CODING)

        # Reasoning models
        if "r1" in mid or "reason" in mid or "think" in mid or mid.startswith("deepseek-r1"):
            if ModelType.REASONING not in types:
                types.append(ModelType.REASONING)

        # Known context windows from Ollama library (best-effort defaults)
        if mid.startswith("llama3.3"):
            ctx = 128000
            name = "Llama 3.3"
        elif mid.startswith("qwen2.5"):
            ctx = 32768
            name = "Qwen 2.5"
        elif mid.startswith("qwen3-coder"):
            ctx = 256000
            name = "Qwen3-Coder"
        elif mid.startswith("deepseek-r1"):
            ctx = 128000
            name = "DeepSeek-R1"
        elif mid.startswith("devstral"):
            ctx = 128000
            name = "Devstral"
        elif mid.startswith("phi4-reasoning"):
            ctx = 32768
            name = "Phi-4 Reasoning"
        elif mid.startswith("nemotron"):
            ctx = 4096
            name = "Nemotron-3"
        elif mid.startswith("nomic-embed-text"):
            ctx = 2048
            name = "nomic-embed-text"

        return ModelCapability(
            name=name,
            provider="ollama",
            model_id=model_id,
            types=types,
            context_window=ctx,
            supports_function_calling=supports_tools,
            supports_vision=supports_vision,
            local=True,
            description="Discovered from local Ollama (/api/tags)",
            success_rate=0.90,
        )
    
    def _initialize_models(self):
        """Initialize all available models"""
        
        # ===== Open-Source Models (via Ollama) =====
        # Reasoning/Complex Tasks
        # Reasoning/Complex Tasks (current Ollama library IDs)
        self.register_model(ModelCapability(
            name="Qwen 2.5 72B",
            provider="ollama",
            model_id="qwen2.5:72b",
            types=[ModelType.REASONING, ModelType.CODING],
            # Ollama's qwen2.5 tags list 32K context by default.
            context_window=32768,
            local=True,
            supports_function_calling=True,
            description="Alibaba's Qwen2.5 - strong reasoning, coding, and structured output",
            success_rate=0.96
        ))
        
        self.register_model(ModelCapability(
            name="DeepSeek-R1 (local)",
            provider="ollama",
            model_id="deepseek-r1:8b",
            types=[ModelType.REASONING],
            context_window=128000,
            local=True,
            supports_function_calling=True,
            description="Open reasoning model family; distilled variants run locally (default: 8B)",
            success_rate=0.95
        ))
        
        self.register_model(ModelCapability(
            name="Llama 3.3 70B",
            provider="ollama",
            model_id="llama3.3:70b",
            types=[ModelType.REASONING, ModelType.GENERAL, ModelType.CODING],
            context_window=128000,
            local=True,
            supports_function_calling=True,
            description="Meta's Llama 3.3 (70B) with 128K context and tool-use support",
            success_rate=0.94
        ))
        
        # Fast Inference
        self.register_model(ModelCapability(
            name="Devstral 24B",
            provider="ollama",
            model_id="devstral:24b",
            types=[ModelType.CODING, ModelType.REASONING],
            context_window=128000,
            local=True,
            supports_function_calling=True,
            description="Agentic coding model (SWE-bench focused) with 128K context",
            success_rate=0.93
        ))
        
        self.register_model(ModelCapability(
            name="Phi-4 Reasoning (14B)",
            provider="ollama",
            model_id="phi4-reasoning:14b",
            types=[ModelType.REASONING, ModelType.FAST],
            context_window=32768,
            local=True,
            supports_function_calling=True,
            description="Compact open-weight reasoning model; plus variant available",
            success_rate=0.90
        ))

        self.register_model(ModelCapability(
            name="Nemotron-3 Nano",
            provider="ollama",
            model_id="nemotron-3-nano",
            types=[ModelType.GENERAL, ModelType.FAST],
            context_window=4096,
            local=True,
            supports_function_calling=True,
            description="NVIDIA's Nemotron-3 nano - optimized for fast, compact performance (2025)",
            success_rate=0.94
        ))

        # Long-context coding (optional, larger)
        self.register_model(ModelCapability(
            name="Qwen3-Coder 30B",
            provider="ollama",
            model_id="qwen3-coder:30b",
            types=[ModelType.CODING, ModelType.REASONING],
            context_window=256000,
            local=True,
            supports_function_calling=True,
            description="Agentic coding + repo-scale context (256K)",
            success_rate=0.92,
        ))

        # Embeddings for RAG/memory
        self.register_model(ModelCapability(
            name="nomic-embed-text (embeddings)",
            provider="ollama",
            model_id="nomic-embed-text:v1.5",
            types=[ModelType.EMBEDDING, ModelType.SEARCH],
            context_window=2048,
            local=True,
            supports_function_calling=False,
            description="Embedding model for retrieval and memory search",
            success_rate=0.98,
        ))
        
        # ===== Commercial Models (Fallback) =====
        self.register_model(ModelCapability(
            name="GPT-4o",
            provider="openai",
            model_id="gpt-4o",
            types=[ModelType.REASONING, ModelType.MULTIMODAL, ModelType.CODING],
            context_window=128000,
            cost_per_1k_input=0.005,
            cost_per_1k_output=0.015,
            supports_function_calling=True,
            supports_vision=True,
            description="OpenAI's most capable model",
            success_rate=0.99
        ))
        
        self.register_model(ModelCapability(
            name="GPT-4o Mini",
            provider="openai",
            model_id="gpt-4o-mini",
            types=[ModelType.FAST, ModelType.GENERAL],
            context_window=128000,
            cost_per_1k_input=0.00015,
            cost_per_1k_output=0.0006,
            supports_function_calling=True,
            supports_vision=True,
            description="Fast and cost-effective variant",
            success_rate=0.95
        ))
        
        # Grok (X.AI)
        self.register_model(ModelCapability(
            name="Grok Beta",
            provider="grok",
            model_id="grok-beta",
            types=[ModelType.REASONING, ModelType.GENERAL],
            context_window=128000,
            supports_function_calling=True,
            description="X.AI's reasoning model with real-time info",
            success_rate=0.92
        ))
        
        # Groq
        self.register_model(ModelCapability(
            name="Llama 3.3 70B (Groq)",
            provider="groq",
            model_id="llama-3.3-70b-versatile",
            types=[ModelType.REASONING, ModelType.GENERAL, ModelType.FAST],
            context_window=8192,
            supports_function_calling=True,
            description="Ultra-fast Llama inference via Groq",
            avg_latency_ms=200,
            success_rate=0.94
        ))
        
        # Google's Models
        self.register_model(ModelCapability(
            name="Gemini 2.0 Flash",
            provider="openrouter",
            model_id="google/gemini-2.0-flash-001",
            types=[ModelType.REASONING, ModelType.MULTIMODAL, ModelType.FAST],
            context_window=1000000,
            cost_per_1k_input=0.0001,
            cost_per_1k_output=0.0004,
            supports_vision=True,
            description="Google's latest multimodal model",
            success_rate=0.96
        ))
        
        # Add learning stats for each model
        for model_id in self.models:
            self.learning_stats[model_id] = {
                "total_uses": 0,
                "successful_uses": 0,
                "total_tokens": 0,
                "avg_response_time": 0.0,
                "task_proficiency": {}
            }
    
    def register_model(self, model: ModelCapability):
        """Register a new model"""
        self.models[model.model_id] = model
        logger.info(f"Registered model: {model.name} ({model.model_id})")
    
    def get_model(self, model_id: str) -> Optional[ModelCapability]:
        """Get a model by ID"""
        return self.models.get(model_id)
    
    def list_models(self, 
                   provider: Optional[str] = None,
                   model_type: Optional[ModelType] = None,
                   local_only: bool = False) -> List[ModelCapability]:
        """List models with optional filtering"""
        filtered = list(self.models.values())
        
        if provider:
            filtered = [m for m in filtered if m.provider == provider]
        if model_type:
            filtered = [m for m in filtered if model_type in m.types]
        if local_only:
            filtered = [m for m in filtered if m.local]
        
        return filtered
    
    def _should_prefer_local_for_task(self, task_type: str) -> bool:
        """Decide whether to prefer local models for the given task (configurable via env)."""
        t = task_type.lower()
        return PREFER_LOCAL_MODELS and t in ("reasoning", "code")

    def get_best_model_for_task(self, task_type: str, 
                               prefer_local: Optional[bool] = None) -> Optional[ModelCapability]:
        """Intelligent model routing based on task type

        If prefer_local is not provided, it defaults to environment-driven behavior
        for critical tasks (coding/reasoning) so we avoid external provider calls.
        """
        # Map task to model type
        task_to_type = {
            "reasoning": ModelType.REASONING,
            "code": ModelType.CODING,
            "fast": ModelType.FAST,
            "search": ModelType.SEARCH,
            "vision": ModelType.MULTIMODAL,
            "general": ModelType.GENERAL,
        }
        model_type = task_to_type.get(task_type.lower(), ModelType.GENERAL)

        # Default prefer_local if not explicitly set
        if prefer_local is None:
            prefer_local = self._should_prefer_local_for_task(task_type)

        # Get candidate models
        candidates = [m for m in self.models.values() if model_type in m.types]

        if prefer_local:
            local_candidates = [m for m in candidates if m.local]
            if local_candidates:
                candidates = local_candidates

        if not candidates:
            # Fallback to general model
            candidates = [m for m in self.models.values() if ModelType.GENERAL in m.types]

        # Sort by success rate and recency
        candidates.sort(
            key=lambda m: (
                -m.success_rate,
                -(m.last_used.timestamp() if m.last_used else 0)
            )
        )

        return candidates[0] if candidates else None
    
    def record_interaction(self, 
                         model_id: str,
                         task_type: str,
                         success: bool,
                         response_time_ms: float,
                         tokens_used: int):
        """Record model interaction for learning"""
        
        if model_id not in self.learning_stats:
            self.learning_stats[model_id] = {
                "total_uses": 0,
                "successful_uses": 0,
                "total_tokens": 0,
                "avg_response_time": 0.0,
                "task_proficiency": {}
            }
        
        stats = self.learning_stats[model_id]
        stats["total_uses"] += 1
        
        if success:
            stats["successful_uses"] += 1
        
        stats["total_tokens"] += tokens_used
        
        # Update average response time
        old_avg = stats["avg_response_time"]
        stats["avg_response_time"] = (
            (old_avg * (stats["total_uses"] - 1) + response_time_ms) / 
            stats["total_uses"]
        )
        
        # Track task-specific proficiency
        if task_type not in stats["task_proficiency"]:
            stats["task_proficiency"][task_type] = {"success": 0, "total": 0}
        
        stats["task_proficiency"][task_type]["total"] += 1
        if success:
            stats["task_proficiency"][task_type]["success"] += 1
        
        # Update model success rate
        model = self.models.get(model_id)
        if model:
            model.success_rate = stats["successful_uses"] / stats["total_uses"]
            model.last_used = datetime.now()
        
        # Store in history
        self.interaction_history.append({
            "timestamp": datetime.now().isoformat(),
            "model_id": model_id,
            "task_type": task_type,
            "success": success,
            "response_time_ms": response_time_ms,
            "tokens_used": tokens_used
        })
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get comprehensive learning statistics"""
        return {
            "total_interactions": len(self.interaction_history),
            "model_stats": self.learning_stats,
            "model_rankings": self._get_model_rankings(),
            "best_models_by_task": self._get_best_models_by_task()
        }
    
    def _get_model_rankings(self) -> List[Dict[str, Any]]:
        """Rank models by success rate"""
        rankings = []
        for model_id, stats in self.learning_stats.items():
            if stats["total_uses"] > 0:
                rankings.append({
                    "model_id": model_id,
                    "model_name": self.models[model_id].name,
                    "success_rate": stats["successful_uses"] / stats["total_uses"],
                    "total_uses": stats["total_uses"],
                    "avg_response_time": stats["avg_response_time"]
                })
        
        rankings.sort(key=lambda x: -x["success_rate"])
        return rankings
    
    def _get_best_models_by_task(self) -> Dict[str, str]:
        """Get best model for each task type"""
        best_by_task = {}
        
        for model_id, stats in self.learning_stats.items():
            for task_type, proficiency in stats["task_proficiency"].items():
                success_rate = (
                    proficiency["success"] / proficiency["total"]
                    if proficiency["total"] > 0 else 0
                )
                
                if task_type not in best_by_task:
                    best_by_task[task_type] = {
                        "model_id": model_id,
                        "model_name": self.models[model_id].name,
                        "success_rate": success_rate
                    }
                elif success_rate > best_by_task[task_type]["success_rate"]:
                    best_by_task[task_type] = {
                        "model_id": model_id,
                        "model_name": self.models[model_id].name,
                        "success_rate": success_rate
                    }
        
        return best_by_task
    
    def export_config(self) -> Dict[str, Any]:
        """Export configuration for UI"""
        return {
            "available_models": {
                model_id: model.to_dict()
                for model_id, model in self.models.items()
            },
            "provider_health": self.provider_health,
            "learning_stats": self.get_learning_statistics()
        }

    async def generate(
        self,
        model_id: str,
        prompt: str,
        system: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a response from a specific model.
        Routes to the appropriate provider API.
        """
        
        model = self.get_model(model_id)
        if not model:
            return {"success": False, "error": f"Model {model_id} not found"}
            
        start_time = datetime.now()
        
        try:
            if model.provider == "ollama":
                result = await self._generate_ollama(model, prompt, system, messages, temperature, max_tokens)
            elif model.provider == "openai":
                result = await self._generate_openai(model, prompt, system, messages, temperature, max_tokens)
            elif model.provider == "groq":
                result = await self._generate_groq(model, prompt, system, messages, temperature, max_tokens)
            elif model.provider == "openrouter":
                result = await self._generate_openrouter(model, prompt, system, messages, temperature, max_tokens)
            else:
                result = {"success": False, "error": f"Provider {model.provider} not supported"}
            
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Record interaction for learning
            if result.get("success"):
                self.record_interaction(
                    model_id=model_id,
                    task_type="general", # Should be passed in
                    success=True,
                    response_time_ms=duration_ms,
                    tokens_used=result.get("usage", {}).get("total_tokens", 0)
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Generation failed for {model_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _generate_ollama(self, model, prompt, system, messages, temperature, max_tokens):
        base_url = self._ollama_base_url()
        
        if messages:
            url = f"{base_url}/api/chat"
            payload = {
                "model": model.model_id,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature}
            }
            if system:
                payload["messages"].insert(0, {"role": "system", "content": system})
        else:
            url = f"{base_url}/api/generate"
            payload = {
                "model": model.model_id,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature}
            }
            if system:
                payload["system"] = system
        
        if max_tokens:
            payload.setdefault("options", {})["num_predict"] = max_tokens
            
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            response_text = data.get("message", {}).get("content", "") if messages else data.get("response", "")
            
            return {
                "success": True,
                "response": response_text,
                "model": model.model_id,
                "usage": {
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                }
            }

    async def _generate_openai(self, model, prompt, system, messages, temperature, max_tokens):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"success": False, "error": "OPENAI_API_KEY not set"}
            
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        if not messages:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
        payload = {
            "model": model.model_id,
            "messages": messages,
            "temperature": temperature
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "success": True,
                "response": data["choices"][0]["message"]["content"],
                "model": model.model_id,
                "usage": data.get("usage", {})
            }

    async def _generate_groq(self, model, prompt, system, messages, temperature, max_tokens):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return {"success": False, "error": "GROQ_API_KEY not set"}
            
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        if not messages:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
        payload = {
            "model": model.model_id,
            "messages": messages,
            "temperature": temperature
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "success": True,
                "response": data["choices"][0]["message"]["content"],
                "model": model.model_id,
                "usage": data.get("usage", {})
            }

    async def _generate_openrouter(self, model, prompt, system, messages, temperature, max_tokens):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return {"success": False, "error": "OPENROUTER_API_KEY not set"}
            
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/darrellbuttigieg/AgentAmigos",
            "X-Title": "Agent Amigos"
        }
        
        if not messages:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
        payload = {
            "model": model.model_id,
            "messages": messages,
            "temperature": temperature
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "success": True,
                "response": data["choices"][0]["message"]["content"],
                "model": model.model_id,
                "usage": data.get("usage", {})
            }


# Global instance
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get or create the global model manager"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager


def reset_model_manager():
    """Reset the model manager (for testing)"""
    global _model_manager
    _model_manager = None
