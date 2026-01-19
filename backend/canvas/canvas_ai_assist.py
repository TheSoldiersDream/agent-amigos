"""
🧠🎨 Canvas AI Augmentation Agent

Enhances the Canvas with AI-assisted capabilities:
- AI-assisted discussion
- AI-assisted drawing
- AI-assisted planning and design
- Visual + conversational interaction

CRITICAL: This module ONLY augments Canvas. It does NOT modify or replace
any existing Agent Amigos tools, permissions, routing, or UI.

Mode: OBSERVER–ASSISTANT
- Listens to Canvas events
- Responds when user addresses the agent or requests help
- Never blocks or intercepts user actions
- Always adds content on new layers with clear AI labels
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from tools.agent_coordinator import (
    agent_thinking,
    agent_working,
    agent_idle,
    coordinator
)
from tools.media_tools import media

from .canvas_controller import canvas_controller, CommandType

logger = logging.getLogger(__name__)

SHARED_SKILLS = """
You are Agent Amigos, a VISUAL THINKING & TECHNICAL DESIGN SPECIALIST.

CORE CAPABILITIES:
• Technical Diagramming (Flowcharts, Architecture, Systems)
• Floor Planning & Spatial Layouts
• Mind Mapping & Brainstorming Visualization
• Educational Illustrations & Explanations
• Process Mapping & Workflow Design

KNOWLEDGE DOMAINS:
• Engineering (mechanical, electrical, civil, software)
• Science (physics, chemistry, biology, mathematics)
• Technology (computers, programming, AI, networking)
• Business (marketing, finance, management)
• Architecture & Design Principles

