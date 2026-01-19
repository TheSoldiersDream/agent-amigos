\"\"\"
Ollie Tools - Smart Open-Source AI Integration for Agent Amigos
==============================================================
Provides integration with smart open-source models via OpenRouter, Groq, or DeepSeek.
Ollie is the \"Smart Assistant\" within the Amigos ecosystem.

Supported Providers:
- OpenRouter (Primary) - Access to Llama 3.3, Qwen 2.5, etc.
- Groq (Fast) - Ultra-fast Llama 3.3 70B
- DeepSeek (Reasoning) - DeepSeek-V3/R1
- Ollama (Local Fallback) - If configured

All models share local memory with Amigos for self-learning.
\"\"\"

import aiohttp
import asyncio
import os
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit
from typing import Optional, Dict, Any, List
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
# OLLIE SERVICE CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class OllieService:
    \"\"\"
    Service for interacting with Smart Open-Source AI models.
    Agent Amigos uses this to delegate tasks to \"Ollie\".
    \"\"\"
    
    # Model recommendations for different task types (OpenRouter format)
    MODEL_ROUTING = {
        \"complex_reasoning\": \"meta-llama/llama-3.3-70b-instruct\",
        \"quick_response\": \"meta-llama/llama-3.1-8b-instruct\",
        \"creative_writing\": \"google/gemini-2.0-flash-001\",
        \"code_generation\": \"qwen/qwen-2.5-coder-32b-instruct\",
        \"summarization\": \"mistralai/mistral-large-2411\",
        \"translation\": \"meta-llama/llama-3.3-70b-instruct\",
        \"default\": \"meta-llama/llama-3.3-70b-instruct\"
    }
    
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=120)
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Determine provider
        self.provider = os.environ.get(\"OLLIE_PROVIDER\", \"openrouter\")
        self.api_key = os.environ.get(\"OLLIE_API_KEY\") or os.environ.get(\"OPENROUTER_API_KEY\") or os.environ.get(\"GROQ_API_KEY\")
        
        if self.provider == \"openrouter\":
            self.base_url = \"https://openrouter.ai/api/v1\"
        elif self.provider == \"groq\":
            self.base_url = \"https://api.groq.com/openai/v1\"
            self.MODEL_ROUTING[\"default\"] = \"llama-3.3-70b-versatile\"
        else:
            # Fallback to Ollama if explicitly requested or no key found
            self.base_url = os.environ.get(\"OLLAMA_API_BASE\", \"http://127.0.0.1:11434/v1\")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def get_recommended_model(self, task_type: str = \"default\") -> str:
        return self.MODEL_ROUTING.get(task_type, self.MODEL_ROUTING[\"default\"])

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        task_type: str = \"default\",
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        \"\"\"Generate a response using the configured provider.\"\"\"
        if model is None:
            model = self.get_recommended_model(task_type)
            
        messages = []
        if system:
            messages.append({\"role\": \"system\", \"content\": system})
        messages.append({\"role\": \"user\", \"content\": prompt})
        
        return await self.chat(messages, model=model, task_type=task_type, temperature=temperature, max_tokens=max_tokens)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        task_type: str = \"default\",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        \"\"\"Chat with the smart AI provider.\"\"\"
        if model is None:
            model = self.get_recommended_model(task_type)
            
        payload = {
            \"model\": model,
            \"messages\": messages,
            \"temperature\": temperature
        }
        if max_tokens:
            payload[\"max_tokens\"] = max_tokens
            
        headers = {
            \"Content-Type\": \"application/json\"
        }
        if self.api_key:
            headers[\"Authorization\"] = f\"Bearer {self.api_key}\"
            
        # OpenRouter specific headers
        if \"openrouter.ai\" in self.base_url:
            headers[\"HTTP-Referer\"] = \"https://github.com/darrellbuttigieg/AgentAmigos\"
            headers[\"X-Title\"] = \"Agent Amigos\"

        try:
            session = await self._get_session()
            async with session.post(
                f\"{self.base_url}/chat/completions\",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data[\"choices\"][0][\"message\"][\"content\"]
                    return {
                        \"success\": True,
                        \"response\": content,
                        \"model\": model,
                        \"provider\": self.provider
                    }
                else:
                    error_text = await response.text()
                    return {
                        \"success\": False,
                        \"error\": f\"HTTP {response.status}: {error_text}\",
                        \"model\": model
                    }
        except Exception as e:
            return {
                \"success\": False,
                \"error\": str(e),
                \"model\": model
            }

    async def amigos_delegate(
        self,
        task: str,
        context: Optional[str] = None,
        task_type: str = \"default\",
        prefer_fast: bool = False
    ) -> Dict[str, Any]:
        \"\"\"Agent Amigos delegates a task to Ollie (Smart AI).\"\"\"
        # AUTO-INTERNET: If task seems to require real-time info, perform a quick search first
        internet_keywords = [
            \"news\", \"current\", \"latest\", \"today\", \"weather\", \"price\", \"stock\", 
            \"search\", \"who is\", \"what is the latest\", \"happening now\", 
            \"recent\", \"update on\", \"live\", \"score\", \"event\"
        ]
        if any(kw in task.lower() for kw in internet_keywords) and \"ollie\" not in task.lower():
            try:
                from tools.web_tools import web
                from tools.agent_coordinator import agent_working
                
                agent_working(\"ollie\", f\"Searching for: {task[:30]}...\", progress=30)
                search_result = await asyncio.to_thread(web.web_search, task, max_results=3)
                
                if search_result.get(\"success\"):
                    results = search_result.get(\"results\", [])
                    search_context = \"\n\n[Real-time Internet Search Results]\n\"
                    for i, res in enumerate(results):
                        search_context += f\"{i+1}. {res.get('title')}: {res.get('body') or res.get('snippet')}\n\"
                    
                    context = (context or \"\") + search_context
                    agent_working(\"ollie\", \"Analyzing search results...\", progress=60)
                    
                    # SELF-LEARNING: Learn from the search results immediately
                    for res in results[:2]:
                        fact = f\"Current info on {task}: {res.get('title')} - {res.get('body') or res.get('snippet')}\"
                        learn(fact, category=\"current_events\")
            except Exception as e:
                print(f\"[OLLIE] Auto-search failed: {e}\")

        # Get shared memory context
        memory_context = shared_memory.build_context_for_agent(task, agent=\"ollie\")
        
        # System Clock & Temporal Context
        now = datetime.now()
        time_str = now.strftime(\"%A, %B %d, %Y at %I:%M:%S %p\")
        
        # Build the system prompt
        system = f\"\"\"You are Ollie, a highly intelligent AI assistant working with Agent Amigos.
You are powered by advanced open-source models (Llama 3.3, Qwen, Mistral).
You share memory with Amigos - you can recall past conversations and learned facts.
You provide quick, accurate, and smart responses to help the user.

CURRENT TIME: {time_str} (Local System Time)

INTERNET ACCESS: You HAVE access to the internet through Agent Amigos' tools. 
If a user asks for real-time information, use the provided context or suggest a search.

IMPORTANT: You are the \"Smart Brain\" of the team. Be insightful and helpful.\"\"\"
        
        model = self.get_recommended_model(task_type)
        if prefer_fast and self.provider == \"openrouter\":
            model = \"meta-llama/llama-3.1-8b-instruct\"
        
        prompt_parts = []
        if memory_context:
            prompt_parts.append(f\"[Shared Memory Context]\n{memory_context}\")
        if context:
            prompt_parts.append(f\"[Additional Context]\n{context}\")
        prompt_parts.append(f\"[Task]\n{task}\")
        
        prompt = \"\n\n\".join(prompt_parts)
        remember_conversation(\"user\", task, agent=\"ollie\")
        
        result = await self.chat(
            messages=[{\"role\": \"user\", \"content\": prompt}],
            model=model,
            task_type=task_type,
            temperature=0.7
        )
        
        if result.get(\"success\"):
            response_text = result.get(\"response\", \"\")
            remember_conversation(\"assistant\", response_text, agent=\"ollie\")
            self._extract_and_learn(task, response_text)
            log_task_completion(task, [\"ollie_delegate\"], True, response_text[:200])
            
            return {
                \"success\": True,
                \"response\": response_text,
                \"delegated_to\": \"Ollie (Smart AI)\",
                \"model_used\": model,
                \"provider\": self.provider,
                \"memory_used\": bool(memory_context)
            }
        else:
            log_task_completion(task, [\"ollie_delegate\"], False, result.get(\"error\", \"\"))
            return {
                \"success\": False,
                \"error\": result.get(\"error\", \"Unknown error\"),
                \"delegated_to\": \"Ollie (Smart AI)\",
                \"model_used\": model
            }

    def _extract_and_learn(self, query: str, response: str):
        \"\"\"Extract potential facts from conversation and learn them.\"\"\"
        import re
        if any(phrase in query.lower() for phrase in [\"what is\", \"define\", \"explain\", \"how does\", \"why is\"]):
            first_sentence = response.split('.')[0].strip()
            if 20 < len(first_sentence) < 300:
                topic = query.replace(\"what is\", \"\").replace(\"define\", \"\").replace(\"explain\", \"\").strip()
                learn(f\"{topic}: {first_sentence}\", category=\"learned\")
        
        preference_patterns = [r\"(?:I |my |user )(?:like|prefer|want|need|always|usually)\s+(.+?)(?:\.|$)\"]
        for pattern in preference_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if len(match) > 5:
                    learn(f\"User preference: {match}\", category=\"preference\")

    async def enhance_content(self, content: str, enhancement_type: str = \"improve\", target_audience: str = \"general\") -> Dict[str, Any]:
        prompts = {
            \"improve\": f\"Improve this content for {target_audience} audience. Make it more engaging and clear:\n\n{content}\",
            \"summarize\": f\"Summarize this content concisely for {target_audience}:\n\n{content}\",
            \"expand\": f\"Expand on this content with more detail for {target_audience}:\n\n{content}\",
            \"rephrase\": f\"Rephrase this content in a fresh way for {target_audience}:\n\n{content}\"
        }
        prompt = prompts.get(enhancement_type, prompts[\"improve\"])
        return await self.generate(prompt=prompt, task_type=\"creative_writing\", temperature=0.8)

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

ollie_service = OllieService()

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def get_ollie_status() -> Dict[str, Any]:
    return {\"success\": True, \"provider\": ollie_service.provider, \"status\": \"online\"}

async def ollie_generate(prompt: str, model: Optional[str] = None, task_type: str = \"default\") -> Dict[str, Any]:
    return await ollie_service.generate(prompt, model, task_type)

async def ollie_chat(messages: List[Dict[str, str]], model: Optional[str] = None) -> Dict[str, Any]:
    return await ollie_service.chat(messages, model)

async def amigos_ask_ollie(task: str, context: Optional[str] = None, task_type: str = \"default\", prefer_fast: bool = False) -> Dict[str, Any]:
    return await ollie_service.amigos_delegate(task, context, task_type, prefer_fast)
