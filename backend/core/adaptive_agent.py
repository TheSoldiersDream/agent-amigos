"""
Advanced Adaptive Agent with Multi-Model Collaboration
Implements reasoning chains, dynamic tool selection, and self-learning
"""

import json
import logging
import asyncio
import re
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
import time

# NOTE: This project is commonly launched with cwd=./backend.
# In that mode, `backend.core.*` imports will fail.
try:
    from core.model_manager import get_model_manager, ModelType
    from core.learning_engine import get_learning_engine
    from core.tool_registry import get_tool_registry
except Exception:  # pragma: no cover
    from backend.core.model_manager import get_model_manager, ModelType
    from backend.core.learning_engine import get_learning_engine
    from backend.core.tool_registry import get_tool_registry

logger = logging.getLogger(__name__)


class ReasoningStrategy(str, Enum):
    """Strategies for agent reasoning"""
    DIRECT = "direct"                    # Simple direct response
    CHAIN_OF_THOUGHT = "chain_of_thought"  # Step-by-step reasoning
    MULTI_MODEL = "multi_model"          # Consensus from multiple models
    ADAPTIVE = "adaptive"                # Choose strategy based on complexity


class ToolUsePattern(Enum):
    """Patterns for tool usage"""
    SEQUENTIAL = "sequential"            # Use tools one after another
    PARALLEL = "parallel"                # Use tools in parallel
    CONDITIONAL = "conditional"          # Use tools based on conditions
    HIERARCHICAL = "hierarchical"        # Use tools in hierarchy