When asked to draw, plan, or brainstorm, use this knowledge to create accurate, high-quality, and visually structured content.
Focus on clarity, precision, and logical organization in your visual outputs.
"""

class SimpleChatMessage:
    """Simple compatible class for ChatMessage to avoid circular imports"""
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

class CanvasAIAssist:
    """
    AI Augmentation layer for Canvas.
    
    Operates in observer-assistant mode:
    - Observes user actions (text, drawings, shapes)
    - Assists when requested or when user pauses
    - Never takes control from user
    - Always labels AI content clearly
    """
    
    def __init__(self):
        self.enabled = True
        self.conversation_history = []
        self.user_context = {
            "last_action": None,
            "last_text": None,
            "last_drawing": None,
            "session_start": datetime.now()
        }
        self.ai_layer_id = "ai_assist_layer"
        self.corner_note_shown = False
        self.agent_engine = None
        
        # Register as listener for Canvas events
        canvas_controller.add_listener(self._on_canvas_event)
        
        logger.info("🧠 Canvas AI Assist initialized (observer mode)")

    def set_agent_engine(self, agent_engine):
        """
        Inject the main AgentEngine instance to enable real LLM capabilities.
        """
        self.agent_engine = agent_engine
        logger.info("🧠 Canvas AI Assist connected to Agent Engine")

    def _process_request(self, prompt: str, system_instruction: str = None) -> str:
        """
        Process a request using the full Agent Engine (enabling tool usage).
        """
        if not self.agent_engine:
            return "Agent Engine not connected."
            
        try:
            messages = []
            # Add context from conversation history if available? 
            # For now, keep it focused on the immediate task to avoid context window issues,
            # but we should ideally pass some history.
            
            if system_instruction:
                messages.append(SimpleChatMessage(role="system", content=system_instruction))
            
            messages.append(SimpleChatMessage(role="user", content=prompt))
            
            # Use process() to allow tool execution (read files, search web, etc.)
            # require_approval=False allows autonomous tool usage
            response = self.agent_engine.process(messages, require_approval=False)
            
            return response.content
        except Exception as e:
            logger.error(f"Agent Engine process error: {e}")
            return f"Error processing request: {e}"
    
    def _on_canvas_event(self, command):
        """
        Observes Canvas events without blocking them.
        Updates context for future AI assistance.
        """
        if not self.enabled:
            return
        
        try:
            # Update context based on command type
            cmd_type = command.command_type
            params = command.parameters
            
            if cmd_type == CommandType.DRAW_TEXT:
                self.user_context["last_text"] = params.get("text", "")
                self.user_context["last_action"] = "text"
                
                # Check if user is addressing the AI
                text = params.get("text", "").lower()
                if any(trigger in text for trigger in ["agent", "ai", "help", "explain", "show me"]):
                    self._trigger_assistance(text, params)
            
            elif cmd_type in [CommandType.DRAW_LINE, CommandType.DRAW_RECTANGLE, 
                             CommandType.DRAW_ELLIPSE, CommandType.DRAW_ARROW]:
                self.user_context["last_drawing"] = {
                    "type": cmd_type.value,
                    "params": params
                }
                self.user_context["last_action"] = "drawing"
            
        except Exception as e:
            logger.debug(f"Canvas AI Assist event handler error: {e}")
    
    def _trigger_assistance(self, user_text: str, context: Dict[str, Any]):
        """
        Triggered when user appears to be requesting AI assistance.
        """
        agent_thinking("canvas", f"Analyzing: {user_text[:50]}...")
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_text,
            "timestamp": datetime.now().isoformat(),
            "context": context
        })
        
        logger.info(f"🧠 AI Assist triggered by: {user_text[:50]}")
    
    def show_startup_note(self):
        """
        Shows a small corner note on first activation.
        Non-intrusive, just indicates AI assist is ready.
        """
        if self.corner_note_shown:
            return None
        
        self.corner_note_shown = True
        
        return canvas_controller.draw_text(
            text="🧠 Canvas AI Assist ready — ask me or draw.",
            x=20,
            y=20,
            font_size=12,
            color="#a78bfa",
            font_family="Arial",
            layer_id=self.ai_layer_id
        )
    
    def discuss(self, topic: str, position: Optional[Dict[str, int]] = None, snapshot: Optional[str] = None, context_objects: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        AI-assisted discussion: Explain ideas written or drawn by the user.
        
        Args:
            topic: The subject to discuss
            position: Where to place the discussion on the board
            snapshot: Optional base64 image of the canvas
            context_objects: Optional list of objects currently on the canvas
        
        Returns:
            Dict with command IDs of created visual elements
        """
        agent_thinking("canvas", f"Discussing: {topic[:50]}...")
        
        if position is None:
            position = {"x": 100, "y": 100}
        
        # Generate insight using LLM if available
        insight = f"I've started a discussion about {topic} on the board."
        discussion_points = [f"Let's explore {topic} together."]
        
        if self.agent_engine:
            try:
                system_prompt = f"""{SHARED_SKILLS}
                You are a helpful AI assistant on a digital whiteboard. Provide 3 brief, insightful key points about the user's topic. Keep each point under 10 words. Format as a simple list. You can use tools to research the topic if needed."""
                
                context_str = ""
                if context_objects:
                    # Summarize context objects to save tokens
                    obj_summary = []
                    for obj in context_objects[:50]: # Limit to 50 objects
                        otype = obj.get('type', 'object')
                        ox = obj.get('x', 0)
                        oy = obj.get('y', 0)
                        otext = obj.get('text', '')
                        desc = f"{otype}"
                        if otext:
                            desc += f"('{otext}')"
                        desc += f" at ({ox}, {oy})"
                        obj_summary.append(desc)
                    context_str = f"\n\nContext (Visible Objects on Canvas):\n" + "\n".join(obj_summary)

                prompt = f"Topic: {topic}{context_str}"
                
                response = self._process_request(prompt, system_prompt)
                insight = response
                
                # Split into points
                lines = [line.strip() for line in response.split('\n') if line.strip()]
                # Filter out lines that are likely not points (e.g. "Here are...")
                discussion_points = [l for l in lines if len(l) > 3 and not l.lower().startswith("here") and not l.lower().startswith("sure") and not l.lower().startswith("i have")]
                if not discussion_points:
                    discussion_points = [response]
            except Exception as e:
                logger.error(f"LLM error in discuss: {e}")
        
        # Create a discussion box
        command_ids = []
        
        # Title
        cmd_id = canvas_controller.draw_text(
            text=f"💭 Discussion: {topic[:30]}",
            x=position["x"],
            y=position["y"],
            font_size=14,
            color="#c4b5fd",
            layer_id=self.ai_layer_id
        )
        command_ids.append(cmd_id)
        
        # AI label
        cmd_id = canvas_controller.draw_text(
            text="(Agent Amigos AI Assist)",
            x=position["x"],
            y=position["y"] + 20,
            font_size=10,
            color="#8b5cf6",
            layer_id=self.ai_layer_id
        )
        command_ids.append(cmd_id)
        
        # Add the content
        y_offset = position["y"] + 45
        for point in discussion_points[:4]: # Limit to 4 points
             # Clean up point text
            point_text = point.replace("*", "").replace("- ", "").strip()
            if len(point_text) > 50:
                point_text = point_text[:47] + "..."
                
            cmd_id = canvas_controller.draw_text(
                text=f"• {point_text}",
                x=position["x"],
                y=y_offset,
                font_size=12,
                color="#e2e8f0",
                layer_id=self.ai_layer_id
            )
            command_ids.append(cmd_id)
            y_offset += 20
        
        agent_idle("canvas")
        
        # Get all commands and filter to only the ones we just created
        all_commands = canvas_controller.get_pending_commands()
        command_objects = [cmd for cmd in all_commands if cmd.get("id") in command_ids]
        
        return {
            "success": True,
            "command_ids": command_ids,
            "commands": command_objects,
            "mode": "discuss",
            "conversational_response": insight
        }
    
    def _extract_json(self, text: str) -> Optional[Any]:
        """
        Robustly extract and parse JSON from LLM response.
        Handles markdown blocks, plain text, and common errors.
        """
        import re
        import json
        
        try:
            # 1. Try to find JSON in markdown code blocks
            match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
            if match:
                return json.loads(match.group(1))
                
            # 2. Try to find a JSON array or object directly
            match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', text)
            if match:
                return json.loads(match.group(1))
                
            # 3. Try cleaning the text
            clean_text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
            
        except Exception as e:
            logger.warning(f"JSON extraction failed: {e}")
            return None

    def draw(self, description: str, position: Optional[Dict[str, int]] = None, snapshot: Optional[str] = None, context_objects: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        AI-assisted drawing: Add sketches, arrows, highlights, callouts.
        Extends user drawings instead of replacing them.
        
        Args:
            description: What to draw
            position: Starting position
            snapshot: Optional base64 image of the canvas
            context_objects: Optional list of objects currently on the canvas
        
        Returns:
            Dict with command IDs of created elements
        """
        agent_working("canvas", f"Drawing: {description[:50]}...")
        
        if position is None:
            position = {"x": 200, "y": 200}
        
        command_ids = []
        
        # Add AI annotation marker
        cmd_id = canvas_controller.draw_text(
            text="🎨 AI Sketch",
            x=position["x"] - 10,
            y=position["y"] - 15,
            font_size=10,
            color="#a78bfa",
            layer_id=self.ai_layer_id
        )
        command_ids.append(cmd_id)
        
        # Use LLM to generate drawing commands if available
        llm_success = False
        if self.agent_engine:
            try:
                system_prompt = f"""{SHARED_SKILLS}
                You are a technical drawing assistant. 
                1. You can use tools to research what needs to be drawn (e.g. read files, search web).
                2. Convert the user's request into a JSON list of simple shapes to draw on a whiteboard.
                3. Return ONLY valid JSON in a markdown code block.
                
                Available shapes:
                - rectangle (x, y, width, height, color, text)
                - ellipse (cx, cy, rx, ry, color, text)
                - diamond (cx, cy, width, height, color, text)
                - line (x1, y1, x2, y2, color)
                - arrow (x1, y1, x2, y2, color)
                - text (x, y, text, color, font_size)
                
                Coordinate System:
                - x increases to the right
                - y increases downwards
                - Keep shapes close to the starting position
                """
                
                context_str = ""
                if context_objects:
                    # Summarize context objects to save tokens
                    obj_summary = []
                    for obj in context_objects[:50]: # Limit to 50 objects
                        otype = obj.get('type', 'object')
                        ox = obj.get('x', 0)
                        oy = obj.get('y', 0)
                        otext = obj.get('text', '')
                        desc = f"{otype}"
                        if otext:
                            desc += f"('{otext}')"
                        desc += f" at ({ox}, {oy})"
                        obj_summary.append(desc)
                    context_str = f"\n\nContext (Visible Objects on Canvas):\n" + "\n".join(obj_summary)

                prompt = f"""
                User Request: "{description}"
                Starting Position: x={position['x']}, y={position['y']}{context_str}
                
                Example Output:
                ```json
                [
                    {{"type": "rectangle", "x": 200, "y": 200, "width": 100, "height": 50, "color": "#8b5cf6", "text": "Process"}},
                    {{"type": "arrow", "x1": 300, "y1": 225, "x2": 350, "y2": 225, "color": "#8b5cf6"}},
                    {{"type": "text", "x": 210, "y": 220, "text": "Hello", "color": "#ffffff", "font_size": 12}}
                ]
                ```
                """
                
                response = self._process_request(prompt, system_prompt)
                shapes = self._extract_json(response)
                
                if shapes:
                    for shape in shapes:
                        sid = None
                        stype = shape.get("type")
                        color = shape.get("color", "#8b5cf6")
                        
                        if stype == "rectangle":
                            sid = canvas_controller.draw_rectangle(
                                x=shape.get("x"), y=shape.get("y"), 
                                width=shape.get("width"), height=shape.get("height"),
                                stroke_color=color, fill_color="rgba(139, 92, 246, 0.1)",
                                layer_id=self.ai_layer_id
                            )
                            if shape.get("text"):
                                canvas_controller.draw_text(
                                    text=shape.get("text"), 
                                    x=shape.get("x") + 10, 
                                    y=shape.get("y") + shape.get("height")/2 - 5,
                                    color="#e2e8f0", font_size=12,
                                    layer_id=self.ai_layer_id
                                )
                        elif stype == "ellipse":
                            sid = canvas_controller.draw_ellipse(
                                cx=shape.get("cx"), cy=shape.get("cy"),
                                rx=shape.get("rx"), ry=shape.get("ry"),
                                stroke_color=color, fill_color="rgba(139, 92, 246, 0.1)",
                                layer_id=self.ai_layer_id
                            )
                            if shape.get("text"):
                                canvas_controller.draw_text(
                                    text=shape.get("text"), 
                                    x=shape.get("cx") - 20, 
                                    y=shape.get("cy") - 5,
                                    color="#e2e8f0", font_size=12,
                                    layer_id=self.ai_layer_id
                                )
                        elif stype == "diamond":
                            # Draw diamond using 4 lines
                            cx, cy = shape.get("cx"), shape.get("cy")
                            w, h = shape.get("width"), shape.get("height")
                            hw, hh = w/2, h/2
                            
                            # Top to Right
                            canvas_controller.draw_line(x1=cx, y1=cy-hh, x2=cx+hw, y2=cy, color=color, layer_id=self.ai_layer_id)
                            # Right to Bottom
                            canvas_controller.draw_line(x1=cx+hw, y1=cy, x2=cx, y2=cy+hh, color=color, layer_id=self.ai_layer_id)
                            # Bottom to Left
                            canvas_controller.draw_line(x1=cx, y1=cy+hh, x2=cx-hw, y2=cy, color=color, layer_id=self.ai_layer_id)
                            # Left to Top
                            sid = canvas_controller.draw_line(x1=cx-hw, y1=cy, x2=cx, y2=cy-hh, color=color, layer_id=self.ai_layer_id)
                            
                            if shape.get("text"):
                                canvas_controller.draw_text(
                                    text=shape.get("text"), 
                                    x=cx - 20, 
                                    y=cy - 5,
                                    color="#e2e8f0", font_size=12,
                                    layer_id=self.ai_layer_id
                                )

                        elif stype == "line":
                            sid = canvas_controller.draw_line(
                                x1=shape.get("x1"), y1=shape.get("y1"),
                                x2=shape.get("x2"), y2=shape.get("y2"),
                                color=color, layer_id=self.ai_layer_id
                            )
                        elif stype == "arrow":
                            sid = canvas_controller.draw_arrow(
                                x1=shape.get("x1"), y1=shape.get("y1"),
                                x2=shape.get("x2"), y2=shape.get("y2"),
                                color=color, layer_id=self.ai_layer_id
                            )
                        elif stype == "text":
                            sid = canvas_controller.draw_text(
                                text=shape.get("text"), x=shape.get("x"), y=shape.get("y"),
                                color=color, font_size=shape.get("font_size", 12),
                                layer_id=self.ai_layer_id
                            )
                        
                        if sid:
                            command_ids.append(sid)
                    
                    llm_success = True
                
            except Exception as e:
                logger.error(f"LLM drawing error: {e}")
        
        if not llm_success:
            # Fallback logic
            desc_lower = description.lower()
            
            if "arrow" in desc_lower:
                cmd_id = canvas_controller.draw_arrow(
                    x1=position["x"],
                    y1=position["y"],
                    x2=position["x"] + 100,
                    y2=position["y"],
                    color="#8b5cf6",
                    width=2,
                    layer_id=self.ai_layer_id
                )
                command_ids.append(cmd_id)
            
            elif "box" in desc_lower or "rectangle" in desc_lower:
                cmd_id = canvas_controller.draw_rectangle(
                    x=position["x"],
                    y=position["y"],
                    width=100,
                    height=60,
                    stroke_color="#8b5cf6",
                    fill_color="rgba(139, 92, 246, 0.1)",
                    stroke_width=2,
                    layer_id=self.ai_layer_id
                )
                command_ids.append(cmd_id)
            
            elif "circle" in desc_lower:
                cmd_id = canvas_controller.draw_ellipse(
                    cx=position["x"] + 40,
                    cy=position["y"] + 40,
                    rx=40,
                    ry=40,
                    stroke_color="#8b5cf6",
                    fill_color="rgba(139, 92, 246, 0.1)",
                    stroke_width=2,
                    layer_id=self.ai_layer_id
                )
                command_ids.append(cmd_id)
        
        agent_idle("canvas")
        
        # Get all commands and filter to only the ones we just created
        all_commands = canvas_controller.get_pending_commands()
        command_objects = [cmd for cmd in all_commands if cmd.get("id") in command_ids]
        
        return {
            "success": True,
            "command_ids": command_ids,
            "commands": command_objects,
            "mode": "draw",
            "description": description,
            "conversational_response": f"I've drawn a sketch of {description} for you."
        }
    
    def plan(self, goal: str, steps: Optional[List[str]] = None, position: Optional[Dict[str, int]] = None, snapshot: Optional[str] = None, context_objects: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        AI-assisted planning: Convert rough ideas into structured visual plans.
        Shows steps, phases, dependencies.
        
        Args:
            goal: The planning objective
            steps: Optional list of steps
            position: Where to place the plan
        
        Returns:
            Dict with command IDs and full commands
        """
        agent_working("canvas", f"Planning: {goal[:50]}...")
        
        if position is None:
            position = {"x": 100, "y": 100}
        
        # Generate steps using LLM if not provided
        if steps is None or not steps:
            steps = ["Step 1", "Step 2", "Step 3"] # Default fallback
            
            if self.agent_engine:
                try:
                    system_prompt = f"""{SHARED_SKILLS}
                    You are a strategic planning assistant. 
                    1. Analyze the user's goal.
                    2. Break it down into 3-6 logical, actionable steps.
                    3. Ensure steps are sequential and clear.
                    4. Return ONLY the steps as a list, one per line.
                    """
                    prompt = f"Goal: {goal}"
                    
                    response = self._process_request(prompt, system_prompt)
                    
                    # Parse response
                    generated_steps = [line.strip().lstrip("1234567890.- ") for line in response.split('\n') if line.strip()]
                    if generated_steps:
                        steps = generated_steps[:6] # Limit to 6 steps
                except Exception as e:
                    logger.error(f"LLM planning error: {e}")
        
        command_ids = []
        y_offset = position["y"]
        
        # Title
        cmd_id = canvas_controller.draw_text(
            text=f"📋 Plan: {goal[:40]}",
            x=position["x"],
            y=y_offset,
            font_size=16,
            color="#c4b5fd",
            layer_id=self.ai_layer_id
        )
        command_ids.append(cmd_id)
        y_offset += 30
        
        # AI label
        cmd_id = canvas_controller.draw_text(
            text="(Agent Amigos AI Assist)",
            x=position["x"],
            y=y_offset,
            font_size=10,
            color="#8b5cf6",
            layer_id=self.ai_layer_id
        )
        command_ids.append(cmd_id)
        y_offset += 30
        
        # Steps
        for i, step in enumerate(steps[:5], 1):  # Limit to 5 steps
            # Step box
            cmd_id = canvas_controller.draw_rectangle(
                x=position["x"],
                y=y_offset,
                width=200,
                height=40,
                stroke_color="#8b5cf6",
                fill_color="rgba(139, 92, 246, 0.1)",
                stroke_width=2,
                layer_id=self.ai_layer_id
            )
            command_ids.append(cmd_id)
            
            # Step text
            cmd_id = canvas_controller.draw_text(
                text=f"{i}. {step[:30]}",
                x=position["x"] + 10,
                y=y_offset + 15,
                font_size=12,
                color="#e2e8f0",
                layer_id=self.ai_layer_id
            )
            command_ids.append(cmd_id)
            
            # Arrow to next step
            if i < len(steps) and i < 5:
                cmd_id = canvas_controller.draw_arrow(
                    x1=position["x"] + 100,
                    y1=y_offset + 40,
                    x2=position["x"] + 100,
                    y2=y_offset + 60,
                    color="#8b5cf6",
                    width=2,
                    layer_id=self.ai_layer_id
                )
                command_ids.append(cmd_id)
            
            y_offset += 60
        
        agent_idle("canvas")
        
        # Get all commands and filter to only the ones we just created
        all_commands = canvas_controller.get_pending_commands()
        command_objects = [cmd for cmd in all_commands if cmd.get("id") in command_ids]
        
        return {
            "success": True,
            "command_ids": command_ids,
            "commands": command_objects,
            "mode": "plan",
            "goal": goal,
            "steps_count": len(steps),
            "conversational_response": f"I've outlined a plan for {goal} with {len(steps)} steps."
        }
    
    def design(self, design_type: str, specs: Optional[Dict[str, Any]] = None, position: Optional[Dict[str, int]] = None, snapshot: Optional[str] = None, context_objects: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        AI-assisted design: Create diagrams, layouts, and technical plans.
        
        Args:
            design_type: Type of design (flowchart, wireframe, diagram, etc.)
            specs: Design specifications
            position: Where to place the design
        
        Returns:
            Dict with command IDs
        """
        # Route to specialized methods
        if "floor" in design_type.lower() or "plan" in design_type.lower() or "house" in design_type.lower():
            return self.create_floor_plan(description=design_type, rooms=specs.get("rooms") if specs else None)
            
        if "image" in design_type.lower() or "visual" in design_type.lower() or "photo" in design_type.lower():
            return self.generate_visual(prompt=design_type, position=position)

        agent_working("canvas", f"Designing: {design_type}...")
        
        if position is None:
            position = {"x": 150, "y": 150}
        
        if specs is None:
            specs = {}
        
        command_ids = []
        
        # Use LLM to generate design elements if available
        llm_success = False
        if self.agent_engine:
            try:
                system_prompt = f"""{SHARED_SKILLS}
                You are a technical diagram designer. 
                1. You can use tools to research the design requirements.
                2. Create a visual design for the user's request.
                3. Return a JSON list of shapes to draw in a markdown code block.
                
                Available shapes:
                - rectangle (x, y, width, height, color, text)
                - ellipse (cx, cy, rx, ry, color, text)
                - diamond (cx, cy, width, height, color, text)
                - line (x1, y1, x2, y2, color)
                - arrow (x1, y1, x2, y2, color)
                - text (x, y, text, color, font_size)
                
                Coordinate System:
                - x increases to the right
                - y increases downwards
                - Keep shapes close to the starting position
                """
                
                prompt = f"""
                Design Type: "{design_type}"
                Specs: {json.dumps(specs)}
                Starting Position: x={position['x']}, y={position['y']}
                
                Example Output:
                ```json
                [
                    {{"type": "rectangle", "x": 100, "y": 100, "width": 120, "height": 60, "color": "#8b5cf6", "text": "Login"}},
                    {{"type": "arrow", "x1": 160, "y1": 160, "x2": 160, "y2": 200, "color": "#8b5cf6"}}
                ]
                ```
                """
                
                response = self._process_request(prompt, system_prompt)
                shapes = self._extract_json(response)
                
                if shapes:
                    for shape in shapes:
                        sid = None
                        stype = shape.get("type")
                        color = shape.get("color", "#8b5cf6")
                        
                        if stype == "rectangle":
                            sid = canvas_controller.draw_rectangle(
                                x=shape.get("x"), y=shape.get("y"), 
                                width=shape.get("width"), height=shape.get("height"),
                                stroke_color=color, fill_color="rgba(139, 92, 246, 0.1)",
                                layer_id=self.ai_layer_id
                            )
                            if shape.get("text"):
                                canvas_controller.draw_text(
                                    text=shape.get("text"), 
                                    x=shape.get("x") + 10, 
                                    y=shape.get("y") + shape.get("height")/2 - 5,
                                    color="#e2e8f0", font_size=12,
                                    layer_id=self.ai_layer_id
                                )
                        elif stype == "ellipse":
                            sid = canvas_controller.draw_ellipse(
                                cx=shape.get("cx"), cy=shape.get("cy"),
                                rx=shape.get("rx"), ry=shape.get("ry"),
                                stroke_color=color, fill_color="rgba(139, 92, 246, 0.1)",
                                layer_id=self.ai_layer_id
                            )
                            if shape.get("text"):
                                canvas_controller.draw_text(
                                    text=shape.get("text"), 
                                    x=shape.get("cx") - 20, 
                                    y=shape.get("cy") - 5,
                                    color="#e2e8f0", font_size=12,
                                    layer_id=self.ai_layer_id
                                )
                        elif stype == "diamond":
                            # Draw diamond using 4 lines
                            cx, cy = shape.get("cx"), shape.get("cy")
                            w, h = shape.get("width"), shape.get("height")
                            hw, hh = w/2, h/2
                            
                            # Top to Right
                            canvas_controller.draw_line(x1=cx, y1=cy-hh, x2=cx+hw, y2=cy, color=color, layer_id=self.ai_layer_id)
                            # Right to Bottom
                            canvas_controller.draw_line(x1=cx+hw, y1=cy, x2=cx, y2=cy+hh, color=color, layer_id=self.ai_layer_id)
                            # Bottom to Left
                            canvas_controller.draw_line(x1=cx, y1=cy+hh, x2=cx-hw, y2=cy, color=color, layer_id=self.ai_layer_id)
                            # Left to Top
                            sid = canvas_controller.draw_line(x1=cx-hw, y1=cy, x2=cx, y2=cy-hh, color=color, layer_id=self.ai_layer_id)
                            
                            if shape.get("text"):
                                canvas_controller.draw_text(
                                    text=shape.get("text"), 
                                    x=cx - 20, 
                                    y=cy - 5,
                                    color="#e2e8f0", font_size=12,
                                    layer_id=self.ai_layer_id
                                )
                        elif stype == "line":
                            sid = canvas_controller.draw_line(
                                x1=shape.get("x1"), y1=shape.get("y1"),
                                x2=shape.get("x2"), y2=shape.get("y2"),
                                color=color, layer_id=self.ai_layer_id
                            )
                        elif stype == "arrow":
                            sid = canvas_controller.draw_arrow(
                                x1=shape.get("x1"), y1=shape.get("y1"),
                                x2=shape.get("x2"), y2=shape.get("y2"),
                                color=color, layer_id=self.ai_layer_id
                            )
                        elif stype == "text":
                            sid = canvas_controller.draw_text(
                                text=shape.get("text"), x=shape.get("x"), y=shape.get("y"),
                                color=color, font_size=shape.get("font_size", 12),
                                layer_id=self.ai_layer_id
                            )
                        
                        if sid:
                            command_ids.append(sid)
                    
                    llm_success = True
            except Exception as e:
                logger.error(f"LLM design error: {e}")

        if not llm_success:
            # Fallback logic
            # Title
            cmd_id = canvas_controller.draw_text(
                text=f"🏗️ Design: {design_type}",
                x=position["x"],
                y=position["y"] - 20,
                font_size=14,
                color="#c4b5fd",
                layer_id=self.ai_layer_id
            )
            command_ids.append(cmd_id)
            
            # AI label
            cmd_id = canvas_controller.draw_text(
                text="(Agent Amigos AI Assist)",
                x=position["x"],
                y=position["y"],
                font_size=10,
                color="#8b5cf6",
                layer_id=self.ai_layer_id
            )
            command_ids.append(cmd_id)
            
            # Simple flowchart as example
            if design_type.lower() in ["flowchart", "flow", "process"]:
                # Start node
                cmd_id = canvas_controller.draw_ellipse(
                    cx=position["x"] + 60,
                    cy=position["y"] + 50,
                    rx=50,
                    ry=25,
                    stroke_color="#8b5cf6",
                    fill_color="rgba(139, 92, 246, 0.1)",
                    stroke_width=2,
                    layer_id=self.ai_layer_id
                )
                command_ids.append(cmd_id)
                
                cmd_id = canvas_controller.draw_text(
                    text="Start",
                    x=position["x"] + 40,
                    y=position["y"] + 45,
                    font_size=12,
                    color="#e2e8f0",
                    layer_id=self.ai_layer_id
                )
                command_ids.append(cmd_id)
                
                # Arrow
                cmd_id = canvas_controller.draw_arrow(
                    x1=position["x"] + 60,
                    y1=position["y"] + 75,
                    x2=position["x"] + 60,
                    y2=position["y"] + 115,
                    color="#8b5cf6",
                    width=2,
                    layer_id=self.ai_layer_id
                )
                command_ids.append(cmd_id)
                
                # Process node
                cmd_id = canvas_controller.draw_rectangle(
                    x=position["x"] + 10,
                    y=position["y"] + 115,
                    width=100,
                    height=50,
                    stroke_color="#8b5cf6",
                    fill_color="rgba(139, 92, 246, 0.1)",
                    stroke_width=2,
                    layer_id=self.ai_layer_id
                )
                command_ids.append(cmd_id)
                
                cmd_id = canvas_controller.draw_text(
                    text="Process",
                    x=position["x"] + 30,
                    y=position["y"] + 135,
                    font_size=12,
                    color="#e2e8f0",
                    layer_id=self.ai_layer_id
                )
                command_ids.append(cmd_id)
        
        agent_idle("canvas")
        
        # Get all commands and filter to only the ones we just created
        all_commands = canvas_controller.get_pending_commands()
        command_objects = [cmd for cmd in all_commands if cmd.get("id") in command_ids]
        
        return {
            "success": True,
            "command_ids": command_ids,
            "commands": command_objects,
            "mode": "design",
            "design_type": design_type,
            "conversational_response": f"I've created a design layout for {design_type}."
        }
    
    def brainstorm(self, central_idea: str, branches: Optional[List[str]] = None, position: Optional[Dict[str, int]] = None, snapshot: Optional[str] = None, context_objects: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        AI-assisted brainstorming: Expand ideas visually using clusters or mind maps.
        
        Args:
            central_idea: The main concept
            branches: Related ideas branching from the center
            position: Center position for the mind map
        
        Returns:
            Dict with command_ids and full command objects
        """
        agent_working("canvas", "Creating mind map...")
        
        if position is None:
            position = {"x": 400, "y": 300}
        
        # Generate branches using LLM if not provided
        if branches is None or not branches:
            branches = ["Idea 1", "Idea 2", "Idea 3"] # Default fallback
            
            if self.agent_engine:
                try:
                    system_prompt = f"""{SHARED_SKILLS}
                    You are a brainstorming assistant. You can use tools to research the central idea. Generate 5 creative, distinct sub-topics or related ideas for the user's central concept. Return ONLY the ideas as a list, one per line."""
                    prompt = f"Central Idea: {central_idea}"
                    
                    response = self._process_request(prompt, system_prompt)
                    
                    # Parse response
                    generated_branches = [line.strip().lstrip("1234567890.- ") for line in response.split('\n') if line.strip()]
                    if generated_branches:
                        branches = generated_branches[:6] # Limit to 6 branches
                except Exception as e:
                    logger.error(f"LLM brainstorming error: {e}")
        
        command_ids = []
        
        # Central idea circle
        cmd_id = canvas_controller.draw_ellipse(
            cx=position["x"],
            cy=position["y"],
            rx=60,
            ry=40,
            stroke_color="#c4b5fd",
            fill_color="rgba(196, 181, 253, 0.2)",
            stroke_width=3,
            layer_id=self.ai_layer_id
        )
        command_ids.append(cmd_id)
        
        # Central text
        cmd_id = canvas_controller.draw_text(
            text=central_idea[:20],
            x=position["x"] - 40,
            y=position["y"] - 5,
            font_size=14,
            color="#e2e8f0",
            layer_id=self.ai_layer_id
        )
        command_ids.append(cmd_id)
        
        # AI label under center
        cmd_id = canvas_controller.draw_text(
            text="(AI Assist)",
            x=position["x"] - 25,
            y=position["y"] + 50,
            font_size=9,
            color="#8b5cf6",
            layer_id=self.ai_layer_id
        )
        command_ids.append(cmd_id)
        
        # Branch nodes in a circle around the center
        import math
        num_branches = min(len(branches), 6)  # Limit to 6 branches
        angle_step = (2 * math.pi) / num_branches
        radius = 120
        
        for i, branch in enumerate(branches[:num_branches]):
            angle = i * angle_step
            branch_x = position["x"] + radius * math.cos(angle)
            branch_y = position["y"] + radius * math.sin(angle)
            
            # Line to branch
            cmd_id = canvas_controller.draw_line(
                x1=position["x"],
                y1=position["y"],
                x2=branch_x,
                y2=branch_y,
                color="#8b5cf6",
                layer_id=self.ai_layer_id
            )
            command_ids.append(cmd_id)
            
            # Branch node
            cmd_id = canvas_controller.draw_ellipse(
                cx=branch_x,
                cy=branch_y,
                rx=45,
                ry=30,
                stroke_color="#8b5cf6",
                fill_color="rgba(139, 92, 246, 0.1)",
                stroke_width=2,
                layer_id=self.ai_layer_id
            )
            command_ids.append(cmd_id)
            
            # Branch text
            cmd_id = canvas_controller.draw_text(
                text=branch[:15],
                x=branch_x - 30,
                y=branch_y - 5,
                font_size=11,
                color="#e2e8f0",
                layer_id=self.ai_layer_id
            )
            command_ids.append(cmd_id)
        
        agent_idle("canvas")
        
        # Get all commands and filter to only the ones we just created
        all_commands = canvas_controller.get_pending_commands()
        command_objects = [cmd for cmd in all_commands if cmd.get("id") in command_ids]
        
        return {
            "success": True,
            "command_ids": command_ids,
            "commands": command_objects,
            "mode": "brainstorm",
            "central_idea": central_idea,
            "branches": branches,
            "conversational_response": f"I've created a mind map for {central_idea} with {len(branches)} branches."
        }
        
        return {
            "success": True,
            "command_ids": command_ids,
            "commands": command_objects,  # Return only the commands we just created
            "mode": "brainstorm",
            "central_idea": central_idea,
            "branches_count": num_branches,
            "conversational_response": f"I've mapped out some ideas centered around {central_idea}."
        }
    
    def annotate(self, target: str, note: str, position: Dict[str, int], snapshot: Optional[str] = None, context_objects: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Add an AI annotation/callout to existing content.
        
        Args:
            target: What is being annotated
            note: The annotation text
            position: Where to place the annotation
        
        Returns:
            Dict with command IDs
        """
        agent_thinking("canvas", f"Annotating: {target}...")
        
        commands = []
        
        # Annotation box
        cmd_id = canvas_controller.draw_rectangle(
            x=position["x"],
            y=position["y"],
            width=150,
            height=40,
            stroke_color="#fbbf24",
            fill_color="rgba(251, 191, 36, 0.1)",
            stroke_width=2,
            layer_id=self.ai_layer_id
        )
        commands.append(cmd_id)
        
        # Note text
        cmd_id = canvas_controller.draw_text(
            text=f"💡 {note[:40]}",
            x=position["x"] + 5,
            y=position["y"] + 12,
            font_size=11,
            color="#fbbf24",
            layer_id=self.ai_layer_id
        )
        commands.append(cmd_id)
        
        # AI label
        cmd_id = canvas_controller.draw_text(
            text="(AI)",
            x=position["x"] + 5,
            y=position["y"] + 27,
            font_size=9,
            color="#f59e0b",
            layer_id=self.ai_layer_id
        )
        commands.append(cmd_id)
        
        agent_idle("canvas")
        
        # Get all commands and filter to only the ones we just created
        all_commands = canvas_controller.get_pending_commands()
        command_objects = [cmd for cmd in all_commands if cmd.get("id") in commands]
        
        return {
            "success": True,
            "command_ids": commands,
            "commands": command_objects,
            "mode": "annotate",
            "conversational_response": f"I've added a note to the {target}."
        }
    
    def highlight(self, area: Dict[str, int], color: str = "#fbbf24") -> Dict[str, Any]:
        """
        Highlight a specific area on the board.
        
        Args:
            area: Dict with x, y, width, height
            color: Highlight color
        
        Returns:
            Dict with command ID and full commands
        """
        cmd_id = canvas_controller.draw_rectangle(
            x=area.get("x", 0),
            y=area.get("y", 0),
            width=area.get("width", 100),
            height=area.get("height", 100),
            stroke_color=color,
            fill_color=f"rgba(251, 191, 36, 0.15)",
            stroke_width=3,
            layer_id=self.ai_layer_id
        )
        
        # Get all commands and filter to only the one we just created
        all_commands = canvas_controller.get_pending_commands()
        command_objects = [cmd for cmd in all_commands if cmd.get("id") == cmd_id]
        
        return {
            "success": True,
            "command_ids": [cmd_id],
            "commands": command_objects,
            "mode": "highlight",
            "conversational_response": "I've highlighted that area for you."
        }

    def create_floor_plan(self, rooms: Optional[List[Dict[str, Any]]] = None, description: Optional[str] = None, scale: float = 10) -> Dict[str, Any]:
        """
        Generate a technical floor plan (AutoCAD style).
        
        Args:
            rooms: List of room specs (optional, can be generated from description)
            description: Description of the layout (e.g. "2 bedroom apartment")
            scale: Pixels per foot
        """
        agent_working("canvas", "Generating floor plan...")
        
        if not rooms and description and self.agent_engine:
            try:
                system_prompt = """You are an expert architect. 
                1. Convert the user's floor plan description into a JSON list of rooms.
                2. Each room needs: name, width (ft), height (ft), x (ft), y (ft), doors[], windows[].
                3. Arrange the rooms logically so they fit together without overlapping (unless intended).
                4. Assume (0,0) is the top-left corner of the house.
                5. Return ONLY valid JSON in a markdown code block.
                
                Example Output:
                ```json
                [
                    {
                        "name": "Living Room", "width": 20, "height": 15, "x": 0, "y": 0,
                        "doors": [{"x": 10, "y": 15, "width": 3, "swing": "left"}],
                        "windows": [{"x": 5, "y": 0, "width": 4}]
                    },
                    {
                        "name": "Kitchen", "width": 15, "height": 15, "x": 20, "y": 0,
                        "doors": [{"x": 20, "y": 10, "width": 3, "swing": "right"}],
                        "windows": [{"x": 35, "y": 5, "width": 4}]
                    }
                ]
                ```
                """
                prompt = f"Create a floor plan for: {description}"
                response = self._process_request(prompt, system_prompt)
                
                # Parse JSON
                import re
                json_str = ""
                # 1. Try markdown code block
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # 2. Try finding the first [ and last ]
                    start_idx = response.find('[')
                    end_idx = response.rfind(']')
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        json_str = response[start_idx:end_idx+1]
                    else:
                        # 3. Fallback cleanup
                        json_str = response.replace("```json", "").replace("```", "").strip()
                        
                rooms = json.loads(json_str)
                logger.info(f"Successfully parsed {len(rooms)} rooms for floor plan.")
            except Exception as e:
                logger.error(f"Floor plan generation error: {e}")
                logger.error(f"Raw response: {response}")
                # Fallback to default rooms if parsing fails
                rooms = None
        
        if not rooms:
            logger.warning("Using fallback floor plan layout.")
            # Fallback simple layout (2 rooms)
            rooms = [
                {
                    "name": "Main Room", "width": 20, "height": 15, "x": 0, "y": 0,
                    "doors": [{"x": 10, "y": 15, "width": 3}],
                    "windows": [{"x": 5, "y": 0, "width": 4}, {"x": 15, "y": 0, "width": 4}]
                },
                {
                    "name": "Side Room", "width": 12, "height": 15, "x": 20, "y": 0,
                    "doors": [{"x": 20, "y": 7, "width": 3}],
                    "windows": [{"x": 32, "y": 7, "width": 4}]
                }
            ]

        # Manually render the floor plan using primitives to ensure quality
        command_ids = []
        
        # Switch to CAD mode
        canvas_controller.set_mode("CAD")
        
        start_x = 100
        start_y = 100
        
        for room in rooms:
            # Convert feet to pixels
            rx = start_x + (room.get("x", 0) * scale)
            ry = start_y + (room.get("y", 0) * scale)
            rw = room.get("width", 10) * scale
            rh = room.get("height", 10) * scale
            
            # Draw Walls (4 sides)
            # Top
            cid = canvas_controller.draw_wall(x1=rx, y1=ry, x2=rx+rw, y2=ry, thickness=6)
            command_ids.append(cid)
            # Right
            cid = canvas_controller.draw_wall(x1=rx+rw, y1=ry, x2=rx+rw, y2=ry+rh, thickness=6)
            command_ids.append(cid)
            # Bottom
            cid = canvas_controller.draw_wall(x1=rx+rw, y1=ry+rh, x2=rx, y2=ry+rh, thickness=6)
            command_ids.append(cid)
            # Left
            cid = canvas_controller.draw_wall(x1=rx, y1=ry+rh, x2=rx, y2=ry, thickness=6)
            command_ids.append(cid)
            
            # Room Name
            cid = canvas_controller.draw_text(
                text=room.get("name", "Room"),
                x=rx + rw/2 - 20,
                y=ry + rh/2,
                font_size=14,
                color="#555555",
                layer_id="cad"
            )
            command_ids.append(cid)
            
            # Dimensions
            cid = canvas_controller.draw_text(
                text=f"{room.get('width')}x{room.get('height')}",
                x=rx + rw/2 - 15,
                y=ry + rh/2 + 20,
                font_size=10,
                color="#888888",
                layer_id="cad"
            )
            command_ids.append(cid)
            
            # Doors
            for door in room.get("doors", []):
                dx = start_x + (door.get("x", 0) * scale)
                dy = start_y + (door.get("y", 0) * scale)
                dw = door.get("width", 3) * scale
                # Determine orientation based on proximity to walls (simplified)
                # For now, just draw it
                cid = canvas_controller.draw_door(x=dx, y=dy, width=dw, swing=door.get("swing", "left"))
                command_ids.append(cid)
                
            # Windows
            for window in room.get("windows", []):
                wx = start_x + (window.get("x", 0) * scale)
                wy = start_y + (window.get("y", 0) * scale)
                ww = window.get("width", 4) * scale
                cid = canvas_controller.draw_window(x=wx, y=wy, width=ww)
                command_ids.append(cid)

        # Get command objects
        all_commands = canvas_controller.get_pending_commands()
        command_objects = [cmd for cmd in all_commands if cmd.get("id") in command_ids]
        
        return {
            "success": True,
            "command_ids": command_ids,
            "commands": command_objects,
            "mode": "floor_plan",
            "conversational_response": f"I've generated a detailed floor plan layout with {len(rooms)} rooms."
        }

    def generate_visual(self, prompt: str, position: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """
        Generate a visual image (Photoshop style) using AI image generation tools.
        
        Args:
            prompt: Image description
            position: Where to place it
        """
        agent_working("canvas", f"Generating visual: {prompt[:30]}...")
        
        if position is None:
            position = {"x": 200, "y": 200}
            
        image_url = "https://via.placeholder.com/300" # Fallback
        
        try:
            # Use the media tool to generate an image
            result = media.generate_image(prompt=prompt, width=512, height=512)
            if result.get("success") and result.get("images"):
                # Get the first image path
                import os
                from pathlib import Path
                image_path = result["images"][0]
                filename = Path(image_path).name
                # Construct URL (assuming standard media mount)
                image_url = f"/media/images/{filename}"
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            
        cmd_id = canvas_controller.draw_image(
            url=image_url,
            x=position["x"],
            y=position["y"],
            width=300,
            height=300,
            caption=prompt,
            layer_id=self.ai_layer_id
        )
        
        all_commands = canvas_controller.get_pending_commands()
        command_objects = [cmd for cmd in all_commands if cmd.get("id") == cmd_id]
        
        return {
            "success": True,
            "command_ids": [cmd_id],
            "commands": command_objects,
            "mode": "visual",
            "conversational_response": f"I've generated a visual for '{prompt}'."
        }
    
    def ask_question(self, question: str, options: List[str], position: Optional[Dict[str, int]] = None, snapshot: Optional[str] = None, context_objects: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Ask a visual question with options the user can point to or circle.
        
        Args:
            question: The question to ask
            options: List of possible answers
            position: Where to place the question
        
        Returns:
            Dict with command IDs
        """
        agent_thinking("canvas", "Asking question...")
        
        if position is None:
            position = {"x": 100, "y": 100}
        
        commands = []
        
        # Question text
        cmd_id = canvas_controller.draw_text(
            text=f"❓ {question[:50]}",
            x=position["x"],
            y=position["y"],
            font_size=13,
            color="#c4b5fd",
            layer_id=self.ai_layer_id
        )
        commands.append(cmd_id)
        
        # AI label
        cmd_id = canvas_controller.draw_text(
            text="(Agent Amigos AI)",
            x=position["x"],
            y=position["y"] + 18,
            font_size=10,
            color="#8b5cf6",
            layer_id=self.ai_layer_id
        )
        commands.append(cmd_id)
        
        # Options
        y_offset = position["y"] + 45
        for i, option in enumerate(options[:4], 1):  # Limit to 4 options
            # Option box
            cmd_id = canvas_controller.draw_rectangle(
                x=position["x"],
                y=y_offset,
                width=180,
                height=30,
                stroke_color="#8b5cf6",
                fill_color="rgba(139, 92, 246, 0.05)",
                stroke_width=1,
                layer_id=self.ai_layer_id
            )
            commands.append(cmd_id)
            
            # Option text
            cmd_id = canvas_controller.draw_text(
                text=f"{i}. {option[:30]}",
                x=position["x"] + 10,
                y=y_offset + 10,
                font_size=11,
                color="#e2e8f0",
                layer_id=self.ai_layer_id
            )
            commands.append(cmd_id)
            
            y_offset += 35
        
        agent_idle("canvas")
        
        # Get all commands and filter to only the ones we just created
        all_commands = canvas_controller.get_pending_commands()
        command_objects = [cmd for cmd in all_commands if cmd.get("id") in commands]
        
        return {
            "success": True,
            "command_ids": commands,
            "commands": command_objects,
            "mode": "ask_question",
            "question": question,
            "conversational_response": f"I've posted the question: {question}"
        }


# Global instance
canvas_ai_assist = CanvasAIAssist()
