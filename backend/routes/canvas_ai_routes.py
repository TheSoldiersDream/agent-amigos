"""
Canvas AI Assist API Routes

Exposes AI-assisted Canvas capabilities:
- /canvas/ai/discuss - AI-assisted discussion
- /canvas/ai/draw - AI-assisted drawing
- /canvas/ai/plan - AI-assisted planning
- /canvas/ai/design - AI-assisted design
- /canvas/ai/brainstorm - AI-assisted brainstorming
- /canvas/ai/annotate - Add AI annotations
- /canvas/ai/highlight - Highlight areas
- /canvas/ai/ask - Ask visual questions
- /canvas/ai/startup - Show startup note
- /canvas/ai/status - Get AI assist status
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging

from canvas.canvas_ai_assist import canvas_ai_assist
from canvas.canvas_controller import canvas_controller

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/canvas/ai", tags=["canvas_ai"])


class PositionModel(BaseModel):
    """Position on the board"""
    x: int = Field(..., description="X coordinate")
    y: int = Field(..., description="Y coordinate")


class AreaModel(BaseModel):
    """Area on the board"""
    x: int
    y: int
    width: int
    height: int


class DiscussRequest(BaseModel):
    """Request for AI-assisted discussion"""
    topic: str = Field(..., description="Topic to discuss")
    position: Optional[PositionModel] = None


class DrawRequest(BaseModel):
    """Request for AI-assisted drawing"""
    description: str = Field(..., description="What to draw")
    position: Optional[PositionModel] = None


class PlanRequest(BaseModel):
    """Request for AI-assisted planning"""
    goal: str = Field(..., description="Planning goal")
    steps: Optional[List[str]] = None
    position: Optional[PositionModel] = None


class DesignRequest(BaseModel):
    """Request for AI-assisted design"""
    design_type: str = Field(..., description="Type of design (flowchart, wireframe, etc.)")
    specs: Optional[Dict[str, Any]] = None
    position: Optional[PositionModel] = None


class BrainstormRequest(BaseModel):
    """Request for AI-assisted brainstorming"""
    central_idea: str = Field(..., description="Central idea/concept")
    branches: Optional[List[str]] = None
    position: Optional[PositionModel] = None


class AnnotateRequest(BaseModel):
    """Request to add AI annotation"""
    target: str = Field(..., description="What is being annotated")
    note: str = Field(..., description="Annotation text")
    position: PositionModel = Field(..., description="Annotation position")


class HighlightRequest(BaseModel):
    """Request to highlight an area"""
    area: AreaModel = Field(..., description="Area to highlight")
    color: str = Field(default="#fbbf24", description="Highlight color")


class AskQuestionRequest(BaseModel):
    """Request to ask a visual question"""
    question: str = Field(..., description="Question to ask")
    options: List[str] = Field(..., description="Answer options")
    position: Optional[PositionModel] = None


class CreateFloorPlanRequest(BaseModel):
    """Request for AI-assisted floor plan"""
    description: Optional[str] = Field(None, description="Description of the layout")
    rooms: Optional[List[Dict[str, Any]]] = None
    scale: float = 10.0


class GenerateVisualRequest(BaseModel):
    """Request for AI-assisted visual generation"""
    prompt: str = Field(..., description="Image description")
    position: Optional[PositionModel] = None


@router.post("/discuss")
async def ai_discuss(request: DiscussRequest):
    """
    AI-assisted discussion: Explain ideas.
    
    Adds a discussion box with AI explanations/thoughts.
    """
    try:
        position = request.position.dict() if request.position else None
        result = canvas_ai_assist.discuss(request.topic, position)
        commands = canvas_controller.get_pending_commands()
        return {**result, "commands": commands}
    except Exception as e:
        logger.error(f"AI discuss error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/draw")
async def ai_draw(request: DrawRequest):
    """
    AI-assisted drawing: Add sketches, arrows, highlights, callouts.
    
    Extends user drawings with AI-generated visual elements.
    """
    try:
        position = request.position.dict() if request.position else None
        result = canvas_ai_assist.draw(request.description, position)
        commands = canvas_controller.get_pending_commands()
        return {**result, "commands": commands}
    except Exception as e:
        logger.error(f"AI draw error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan")
async def ai_plan(request: PlanRequest):
    """
    AI-assisted planning: Convert rough ideas into structured visual plans.
    
    Creates step-by-step visual plans with boxes and arrows.
    """
    try:
        position = request.position.dict() if request.position else None
        result = canvas_ai_assist.plan(
            request.goal,
            request.steps,
            position
        )
        commands = canvas_controller.get_pending_commands()
        return {**result, "commands": commands}
    except Exception as e:
        logger.error(f"AI plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/design")
async def ai_design(request: DesignRequest):
    """
    AI-assisted design: Create diagrams, layouts, technical plans.
    
    Generates flowcharts, wireframes, system diagrams, etc.
    """
    try:
        position = request.position.dict() if request.position else None
        result = canvas_ai_assist.design(
            request.design_type,
            request.specs,
            position
        )
        commands = canvas_controller.get_pending_commands()
        return {**result, "commands": commands}
    except Exception as e:
        logger.error(f"AI design error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brainstorm")
async def ai_brainstorm(request: BrainstormRequest):
    """
    AI-assisted brainstorming: Expand ideas visually using mind maps.
    
    Creates radial mind maps with central idea and branches.
    """
    try:
        position = request.position.dict() if request.position else None
        result = canvas_ai_assist.brainstorm(
            request.central_idea,
            request.branches,
            position
        )
        
        logger.info(f"🧠 Brainstorm: result has {len(result.get('commands', []))} commands and {len(result.get('command_ids', []))} command_ids")
        
        return result
    except Exception as e:
        logger.error(f"AI brainstorm error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/annotate")
async def ai_annotate(request: AnnotateRequest):
    """
    Add an AI annotation/callout to existing content.
    
    Creates a labeled note box with AI insights.
    """
    try:
        result = canvas_ai_assist.annotate(
            request.target,
            request.note,
            request.position.dict()
        )
        commands = canvas_controller.get_pending_commands()
        return {**result, "commands": commands}
    except Exception as e:
        logger.error(f"AI annotate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/highlight")
async def ai_highlight(request: HighlightRequest):
    """
    Highlight a specific area on the board.
    
    Draws a semi-transparent highlight box.
    """
    try:
        result = canvas_ai_assist.highlight(
            request.area.dict(),
            request.color
        )
        commands = canvas_controller.get_pending_commands()
        return {**result, "commands": commands}
    except Exception as e:
        logger.error(f"AI highlight error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask")
async def ai_ask_question(request: AskQuestionRequest):
    """
    Ask a visual question with options.
    
    Creates a question box with clickable/circable options.
    """
    try:
        position = request.position.dict() if request.position else None
        result = canvas_ai_assist.ask_question(
            request.question,
            request.options,
            position
        )
        commands = canvas_controller.get_pending_commands()
        return {**result, "commands": commands}
    except Exception as e:
        logger.error(f"AI ask question error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/floor_plan")
async def ai_floor_plan(request: CreateFloorPlanRequest):
    """Generate a technical floor plan."""
    try:
        result = canvas_ai_assist.create_floor_plan(
            rooms=request.rooms,
            description=request.description,
            scale=request.scale
        )
        commands = canvas_controller.get_pending_commands()
        return {**result, "commands": commands}
    except Exception as e:
        logger.error(f"AI floor plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/visual")
async def ai_visual(request: GenerateVisualRequest):
    """Generate a visual image."""
    try:
        position = request.position.dict() if request.position else None
        result = canvas_ai_assist.generate_visual(
            prompt=request.prompt,
            position=position
        )
        commands = canvas_controller.get_pending_commands()
        return {**result, "commands": commands}
    except Exception as e:
        logger.error(f"AI visual error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Playwright test generation (prototype integration with Awesome Copilot prompt)
class PlaywrightRequest(BaseModel):
    """Request to generate a Playwright test from a scenario"""
    scenario: Optional[str] = Field(None, description="Natural-language scenario to convert into a test")
    model_id: Optional[str] = Field(None, description="Model id to use (optional)")


@router.post("/playwright")
async def generate_playwright_test(request: PlaywrightRequest):
    """Generate a Playwright test using the Awesome Copilot prompt and the configured LLM(s).

    Prototype behavior:
    - Read the `playwright-generate-test.prompt.md` file from the cloned `external/awesome-copilot` repo
    - Compose a prompt that includes the scenario
    - Use backend/core/model_manager.get_model_manager().generate to call a model
    - Save a generated test file under `backend/test_generated` and return its path and content
    """
    try:
        from backend.core.model_manager import get_model_manager
        import os
        from datetime import datetime

        scenario_text = request.scenario or ""

        # Locate prompt file in the cloned repo
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        prompt_path = os.path.join(repo_root, "external", "awesome-copilot", "prompts", "playwright-generate-test.prompt.md")

        if not os.path.exists(prompt_path):
            logger.error(f"Playwright prompt file not found: {prompt_path}")
            raise HTTPException(status_code=500, detail="Playwright prompt not found in external/awesome-copilot")

        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()

        # Build the final prompt for the model
        final_prompt = f"{prompt_template}\n\nScenario:\n{scenario_text}\n\nPlease produce a single Playwright TypeScript test using @playwright/test. Only output the test code."

        manager = get_model_manager()
        # Choose a default coding-capable model if not provided
        model_id = request.model_id or "qwen2.5:72b"

        result = await manager.generate(model_id=model_id, prompt=final_prompt)

        if not result.get("success"):
            logger.error(f"Model generation failed: {result}")
            raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))

        response_text = result.get("response", "")

        # Attempt to extract code block if present
        import re
        code_match = re.search(r"```(?:ts|typescript)?\n([\s\S]*?)\n```", response_text, re.IGNORECASE)
        code = code_match.group(1) if code_match else response_text

        # Ensure output dir exists
        out_dir = os.path.join(repo_root, "backend", "test_generated")
        os.makedirs(out_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        filename = f"playwright_test_{timestamp}.spec.ts"
        out_path = os.path.join(out_dir, filename)

        with open(out_path, "w", encoding="utf-8") as out_f:
            out_f.write(code)

        commands = canvas_controller.get_pending_commands()
        return {
            "success": True,
            "file": out_path,
            "code": code,
            "response": response_text,
            "commands": commands,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Playwright generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/startup")
async def show_startup_note():
    """
    Show the AI assist startup note.
    
    Displays a small corner message indicating AI is ready.
    """
    try:
        result = canvas_ai_assist.show_startup_note()
        if result is None:
            return {"success": True, "already_shown": True}
        return {"success": True, "command_id": result}
    except Exception as e:
        logger.error(f"AI startup note error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_ai_status():
    """
    Get the current status of Canvas AI Assist.
    
    Returns:
        - enabled: Whether AI assist is active
        - conversation_count: Number of conversation entries
        - corner_note_shown: Whether startup note has been displayed
    """
    try:
        return {
            "success": True,
            "enabled": canvas_ai_assist.enabled,
            "conversation_count": len(canvas_ai_assist.conversation_history),
            "corner_note_shown": canvas_ai_assist.corner_note_shown,
            "ai_layer_id": canvas_ai_assist.ai_layer_id
        }
    except Exception as e:
        logger.error(f"AI status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enable")
async def enable_ai_assist():
    """Enable Canvas AI Assist"""
    canvas_ai_assist.enabled = True
    return {"success": True, "enabled": True}


@router.post("/disable")
async def disable_ai_assist():
    """Disable Canvas AI Assist"""
    canvas_ai_assist.enabled = False
    return {"success": True, "enabled": False}