class AdaptiveAgent:
    """
    Advanced agent with:
    - Multi-model collaboration
    - Reasoning chain execution
    - Dynamic tool selection
    - Learning from interactions
    - Self-correction
    """
    
    def __init__(self, 
                 agent_name: str,
                 agent_type: str = "general",
                 learning_enabled: bool = True):
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.learning_enabled = learning_enabled
        
        self.model_manager = get_model_manager()
        self.learning_engine = get_learning_engine()
        self.tool_registry = get_tool_registry()
        
        # Performance metrics
        self.metrics = {
            "total_interactions": 0,
            "successful_interactions": 0,
            "total_reasoning_chains": 0,
            "tools_used_count": {},
            "model_preferences": {},
            "avg_response_time": 0.0,
            "learned_patterns": []
        }
        
        logger.info(f"Initialized AdaptiveAgent: {agent_name} ({agent_type})")
    
    async def fix_transcript(self, transcript: str) -> str:
        """
        Fix common Speech-to-Text errors using LLM context
        """
        if not transcript or len(transcript) < 3:
            return transcript
            
        system_prompt = f"""
        You are the Voice Correction module for {self.agent_name}.
        The user is speaking to an AI assistant with tools like: Maps, Finance, Scraper, Canvas, Macros, and Files.
        Speech-to-Text often makes mistakes. Your job is to fix the transcript to what the user LIKELY said.
        
        Examples:
        - "open the chocolate" -> "open the canvas"
        - "search for apple stop price" -> "search for apple stock price"
        - "run the macro for link in" -> "run the macro for linkedin"
        - "scrape the web site" -> "scrape the website"
        
        ONLY return the corrected text. If it looks correct, return it as is.
        """
        
        try:
            # Use a fast model for this
            model = self.model_manager.get_best_model_for_task("fast", prefer_local=True)
            if not model:
                return transcript
                
            result = await self.model_manager.generate(
                model_id=model.model_id,
                prompt=f"Transcript to fix: '{transcript}'",
                system=system_prompt,
                temperature=0.1
            )
            
            if result.get("success"):
                corrected = result.get("response", "").strip().strip("'\"")
                if corrected.lower() != transcript.lower():
                    logger.info(f"[{self.agent_name}] Fixed transcript: '{transcript}' -> '{corrected}'")
                return corrected
        except Exception as e:
            logger.warning(f"Voice correction failed: {e}")
            
        return transcript

    async def execute_task(self,
                          task: str,
                          context: Optional[Dict[str, Any]] = None,
                          reasoning_strategy: ReasoningStrategy = ReasoningStrategy.ADAPTIVE,
                          prefer_local: bool = True) -> Dict[str, Any]:
        """
        Execute a task with adaptive reasoning and multi-model support
        """
        
        start_time = time.time()
        interaction_id = self._generate_id(task)
        
        try:
            # AUTO-INTERNET: If task seems to require real-time info, perform a quick search first
            internet_keywords = [
                "news", "current", "latest", "today", "weather", "price", "stock", 
                "search", "who is", "what is the latest", "happening now", 
                "recent", "update on", "live", "score", "event", "finance", "market"
            ]
            
            if any(kw in task.lower() for kw in internet_keywords):
                logger.info(f"[{self.agent_name}] Auto-internet triggered for task: {task[:50]}...")
                search_tool = self.tool_registry.get_tool("web_search")
                if search_tool:
                    search_func = search_tool[0]
                    try:
                        if asyncio.iscoroutinefunction(search_func):
                            search_result = await search_func(query=task)
                        else:
                            search_result = await asyncio.to_thread(search_func, query=task)
                            
                        if search_result.get("success"):
                            results = search_result.get("results", [])
                            search_context = "\n\n[Real-time Internet Search Results]\n"
                            for i, res in enumerate(results[:3]):
                                search_context += f"{i+1}. {res.get('title')}: {res.get('body') or res.get('snippet')}\n"
                            
                            if context is None:
                                context = {}
                            context["internet_search"] = search_context
                            logger.info(f"[{self.agent_name}] Added internet context to task")
                    except Exception as e:
                        logger.warning(f"Auto-internet search failed: {e}")

            # Step 1: Analyze task complexity and determine strategy
            if reasoning_strategy == ReasoningStrategy.ADAPTIVE:
                reasoning_strategy = self._determine_strategy(task, context)
            
            logger.info(f"[{self.agent_name}] Using strategy: {reasoning_strategy.value}")
            
            # Step 2: Get best models for this task
            models = self._select_models(
                task, 
                strategy=reasoning_strategy,
                prefer_local=prefer_local
            )
            
            # Step 3: Build reasoning chain
            reasoning_chain = []
            
            if reasoning_strategy == ReasoningStrategy.DIRECT:
                result = await self._execute_direct(task, context, models[0])
                reasoning_chain = [f"Direct execution with {models[0].name}"]
            
            elif reasoning_strategy == ReasoningStrategy.CHAIN_OF_THOUGHT:
                result, reasoning_chain = await self._execute_chain_of_thought(
                    task, context, models[0]
                )
            
            elif reasoning_strategy == ReasoningStrategy.MULTI_MODEL:
                result, reasoning_chain = await self._execute_multi_model(
                    task, context, models
                )
            
            else:  # ADAPTIVE already handled
                result = await self._execute_direct(task, context, models[0])
                reasoning_chain = [f"Adaptive execution with {models[0].name}"]
            
            # Step 4: Check for tool calls in the response
            response_text = result.get("response", "")
            tool_call = self._parse_tool_call(response_text)
            
            tools_used = []
            map_commands = []
            canvas_commands = []
            search_results = []
            todo_list = []
            progress = None

            if tool_call:
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args", {})
                
                if tool_name:
                    tools_used.append(tool_name)
                    tool_result = await self._execute_tool(tool_name, tool_args)
                    
                    # If tool was successful, we might want to generate a final response based on tool output
                    if tool_result.get("success"):
                        reasoning_chain.append(f"Executed tool: {tool_name}")
                        
                        # Extract special fields from tool result for frontend automation
                        res_data = tool_result.get("result", {})
                        if isinstance(res_data, dict):
                            if "map_commands" in res_data:
                                map_commands.extend(res_data["map_commands"])
                            if "canvas_commands" in res_data:
                                canvas_commands.extend(res_data["canvas_commands"])
                            if "search_results" in res_data:
                                search_results.extend(res_data["search_results"])
                            elif "results" in res_data and tool_name in ["web_search", "web_search_news"]:
                                search_results.extend(res_data["results"])
                            if "todo_list" in res_data:
                                todo_list.extend(res_data["todo_list"])
                            if "progress" in res_data:
                                progress = res_data["progress"]

                        final_prompt = f"Task: {task}\n\nTool '{tool_name}' result: {json.dumps(res_data)}\n\nProvide a final response to the user based on this result."
                        
                        final_result = await self.model_manager.generate(
                            model_id=models[0].model_id,
                            prompt=final_prompt,
                            system=self._get_system_prompt()
                        )
                        
                        if final_result.get("success"):
                            result["response"] = final_result.get("response")
                    else:
                        reasoning_chain.append(f"Tool execution failed: {tool_name} - {tool_result.get('error')}")
            
            # Step 5: Record interaction for learning
            duration_ms = (time.time() - start_time) * 1000
            success = result.get("success", True)
            
            if self.learning_enabled:
                self.learning_engine.store_interaction(
                    agent_name=self.agent_name,
                    task=task,
                    input_text=task,
                    output_text=result.get("response", ""),
                    success=success,
                    model_used=models[0].model_id,
                    duration_ms=duration_ms,
                    tools_used=tools_used,
                    reasoning_chain=reasoning_chain
                )
                
                # Learn from patterns
                self._learn_from_execution(task, result, tools_used, success)
            
            # Step 6: Update metrics
            self._update_metrics(models[0], tools_used, duration_ms, success)
            
            return {
                "interaction_id": interaction_id,
                "response": result.get("response", ""),
                "reasoning_chain": reasoning_chain,
                "tools_used": tools_used,
                "map_commands": map_commands,
                "canvas_commands": canvas_commands,
                "search_results": search_results,
                "todo_list": todo_list,
                "progress": progress,
                "model_used": models[0].model_id,
                "model_name": models[0].name,
                "success": success,
                "duration_ms": duration_ms,
                "strategy_used": reasoning_strategy.value,
                "metadata": {
                    "agent": self.agent_name,
                    "task_type": self.agent_type,
                    "models_considered": [m.model_id for m in models]
                }
            }
        
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {
                "interaction_id": interaction_id,
                "response": f"Error executing task: {str(e)}",
                "success": False,
                "error": str(e),
                "duration_ms": (time.time() - start_time) * 1000
            }
    
    def _determine_strategy(self,
                           task: str,
                           context: Optional[Dict[str, Any]]) -> ReasoningStrategy:
        """Determine best reasoning strategy based on task complexity"""
        
        complexity_indicators = {
            "complex": ["analyze", "evaluate", "compare", "solve", "explain"],
            "multi_step": ["step", "process", "procedure", "workflow"],
            "creative": ["generate", "create", "design", "imagine"],
            "factual": ["what", "where", "when", "who"]
        }
        
        task_lower = task.lower()
        task_length = len(task.split())
        
        # Simple heuristic scoring
        complexity_score = 0
        
        if task_length > 20:
            complexity_score += 2
        
        for category, keywords in complexity_indicators.items():
            if any(kw in task_lower for kw in keywords):
                complexity_score += 1
        
        # Select strategy based on score
        if complexity_score >= 3:
            return ReasoningStrategy.CHAIN_OF_THOUGHT
        elif complexity_score >= 2:
            return ReasoningStrategy.ADAPTIVE
        else:
            return ReasoningStrategy.DIRECT
    
    def _select_models(self,
                      task: str,
                      strategy: ReasoningStrategy,
                      prefer_local: bool = True) -> List:
        """Select appropriate models for the task"""
        
        # Map task to model type
        if "code" in task.lower():
            model_type = ModelType.CODING
        elif "reason" in task.lower() or "analyze" in task.lower():
            model_type = ModelType.REASONING
        elif "search" in task.lower() or "find" in task.lower():
            model_type = ModelType.SEARCH
        else:
            model_type = ModelType.GENERAL
        
        # Get best model for primary task
        primary_model = self.model_manager.get_best_model_for_task(
            model_type.value,
            prefer_local=prefer_local
        )
        
        models = [primary_model] if primary_model else []
        
        # For multi-model strategy, get additional models
        if strategy == ReasoningStrategy.MULTI_MODEL:
            all_models = self.model_manager.list_models(model_type=model_type)
            # Add secondary models (different providers for diversity)
            for model in all_models:
                if model not in models and len(models) < 3:
                    models.append(model)
        
        return models or [self.model_manager.get_best_model_for_task("general")]
    
    async def _execute_direct(
        self,
        task: str,
        context: Optional[Dict[str, Any]],
        model,
    ) -> Dict[str, Any]:
        """Direct execution without complex reasoning"""
        
        logger.info(f"Direct execution using {model.name}")
        
        system_prompt = f"You are {self.agent_name}, an expert AI assistant. Task type: {self.agent_type}."
        if context:
            system_prompt += f" Context: {json.dumps(context)}"
            
        result = await self.model_manager.generate(
            model_id=model.model_id,
            prompt=task,
            system=system_prompt
        )
        
        return result
    
    async def _execute_chain_of_thought(
        self,
        task: str,
        context: Optional[Dict[str, Any]],
        model,
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Execute with chain-of-thought reasoning"""
        
        logger.info(f"Chain-of-thought execution using {model.name}")
        
        # Step 1: Generate reasoning steps
        reasoning_prompt = f"Task: {task}\n\nBreak this task down into 3-5 logical steps for execution. Output ONLY the steps as a numbered list."
        
        reasoning_result = await self.model_manager.generate(
            model_id=model.model_id,
            prompt=reasoning_prompt,
            system="You are a strategic planner. Break down tasks into logical steps."
        )
        
        if not reasoning_result.get("success"):
            return reasoning_result, ["Failed to generate reasoning steps"]
            
        reasoning_chain = reasoning_result.get("response", "").strip().split("\n")
        reasoning_chain = [s.strip() for s in reasoning_chain if s.strip()]
        
        # Step 2: Execute task with reasoning
        execution_prompt = f"Task: {task}\n\nReasoning Steps:\n" + "\n".join(reasoning_chain) + "\n\nExecute the task based on these steps."
        
        result = await self.model_manager.generate(
            model_id=model.model_id,
            prompt=execution_prompt,
            system=f"You are {self.agent_name}. Execute the task following the reasoning chain."
        )
        
        return result, reasoning_chain
    
    async def _execute_multi_model(
        self,
        task: str,
        context: Optional[Dict[str, Any]],
        models: List,
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Execute with multiple models and consensus"""
        
        logger.info(f"Multi-model execution with {len(models)} models")
        
        tasks = []
        for model in models:
            tasks.append(self.model_manager.generate(
                model_id=model.model_id,
                prompt=task,
                system=f"You are {self.agent_name}. Provide your best response for the task."
            ))
            
        responses = await asyncio.gather(*tasks)
        
        reasoning_chain = [f"Collected responses from {len(models)} models:"]
        valid_responses = []
        
        for i, resp in enumerate(responses):
            m_name = models[i].name
            if resp.get("success"):
                reasoning_chain.append(f"- {m_name}: Success")
                valid_responses.append(f"Model {m_name} response: {resp.get('response')}")
            else:
                reasoning_chain.append(f"- {m_name}: Failed ({resp.get('error')})")
                
        if not valid_responses:
            return {"success": False, "error": "All models failed"}, reasoning_chain
            
        # Step 3: Synthesize consensus
        synthesis_prompt = "Task: " + task + "\n\nHere are responses from different models:\n\n" + "\n\n".join(valid_responses) + "\n\nSynthesize the best final response based on these inputs."
        
        # Use the first model for synthesis
        synthesis_result = await self.model_manager.generate(
            model_id=models[0].model_id,
            prompt=synthesis_prompt,
            system="You are a consensus engine. Synthesize multiple model outputs into a single high-quality response."
        )
        
        reasoning_chain.append("Synthesized final response from all model inputs.")
        
        return synthesis_result, reasoning_chain
    
    def _extract_tools_used(self, result: Dict[str, Any]) -> List[str]:
        """Extract which tools were used in execution"""
        
        # Simple extraction - in real implementation, parse from LLM output
        tools = []
        
        if "tools_used" in result:
            tools = result["tools_used"]
        elif "reasoning_steps" in result:
            # Infer from reasoning steps
            steps = str(result["reasoning_steps"]).lower()
            if "search" in steps:
                tools.append("search")
            if "file" in steps:
                tools.append("file_system")
            if "browser" in steps:
                tools.append("browser")
        
        return tools
    
    def _learn_from_execution(self,
                             task: str,
                             result: Dict[str, Any],
                             tools_used: List[str],
                             success: bool):
        """Learn from execution results"""
        
        # Store learned patterns
        if success and tools_used:
            pattern = {
                "task_type": self._infer_task_type(task),
                "tools": tools_used,
                "success": success,
                "timestamp": datetime.now().isoformat()
            }
            self.metrics["learned_patterns"].append(pattern)
            
            # Keep only recent patterns
            if len(self.metrics["learned_patterns"]) > 100:
                self.metrics["learned_patterns"] = self.metrics["learned_patterns"][-100:]
    
    def _infer_task_type(self, task: str) -> str:
        """Infer task type from task description"""
        
        task_lower = task.lower()
        
        if "code" in task_lower or "programming" in task_lower:
            return "coding"
        elif "search" in task_lower or "find" in task_lower:
            return "search"
        elif "analyze" in task_lower or "evaluate" in task_lower:
            return "analysis"
        elif "file" in task_lower:
            return "file_management"
        elif "browser" in task_lower or "web" in task_lower:
            return "web_browsing"
        else:
            return "general"
    
    def _extract_tools_used_from_steps(self, steps: List[str]) -> List[str]:
        """Extract tools from reasoning steps"""
        
        tools = []
        steps_str = " ".join(steps).lower()
        
        tool_keywords = {
            "search": ["search", "query", "find", "lookup"],
            "file": ["file", "read", "write", "save", "load"],
            "browser": ["browser", "web", "url", "navigate", "visit"],
            "terminal": ["terminal", "command", "execute", "run"],
            "code": ["code", "python", "javascript", "compile"]
        }
        
        for tool, keywords in tool_keywords.items():
            if any(kw in steps_str for kw in keywords):
                tools.append(tool)
        
        return list(set(tools))  # Remove duplicates
    
    def _update_metrics(self,
                       model,
                       tools_used: List[str],
                       duration_ms: float,
                       success: bool):
        """Update agent metrics"""
        
        self.metrics["total_interactions"] += 1
        
        if success:
            self.metrics["successful_interactions"] += 1
        
        # Update average response time
        old_avg = self.metrics["avg_response_time"]
        n = self.metrics["total_interactions"]
        self.metrics["avg_response_time"] = (
            (old_avg * (n - 1) + duration_ms) / n
        )
        
        # Track model preferences
        if model.model_id not in self.metrics["model_preferences"]:
            self.metrics["model_preferences"][model.model_id] = 0
        self.metrics["model_preferences"][model.model_id] += 1
        
        # Track tool usage
        for tool in tools_used:
            if tool not in self.metrics["tools_used_count"]:
                self.metrics["tools_used_count"][tool] = 0
            self.metrics["tools_used_count"][tool] += 1
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status and capabilities"""
        
        skills = self.learning_engine.get_agent_skills(self.agent_name)
        success_patterns = self.learning_engine.get_success_patterns(self.agent_name)
        
        return {
            "name": self.agent_name,
            "type": self.agent_type,
            "learning_enabled": self.learning_enabled,
            "metrics": self.metrics,
            "skills": skills,
            "recent_successes": success_patterns[:5],
            "models_available": len(self.model_manager.models),
            "total_interactions": self.metrics["total_interactions"],
            "success_rate": (
                self.metrics["successful_interactions"] / self.metrics["total_interactions"]
                if self.metrics["total_interactions"] > 0 else 0
            )
        }
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID"""
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_system_prompt(self) -> str:
        """Generate system prompt with tool descriptions"""
        
        tools_metadata = self.tool_registry.get_tools_metadata()
        
        tools_str = ""
        for name, meta in tools_metadata.items():
            tools_str += f"- {name}: {meta['description']}\n"
            
        system_prompt = f"""You are {self.agent_name}, an advanced AI assistant part of the Agent Amigos ecosystem.
You have access to a wide range of tools to interact with the system, the web, and various consoles (Finance, Internet, Maps, Canvas).

AVAILABLE TOOLS:
{tools_str}

TOOL USE FORMAT:
If you need to use a tool, you MUST output a JSON block. Do NOT just describe what you will do.
Example:
```json
{{
  "tool": "tool_name",
  "args": {{
    "arg1": "value1"
  }}
}}
```

CRITICAL INSTRUCTIONS:
1. If the user asks for a location, route, or map, you MUST use the 'map_control' tool.
2. If the user asks for real-time information, you MUST use 'web_search'.
3. If the user asks to draw or design, you MUST use 'canvas_design' or related canvas tools.
4. ALWAYS output the JSON block to trigger the automation. If you don't output the JSON, nothing will happen in the UI.

INTERNET & CONSOLES:
- You HAVE access to the internet. Use 'web_search' or 'fetch_url' for real-time info.
- You can control the Map Console using 'map_control'.
- You can design on Canvas using 'canvas_design'.
- You can access Finance data via web search or specific finance tools if available.

Always think step-by-step. If a task is complex, use the CHAIN_OF_THOUGHT strategy.
"""
        return system_prompt

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool from the registry"""
        
        tool_info = self.tool_registry.get_tool(tool_name)
        if not tool_info:
            return {"success": False, "error": f"Tool {tool_name} not found"}
            
        func, requires_approval, desc = tool_info
        
        try:
            logger.info(f"Agent {self.agent_name} executing tool: {tool_name} with args: {args}")
            
            # In a real environment, we would check for approval here if requires_approval is True
            # For now, we'll assume the agent has permission or the UI handles it
            
            if asyncio.iscoroutinefunction(func):
                result = await func(**args)
            else:
                # Run synchronous tools in a thread to avoid blocking the event loop
                result = await asyncio.to_thread(func, **args)
                
            return {"success": True, "result": result, "tool": tool_name}
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}, error: {e}")
            return {"success": False, "error": str(e), "tool": tool_name}

    def _parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse tool call from LLM response"""
        
        # Look for JSON block
        pattern = r'```json\s*\n?({.*?})\s*\n?```'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
                
        # Fallback to simple brace search
        pattern2 = r'({.*"tool":\s*"[^"]+".*})'
        match2 = re.search(pattern2, text, re.DOTALL)
        if match2:
            try:
                return json.loads(match2.group(1))
            except:
                pass
                
        return None


# Global agent registry
_agents: Dict[str, AdaptiveAgent] = {}


def get_or_create_agent(agent_name: str, 
                       agent_type: str = "general",
                       learning_enabled: bool = True) -> AdaptiveAgent:
    """Get or create an agent"""
    
    if agent_name not in _agents:
        _agents[agent_name] = AdaptiveAgent(
            agent_name,
            agent_type,
            learning_enabled
        )
    
    return _agents[agent_name]


def get_agent_registry() -> Dict[str, AdaptiveAgent]:
    """Get all agents"""
    return _agents.copy()
