"""
Canvas Design Tool for Agent Amigos
====================================

Enables AI agent to actively use Canvas for visual design.
Implements the Think → Draw → Explain loop.

Integrated with Media tools to generate 2D/3D images from designs.
"""

import logging
from typing import Dict, Any, Optional
from ..agents.design import DesignPlanner

# Import canvas controller to queue commands
try:
    from ..canvas import canvas_controller
    CANVAS_AVAILABLE = True
except ImportError:
    CANVAS_AVAILABLE = False
    import warnings
    warnings.warn("Canvas controller not available - design commands won't render")

# Import media tools for image generation
try:
    from .media_tools import media
    MEDIA_AVAILABLE = True
except ImportError:
    MEDIA_AVAILABLE = False
    media = None

logger = logging.getLogger(__name__)

# Global design planner instance (per session)
_design_planners = {}


def get_design_planner(session_id: str) -> DesignPlanner:
    """Get or create DesignPlanner for session"""
    if session_id not in _design_planners:
        _design_planners[session_id] = DesignPlanner(session_id)
    return _design_planners[session_id]


def canvas_design(
    goal: str,
    action: str = "design",
    feedback: Optional[str] = None,
    session_id: str = "default",
    narrate: bool = True,
    generate_images: bool = True
) -> Dict[str, Any]:
    """
    Canvas Design Tool - Draw and plan designs on Canvas.
    
    Args:
        goal: Natural language design goal (e.g., "2 bedroom tropical house with good airflow")
        action: "design" (new), "refine" (modify existing), "iterate" (multi-pass)
        feedback: Refinement instructions when action="refine"
        session_id: Session identifier for design continuity
        narrate: Whether to narrate design process
    
    Returns:
        Design result with Canvas commands and narration
        
    Examples:
        canvas_design(goal="Small office with separate entrance")
        canvas_design(goal="...", action="refine", feedback="Make kitchen bigger")
        canvas_design(goal="...", action="iterate")  # Multi-pass refinement
    """
    
    try:
        planner = get_design_planner(session_id)
        
        if action == "design":
            # New design
            logger.info(f"🎨 Creating new design: {goal}")
            result = planner.design(goal, narrate=narrate)
            
        elif action == "refine":
            # Refine existing design
            if not feedback:
                return {
                    "success": False,
                    "error": "Refinement requires 'feedback' parameter"
                }
            
            logger.info(f"🔄 Refining design: {feedback}")
            result = planner.refine(feedback, narrate=narrate)
            
        elif action == "iterate":
            # Multi-pass iteration
            logger.info(f"🔁 Multi-pass iteration: {goal}")
            result = planner.iterate(goal, passes=3, narrate=narrate)
            
        elif action == "list":
            # List recent designs
            result = planner.list_recent_designs(limit=10)
            
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}. Use: design, refine, iterate, list"
            }
        
        # Format result for agent
        if result.get("success"):
            # Ensure narration is a list of strings, not a string
            narration_data = result.get("narration", [])
            if isinstance(narration_data, str):
                # If it's a string (shouldn't be), split by newlines
                narration_list = narration_data.split("\n")
            elif not isinstance(narration_data, list):
                # If it's something else, convert to list
                narration_list = [str(narration_data)]
            else:
                narration_list = narration_data

            narration_list = [str(n) for n in narration_list if n is not None]

            # Keep a text version for backward compatibility with older callers.
            narration_text = "\n".join(narration_list)
            
            response = {
                "success": True,
                "action": action,
                "goal": result.get("goal", goal),
                "design_summary": result.get("plan", {}),
                # Prefer structured narration (list of steps). Also include narration_text.
                "narration": narration_list,
                "narration_text": narration_text,
                "explanation": result.get("explanation", ""),
                "canvas_updated": bool(result.get("canvas_commands")),
                "session_id": result.get("session_id"),
                "design_pass": result.get("design_pass", 1)
            }
            
            # Add Canvas commands and queue them for rendering
            if "canvas_commands" in result and result["canvas_commands"]:
                response["canvas_commands"] = result["canvas_commands"]

                # NOTE:
                # We intentionally do NOT push these raw, type-based commands into the
                # Canvas MCP command queue. The MCP queue stores DrawCommand objects and
                # expects `to_dict()`; appending raw dicts corrupts the queue.
                # The frontend already consumes `canvas_commands` directly from tool results
                # and maps them to its internal command format.
            
            # Optionally generate AI images of the design (2D and 3D)
            if generate_images and action in ["design", "iterate"]:
                try:
                    generated_images = []
                    
                    # Generate 2D floor plan image
                    img_2d = generate_design_image(
                        design_description=goal,
                        image_type="2d",
                        style="architectural"
                    )
                    if img_2d.get("success"):
                        generated_images.append(img_2d)
                        logger.info("✓ Generated 2D floor plan image")
                    
                    # Generate 3D render image
                    img_3d = generate_design_image(
                        design_description=goal,
                        image_type="3d",
                        style="modern"
                    )
                    if img_3d.get("success"):
                        generated_images.append(img_3d)
                        logger.info("✓ Generated 3D architectural render")
                    
                    if generated_images:
                        response["generated_images"] = generated_images
                        response["visual_aids"] = f"Generated {len(generated_images)} visualization images"
                
                except Exception as e:
                    logger.warning(f"Could not generate images: {e}")
            
            return response
        else:
            return result
            
    except Exception as e:
        logger.error(f"Canvas design error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "action": action,
            "goal": goal
        }


