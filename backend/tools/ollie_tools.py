"""
Ollama Tools - Local LLM Integration for Agent Amigos
======================================================
Provides integration with locally running Ollama models.
Agent Amigos manages when and how Ollama is utilized.

Supported Models:
- qwen2.5:7b (4.7GB) - Smarter, better reasoning
- llama3.2:latest (2.0GB) - Faster, lighter tasks

All models share local memory with Amigos for self-learning.
"""

import aiohttp
import asyncio
import os
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit
from typing import Optional, Dict, Any, List
from config import get_default_model
import logging
import json

# Import shared memory system
from tools.shared_memory import (
    shared_memory,
    remember_conversation,
    learn,
    recall,
    get_context,
    log_task_completion
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA SERVICE CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class OllamaService:
    """
    Service for interacting with local Ollama API.
    Agent Amigos uses this to delegate tasks to local LLMs.
    """
    
    BASE_URL = "http://127.0.0.1:11434"
    
    # Model recommendations for different task types
    MODEL_ROUTING = {
        # Users may override these per deployment; default to Raptor Mini (Preview)
        "complex_reasoning": "qwen2.5:7b",
        "quick_response": "llama3.2:latest",
        "creative_writing": "qwen2.5:7b",
        "code_generation": "qwen2.5:7b",
        "summarization": "llama3.2:latest",
        "translation": "qwen2.5:7b",
        # Default model: prefer raptor-mini if available (preview)
        "default": "raptor-mini"
    }
    
    def __init__(self):
        self.base_url = self._resolve_base_url()
        self.timeout = aiohttp.ClientTimeout(total=120)  # 2 minute timeout for generation
        self._session: Optional[aiohttp.ClientSession] = None

    def _resolve_base_url(self) -> str:
        """Resolve Ollama base URL.

        Supports either the native Ollama REST API (e.g. http://127.0.0.1:11434)
        or an OpenAI-compatible base URL (e.g. http://127.0.0.1:11434/v1).

        Env precedence:
        - OLLAMA_BASE_URL: native Ollama REST API base
        - OLLAMA_API_BASE: OpenAI-compatible base (we strip path like /v1)
        """

        raw = (os.environ.get("OLLAMA_BASE_URL") or "").strip()
        if raw:
            return raw.rstrip("/")

        raw = (os.environ.get("OLLAMA_API_BASE") or "").strip()
        if raw:
            parsed = urlsplit(raw)
            if parsed.scheme and parsed.netloc:
                # Keep only scheme://netloc for native endpoints.
                return urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")
            return raw.rstrip("/")

        return self.BASE_URL
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session
    
    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    # ───────────────────────────────────────────────────────────────────────────
    # STATUS & MODEL MANAGEMENT
    # ───────────────────────────────────────────────────────────────────────────
    
    async def check_status(self) -> Dict[str, Any]:
        """
        Check if Ollama is running and responsive.
        
        Returns:
            Dict with status information
        """
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get("models", [])
                    return {
                        "running": True,
                        "status": "online",
                        "model_count": len(models),
                        "models": [m.get("name", "unknown") for m in models],
                        "base_url": self.base_url
                    }
                else:
                    return {
                        "running": False,
                        "status": "error",
                        "error": f"HTTP {response.status}"
                    }
        except (aiohttp.ClientConnectorError, aiohttp.ClientConnectionError):
            return {
                "running": False,
                "status": "offline",
                "error": f"Cannot connect to Ollama at {self.base_url}. Is it running (ollama serve)?"
            }
        except Exception as e:
            return {
                "running": False,
                "status": "error",
                "error": str(e)
            }
    
    async def list_models(self) -> Dict[str, Any]:
        """
        List all available Ollama models.
        
        Returns:
            Dict with models list and metadata
        """
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = []
                    for m in data.get("models", []):
                        size_gb = m.get("size", 0) / (1024 ** 3)
                        models.append({
                            "name": m.get("name", "unknown"),
                            "size": f"{size_gb:.1f}GB",
                            "size_bytes": m.get("size", 0),
                            "modified": m.get("modified_at", ""),
                            "family": m.get("details", {}).get("family", "unknown"),
                            "parameter_size": m.get("details", {}).get("parameter_size", "unknown"),
                            "quantization": m.get("details", {}).get("quantization_level", "unknown")
                        })
                    
                    return {
                        "success": True,
                        "models": models,
                        "count": len(models),
                        "recommended": {
                            "smart": "qwen2.5:7b",
                            "fast": "llama3.2:latest"
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}",
                        "models": []
                    }
        except (aiohttp.ClientConnectorError, aiohttp.ClientConnectionError) as e:
            return {
                "success": False,
                "error": f"Cannot connect to Ollama at {self.base_url}: {e}",
                "models": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "models": []
            }
    
    def get_recommended_model(self, task_type: str = "default") -> str:
        """
        Get the recommended model for a task type.
        Agent Amigos uses this to route tasks appropriately.
        
        Args:
            task_type: Type of task (complex_reasoning, quick_response, etc.)
            
        Returns:
            Model name string
        """
        if task_type == "default":
            # Use configured default model if available
            default_model = get_default_model()
            if default_model:
                return default_model
        return self.MODEL_ROUTING.get(task_type, self.MODEL_ROUTING["default"])
    
    # ───────────────────────────────────────────────────────────────────────────
    # GENERATION METHODS
    # ───────────────────────────────────────────────────────────────────────────
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        task_type: str = "default",
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a response from Ollama.
        
        Args:
            prompt: The prompt to send
            model: Model to use (or None for auto-selection)
            task_type: Type of task for auto model selection
            system: Optional system prompt
            temperature: Creativity (0.0-1.0)
            max_tokens: Max tokens to generate
            stream: Whether to stream response
            
        Returns:
            Dict with response or error
        """
        # Auto-select model if not specified
        if model is None:
            model = self.get_recommended_model(task_type)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature
            }
        }
        
        if system:
            payload["system"] = system
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "response": data.get("response", ""),
                        "model": model,
                        "task_type": task_type,
                        "done": data.get("done", True),
                        "eval_count": data.get("eval_count", 0),
                        "eval_duration": data.get("eval_duration", 0)
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}",
                        "model": model
                    }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Request timed out. The model may be loading or the prompt too complex.",
                "model": model
            }
        except (aiohttp.ClientConnectorError, aiohttp.ClientConnectionError) as e:
            return {
                "success": False,
                "error": f"Cannot connect to Ollama at {self.base_url}: {e}. Start Ollama with 'ollama serve' and ensure port 11434 is reachable.",
                "model": model
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": model
            }
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        task_type: str = "default",
        system: Optional[str] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Chat with Ollama using conversation history.
        
        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            model: Model to use (or None for auto-selection)
            task_type: Type of task for auto model selection
            system: Optional system prompt
            temperature: Creativity (0.0-1.0)
            
        Returns:
            Dict with response or error
        """
        # Auto-select model if not specified
        if model is None:
            model = self.get_recommended_model(task_type)
        
        # Build Ollama message format
        ollama_messages = []
        
        # Add system message if provided
        if system:
            ollama_messages.append({
                "role": "system",
                "content": system
            })
        
        # Add conversation messages
        for msg in messages:
            ollama_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    message = data.get("message", {})
                    return {
                        "success": True,
                        "response": message.get("content", ""),
                        "role": message.get("role", "assistant"),
                        "model": model,
                        "task_type": task_type,
                        "done": data.get("done", True),
                        "total_duration": data.get("total_duration", 0),
                        "eval_count": data.get("eval_count", 0)
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}",
                        "model": model
                    }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Request timed out. The model may be loading or processing a complex request.",
                "model": model
            }
        except (aiohttp.ClientConnectorError, aiohttp.ClientConnectionError) as e:
            return {
                "success": False,
                "error": f"Cannot connect to Ollama at {self.base_url}: {e}. Start Ollama with 'ollama serve' and ensure port 11434 is reachable.",
                "model": model
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": model
            }
    
    # ───────────────────────────────────────────────────────────────────────────
    # AGENT AMIGOS MANAGED METHODS
    # ───────────────────────────────────────────────────────────────────────────
    
    async def amigos_delegate(
        self,
        task: str,
        context: Optional[str] = None,
        task_type: str = "default",
        prefer_fast: bool = False
    ) -> Dict[str, Any]:
        """
        Agent Amigos delegates a task to Ollama.
        This is the main method Amigos uses to route work to local LLMs.
        
        Args:
            task: The task/question to handle
            context: Additional context for the task
            task_type: Type of task for model selection
            prefer_fast: If True, prefer faster model over smarter
            
        Returns:
            Dict with delegated response
        """
        # AUTO-INTERNET: If task seems to require real-time info, perform a quick search first
        internet_keywords = [
            "news", "current", "latest", "today", "weather", "price", "stock", 
            "search", "who is", "what is the latest", "happening now", 
            "recent", "update on", "live", "score", "event"
        ]
        if any(kw in task.lower() for kw in internet_keywords) and "ollie" not in task.lower():
            try:
                from tools.web_tools import web
                from tools.agent_coordinator import agent_working
                
                import asyncio
                agent_working("ollie", f"Searching for: {task[:30]}...", progress=30)
                search_result = await asyncio.to_thread(web.web_search, task, max_results=3)
                
                if search_result.get("success"):
                    results = search_result.get("results", [])
                    search_context = "\n\n[Real-time Internet Search Results]\n"
                    for i, res in enumerate(results):
                        search_context += f"{i+1}. {res.get('title')}: {res.get('body') or res.get('snippet')}\n"
                    
                    context = (context or "") + search_context
                    agent_working("ollie", "Analyzing search results...", progress=60)
                    
                    # SELF-LEARNING: Learn from the search results immediately
                    for res in results[:2]:
                        fact = f"Current info on {task}: {res.get('title')} - {res.get('body') or res.get('snippet')}"
                        learn(fact, category="current_events")
            except Exception as e:
                print(f"[OLLIE] Auto-search failed: {e}")

        # Get shared memory context
        memory_context = shared_memory.build_context_for_agent(task, agent="ollie")
        
        # System Clock & Temporal Context
        now = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y at %I:%M:%S %p")
        
        # Build the system prompt with memory awareness
        system = f"""You are Ollie, the Assistant Agent to Agent Amigos.
Agent Amigos is your Master Agent and the Lead Orchestrator.
You report directly to Agent Amigos and only take tasks delegated by Amigos.
You share memory with Amigos - you can recall past conversations and learned facts.
You provide quick, accurate responses to help the user under the guidance of Agent Amigos.
Keep responses concise but helpful.

CURRENT TIME: {time_str} (Local System Time)

INTERNET ACCESS: While you run locally for privacy, you HAVE access to the internet through Agent Amigos' tools (the Internet Console). 
If a user asks for real-time information, news, or web data, you can and should use the information provided in your context, or suggest that Agent Amigos performs a search.
Do NOT claim you cannot access the internet. You are part of the Amigos ecosystem which is fully internet-capable.

IMPORTANT: You are running LOCALLY on the user's machine. All data stays private unless you explicitly use an internet tool via Amigos."""
        
        if prefer_fast:
            model = "llama3.2:latest"
        else:
            model = self.get_recommended_model(task_type)
        
        # Build prompt with memory context
        prompt_parts = []
        if memory_context:
            prompt_parts.append(f"[Shared Memory Context]\n{memory_context}")
        if context:
            prompt_parts.append(f"[Additional Context]\n{context}")
        prompt_parts.append(f"[Task]\n{task}")
        
        prompt = "\n\n".join(prompt_parts)
        
        # Remember this interaction
        remember_conversation("user", task, agent="ollie")
        
        result = await self.generate(
            prompt=prompt,
            model=model,
            task_type=task_type,
            system=system,
            temperature=0.7
        )
        
        if result.get("success"):
            response_text = result.get("response", "")
            
            # Remember Ollie's response
            remember_conversation("assistant", response_text, agent="ollie")
            
            # Try to extract and learn facts from the response
            self._extract_and_learn(task, response_text)
            
            # Log task completion
            log_task_completion(task, ["ollama_delegate"], True, response_text[:200])
            
            return {
                "success": True,
                "response": response_text,
                "delegated_to": "Ollie (Local LLM)",
                "model_used": model,
                "task_type": task_type,
                "memory_used": bool(memory_context)
            }
        else:
            log_task_completion(task, ["ollama_delegate"], False, result.get("error", ""))
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "delegated_to": "Ollie (Local LLM)",
                "model_used": model
            }
    
    def _extract_and_learn(self, query: str, response: str):
        """Extract potential facts from conversation and learn them."""
        # Simple fact extraction - look for definitive statements
        import re
        
        # Learn if it's a definition or explanation
        if any(phrase in query.lower() for phrase in ["what is", "define", "explain", "how does", "why is"]):
            # Extract first sentence of response as a fact
            first_sentence = response.split('.')[0].strip()
            if len(first_sentence) > 20 and len(first_sentence) < 300:
                topic = query.replace("what is", "").replace("define", "").replace("explain", "").strip()
                learn(f"{topic}: {first_sentence}", category="learned")
        
        # Learn user preferences if mentioned
        preference_patterns = [
            r"(?:I |my |user )(?:like|prefer|want|need|always|usually)\s+(.+?)(?:\.|$)",
        ]
        for pattern in preference_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if len(match) > 5:
                    learn(f"User preference: {match}", category="preference")
    
    async def enhance_content(
        self,
        content: str,
        enhancement_type: str = "improve",
        target_audience: str = "general"
    ) -> Dict[str, Any]:
        """
        Enhance content using Ollama.
        Used by Scrapey and other tools for AI enhancement.
        
        Args:
            content: Content to enhance
            enhancement_type: Type of enhancement (improve, summarize, expand, rephrase)
            target_audience: Target audience for the content
            
        Returns:
            Dict with enhanced content
        """
        prompts = {
            "improve": f"Improve this content for {target_audience} audience. Make it more engaging and clear:\n\n{content}",
            "summarize": f"Summarize this content concisely for {target_audience}:\n\n{content}",
            "expand": f"Expand on this content with more detail for {target_audience}:\n\n{content}",
            "rephrase": f"Rephrase this content in a fresh way for {target_audience}:\n\n{content}"
        }
        
        prompt = prompts.get(enhancement_type, prompts["improve"])
        
        return await self.generate(
            prompt=prompt,
            task_type="creative_writing",
            temperature=0.8
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

ollama_service = OllamaService()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def get_ollama_status() -> Dict[str, Any]:
    """Quick status check for Ollama."""
    return await ollama_service.check_status()

async def get_ollama_models() -> Dict[str, Any]:
    """Get list of available models."""
    return await ollama_service.list_models()

async def ollama_generate(
    prompt: str,
    model: Optional[str] = None,
    task_type: str = "default"
) -> Dict[str, Any]:
    """Generate response from Ollama."""
    return await ollama_service.generate(prompt, model, task_type)

async def ollama_chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None
) -> Dict[str, Any]:
    """Chat with Ollama."""
    return await ollama_service.chat(messages, model)

async def amigos_ask_ollie(
    task: str,
    context: Optional[str] = None,
    prefer_fast: bool = False
) -> Dict[str, Any]:
    """Agent Amigos asks Ollie (local LLM) for help."""
    return await ollama_service.amigos_delegate(task, context, prefer_fast=prefer_fast)