# Tool metadata for registration
CANVAS_DESIGN_TOOL = {
    "name": "canvas_design",
    "description": "Draw and plan architectural designs on Canvas. Use this when users ask to design, draw, sketch, or show layouts. Supports new designs, refinements, and multi-pass iterations.",
    "parameters": {
        "goal": {
            "type": "string",
            "description": "Natural language design goal (e.g., '2 bedroom tropical house with good airflow', 'small office with separate entrance')",
            "required": True
        },
        "action": {
            "type": "string",
            "description": "Action type: 'design' (new design), 'refine' (modify existing), 'iterate' (multi-pass refinement), 'list' (show recent designs)",
            "enum": ["design", "refine", "iterate", "list"],
            "default": "design"
        },
        "feedback": {
            "type": "string",
            "description": "Refinement instructions when action='refine' (e.g., 'make kitchen bigger', 'add balcony', 'improve ventilation')",
            "required": False
        },
        "session_id": {
            "type": "string",
            "description": "Session identifier for design continuity",
            "default": "default"
        },
        "narrate": {
            "type": "boolean",
            "description": "Whether to narrate design process (recommended: true)",
            "default": True
        }
    },
    "returns": {
        "success": "boolean",
        "design_summary": "object with layout info",
        "narration": "design process narrative",
        "explanation": "design explanation",
        "canvas_updated": "boolean",
        "canvas_commands": "list of Canvas drawing commands"
    },
    "category": "design",
    "trigger_keywords": ["design", "draw", "sketch", "plan", "layout", "show me", "create", "blueprint", "house", "room", "building"]
}


def generate_design_image(
    design_description: str,
    image_type: str = "2d",
    style: str = "architectural",
    output_format: str = "png"
) -> Dict[str, Any]:
    """
    Generate 2D or 3D image of a design using AI.
    
    Args:
        design_description: Description of the design (e.g., "2 bedroom tropical house with good airflow")
        image_type: "2d" (floor plan style), "3d" (3D render), or "perspective" (3D perspective view)
        style: "architectural", "modern", "minimalist", "luxury", "rustic", etc.
        output_format: "png", "jpg", "webp"
    
    Returns:
        Result dict with image path, URL, and metadata
    """
    if not MEDIA_AVAILABLE:
        logger.warning("Media tools not available - cannot generate images")
        return {
            "success": False,
            "error": "Media generation tools not available"
        }

    # For type checkers: MEDIA_AVAILABLE implies `media` imported successfully.
    assert media is not None
    
    try:
        # Build comprehensive prompt for image generation
        if image_type == "2d":
            prompt = f"Floor plan, top-down view, {design_description}, {style} architecture style, clean lines, labeled rooms, dimensions shown, professional blueprint"
        elif image_type == "3d":
            prompt = f"3D architectural render, {design_description}, {style} interior design, realistic lighting, detailed textures, high quality, professional visualization"
        elif image_type == "perspective":
            prompt = f"3D perspective view exterior, {design_description}, {style} architecture, beautiful surroundings, natural lighting, architectural visualization"
        else:
            prompt = f"{design_description}, {style} architecture style"
        
        logger.info(f"🎨 Generating {image_type} image: {prompt[:60]}...")
        
        # Call media generation tool
        result = media.generate_image(
            prompt=prompt,
            style=style,
            output_format=output_format
        )
        
        if result.get("success"):
            logger.info(f"✓ Generated {image_type} image: {result.get('image_path')}")
            return {
                "success": True,
                "image_path": result.get("image_path"),
                "image_url": result.get("image_url"),
                "image_type": image_type,
                "design_description": design_description,
                "prompt_used": prompt,
                "format": output_format
            }
        else:
            logger.error(f"Image generation failed: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "design_description": design_description
            }
    
    except Exception as e:
        logger.error(f"Error generating design image: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "design_description": design_description
        }


def detect_design_request(user_message: str) -> bool:
    """
    Detect if user is requesting design/drawing.
    
    Trigger phrases:
    - "show me"
    - "draw it"
    - "can you sketch"
    - "design a"
    - "create a layout"
    - "plan a house"
    - "let's redesign"
    - "change the kitchen"
    """
    message_lower = user_message.lower()
    
    triggers = [
        "show me",
        "draw",
        "sketch",
        "design",
        "create a layout",
        "plan a",
        "let's redesign",
        "redesign",
        "change the",
        "make a",
        "blueprint",
        "floor plan",
        "layout",
        "house plan",
        "building design",
        "room layout"
    ]
    
    return any(trigger in message_lower for trigger in triggers)
