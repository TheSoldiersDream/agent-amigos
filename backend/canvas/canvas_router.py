"""
🧠🎨 Agent Amigos Chalk Board - API Router

FastAPI router for chalk board endpoints.

Created by Darrell Buttigieg (@darrellbuttigieg) #thesoldiersdream
"""

from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import io

from .canvas_models import (
    CanvasState, CanvasObject, Layer, DrawMode, ObjectType,
    AgentDrawCommand, AgentCommandResponse,
    ExportRequest, ExportResponse, ExportFormat,
    FloorPlanTemplate, FloorPlanRoom, FlowchartTemplate,
    DiscussRequest, DrawRequest, PlanRequest, DesignRequest,
    BrainstormRequest, AnnotateRequest, AskRequest
)
from .canvas_state import state_manager
from .canvas_controller import canvas_controller
from .canvas_ai_assist import canvas_ai_assist
try:
    from autonomy.controller import autonomy_controller
except Exception:
    autonomy_controller = None


router = APIRouter(prefix="/canvas", tags=["Canvas"])


# ═══════════════════════════════════════════════════════════════
# SESSION ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/session", response_model=CanvasState)
async def create_session(
    user_id: Optional[str] = Body(None),
    title: str = Body("Untitled"),
    action: str = Body("create")
):
    """Create a new chalk board session"""
    if action == "create":
        session = state_manager.create_session(user_id=user_id, title=title)
        return session
    raise HTTPException(status_code=400, detail="Invalid action")


@router.get("/session/{session_id}", response_model=CanvasState)
async def get_session(session_id: str):
    """Get a chalk board session by ID"""
    session = state_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions", response_model=List[CanvasState])
async def list_sessions(user_id: Optional[str] = Query(None)):
    """List all sessions"""
    return state_manager.list_sessions(user_id=user_id)


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a chalk board session"""
    if state_manager.delete_session(session_id):
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@router.patch("/session/{session_id}")
async def update_session(
    session_id: str,
    title: Optional[str] = Body(None),
    mode: Optional[DrawMode] = Body(None),
    grid_enabled: Optional[bool] = Body(None),
    snap_to_grid: Optional[bool] = Body(None),
    pan_x: Optional[float] = Body(None),
    pan_y: Optional[float] = Body(None),
    zoom: Optional[float] = Body(None),
):
    """Update session settings"""
    session = state_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if title is not None:
        session.title = title
    if mode is not None:
        session.mode = mode
    if grid_enabled is not None:
        session.grid_enabled = grid_enabled
    if snap_to_grid is not None:
        session.snap_to_grid = snap_to_grid
    if pan_x is not None:
        session.pan_x = pan_x
    if pan_y is not None:
        session.pan_y = pan_y
    if zoom is not None:
        session.zoom = zoom
    
    session.updated_at = datetime.utcnow()
    state_manager._save_session(session_id)
    
    return session


# ═══════════════════════════════════════════════════════════════
# OBJECT ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/session/{session_id}/objects", response_model=CanvasObject)
async def add_object(session_id: str, obj: CanvasObject):
    """Add an object to the chalk board"""
    result = state_manager.add_object(session_id, obj)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.get("/session/{session_id}/objects", response_model=List[CanvasObject])
async def get_objects(
    session_id: str,
    layer_id: Optional[str] = Query(None)
):
    """Get objects from a session"""
    return state_manager.get_objects(session_id, layer_id=layer_id)


@router.patch("/session/{session_id}/objects/{object_id}", response_model=CanvasObject)
async def update_object(
    session_id: str,
    object_id: str,
    updates: Dict[str, Any] = Body(...)
):
    """Update an object"""
    result = state_manager.update_object(session_id, object_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Object or session not found")
    return result


@router.delete("/session/{session_id}/objects/{object_id}")
async def delete_object(session_id: str, object_id: str):
    """Delete an object"""
    if state_manager.delete_object(session_id, object_id):
        return {"status": "deleted", "object_id": object_id}
    raise HTTPException(status_code=404, detail="Object or session not found")


@router.delete("/session/{session_id}/objects")
async def clear_objects(session_id: str):
    """Clear all objects from a session"""
    if state_manager.clear_objects(session_id):
        return {"status": "cleared", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


# ═══════════════════════════════════════════════════════════════
# LAYER ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/session/{session_id}/layers", response_model=Layer)
async def add_layer(session_id: str, layer: Layer):
    """Add a layer to the session"""
    result = state_manager.add_layer(session_id, layer)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.patch("/session/{session_id}/layers/{layer_id}", response_model=Layer)
async def update_layer(
    session_id: str,
    layer_id: str,
    updates: Dict[str, Any] = Body(...)
):
    """Update a layer"""
    result = state_manager.update_layer(session_id, layer_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Layer or session not found")
    return result


@router.delete("/session/{session_id}/layers/{layer_id}")
async def delete_layer(session_id: str, layer_id: str):
    """Delete a layer and its objects"""
    if state_manager.delete_layer(session_id, layer_id):
        return {"status": "deleted", "layer_id": layer_id}
    raise HTTPException(status_code=404, detail="Layer or session not found")


@router.put("/session/{session_id}/layers/reorder")
async def reorder_layers(
    session_id: str,
    layer_order: List[str] = Body(...)
):
    """Reorder layers"""
    if state_manager.reorder_layers(session_id, layer_order):
        return {"status": "reordered"}
    raise HTTPException(status_code=404, detail="Session not found")


# ═══════════════════════════════════════════════════════════════
# HISTORY ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/session/{session_id}/undo")
async def undo(session_id: str):
    """Undo the last action"""
    if state_manager.undo(session_id):
        return {"status": "undone"}
    raise HTTPException(status_code=400, detail="Nothing to undo")


@router.post("/session/{session_id}/redo")
async def redo(session_id: str):
    """Redo the last undone action"""
    if state_manager.redo(session_id):
        return {"status": "redone"}
    raise HTTPException(status_code=400, detail="Nothing to redo")


@router.get("/session/{session_id}/history")
async def get_history_status(session_id: str):
    """Get history status"""
    return {
        "can_undo": state_manager.can_undo(session_id),
        "can_redo": state_manager.can_redo(session_id),
    }


# ═══════════════════════════════════════════════════════════════
# AGENT COMMAND ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/session/{session_id}/agent/command", response_model=AgentCommandResponse)
async def execute_agent_command(session_id: str, command: AgentDrawCommand):
    """Execute a command from an agent"""
    # Autonomy check: ensure canvas actions are allowed
    if autonomy_controller and not autonomy_controller.is_action_allowed('canvas'):
        raise HTTPException(status_code=403, detail='Autonomy policy blocks canvas operations')
    response = await state_manager.process_agent_command(session_id, command)
    if autonomy_controller:
        try:
            autonomy_controller.log_action('canvas_executed', {'session_id': session_id, 'command': command.model_dump()}, {'result': response})
        except Exception:
            pass
    return response


@router.post("/session/{session_id}/agent/queue")
async def queue_agent_command(session_id: str, command: AgentDrawCommand):
    """Queue a command for frontend processing"""
    state_manager.queue_agent_command(session_id, command)
    if autonomy_controller:
        try:
            autonomy_controller.log_action('canvas_queued', {'session_id': session_id, 'command': command.model_dump()}, {})
        except Exception:
            pass
    return {"status": "queued", "command_id": command.id}


@router.post("/session/{session_id}/agent/reject")
async def reject_agent_command(session_id: str, command: AgentDrawCommand):
    """Reject a pending command from an agent (user declined execution)."""
    # Log rejection to autonomy controller if present
    if autonomy_controller:
        try:
            autonomy_controller.log_action('canvas_command_rejected', {'session_id': session_id, 'command': command.model_dump()}, {})
        except Exception:
            pass
    # No state change necessary other than acknowledging rejection
    return {"status": "rejected", "command_id": command.id}


@router.get("/session/{session_id}/agent/pending", response_model=List[AgentDrawCommand])
async def get_pending_commands(session_id: str):
    """Get pending commands for frontend"""
    return state_manager.get_pending_commands(session_id)



@router.get("/agent/queue")
async def get_global_pending_commands():
    """Get all pending commands from default session"""
    # Return commands from controller queue
    return {"commands": canvas_controller.get_pending_commands()}


@router.post("/agent/clear")
async def clear_agent_commands():
    """Clear all pending commands from the queue"""
    canvas_controller.clear_queue()
    return {"status": "cleared"}
# ═══════════════════════════════════════════════════════════════
# EXPORT ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/export")
async def export_canvas(request: ExportRequest):
    """Export chalk board content"""
    try:
        if request.format == ExportFormat.JSON:
            content = json.dumps({
                "objects": [obj.model_dump() for obj in request.objects],
                "layers": [layer.model_dump() for layer in (request.layers or [])],
                "exported_at": datetime.utcnow().isoformat(),
            }, default=str, indent=2)
            
            return StreamingResponse(
                io.BytesIO(content.encode()),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=canvas.json"}
            )
        
        elif request.format == ExportFormat.SVG:
            svg = generate_svg(request.objects, request.width, request.height, request.background_color)
            return StreamingResponse(
                io.BytesIO(svg.encode()),
                media_type="image/svg+xml",
                headers={"Content-Disposition": "attachment; filename=canvas.svg"}
            )
        
        # For PNG, PDF, DXF - would need additional libraries
        else:
            raise HTTPException(
                status_code=501,
                detail=f"Export to {request.format.value} requires additional backend support"
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def generate_svg(objects: List[CanvasObject], width: int, height: int, bg_color: str) -> str:
    """Generate SVG from objects"""
    svg_elements = []
    
    for obj in objects:
        if obj.type == ObjectType.PATH and obj.points:
            d = f"M {' L '.join([f'{p.x},{p.y}' for p in obj.points])}"
            svg_elements.append(
                f'<path d="{d}" stroke="{obj.stroke_color}" stroke-width="{obj.stroke_width}" fill="none"/>'
            )
        
        elif obj.type == ObjectType.RECTANGLE:
            svg_elements.append(
                f'<rect x="{obj.x}" y="{obj.y}" width="{obj.width}" height="{obj.height}" '
                f'stroke="{obj.stroke_color}" stroke-width="{obj.stroke_width}" '
                f'fill="{obj.fill_color if obj.fill_color != "transparent" else "none"}"/>'
            )
        
        elif obj.type == ObjectType.ELLIPSE:
            cx = obj.x + (obj.width or 0) / 2
            cy = obj.y + (obj.height or 0) / 2
            rx = (obj.width or 0) / 2
            ry = (obj.height or 0) / 2
            svg_elements.append(
                f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
                f'stroke="{obj.stroke_color}" stroke-width="{obj.stroke_width}" '
                f'fill="{obj.fill_color if obj.fill_color != "transparent" else "none"}"/>'
            )
        
        elif obj.type == ObjectType.LINE:
            svg_elements.append(
                f'<line x1="{obj.x1}" y1="{obj.y1}" x2="{obj.x2}" y2="{obj.y2}" '
                f'stroke="{obj.stroke_color}" stroke-width="{obj.stroke_width}"/>'
            )
        
        elif obj.type == ObjectType.TEXT and obj.text:
            svg_elements.append(
                f'<text x="{obj.x}" y="{obj.y}" fill="{obj.stroke_color}" '
                f'font-size="{obj.font_size}" font-family="{obj.font_family}">{obj.text}</text>'
            )
        
        elif obj.type == ObjectType.WALL:
            svg_elements.append(
                f'<line x1="{obj.x1}" y1="{obj.y1}" x2="{obj.x2}" y2="{obj.y2}" '
                f'stroke="{obj.stroke_color}" stroke-width="{obj.thickness or 8}"/>'
            )
    
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="{bg_color}"/>
  {chr(10).join(svg_elements)}
</svg>'''


# ═══════════════════════════════════════════════════════════════
# TEMPLATE ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/templates/floor-plan")
async def generate_floor_plan(template: FloorPlanTemplate):
    """Generate floor plan objects from a template"""
    objects = []
    offset_x = 100
    offset_y = 100
    scale_px = 50 * template.scale  # 1 meter = 50 pixels at scale 1.0
    
    for room in template.rooms:
        w = room.width * scale_px
        h = room.height * scale_px
        
        # Room walls (rectangle)
        objects.append(CanvasObject(
            type=ObjectType.RECTANGLE,
            x=offset_x,
            y=offset_y,
            width=w,
            height=h,
            stroke_color="#64748b",
            stroke_width=6,
            fill_color="transparent",
            layer_id="cad",
        ))
        
        # Room label
        objects.append(CanvasObject(
            type=ObjectType.TEXT,
            text=room.name,
            x=offset_x + w / 2 - 30,
            y=offset_y + h / 2,
            font_size=14,
            stroke_color="#94a3b8",
            layer_id="text",
        ))
        
        # Doors
        if room.doors:
            for i, door in enumerate(room.doors):
                door_x = offset_x if door.get("position") == "left" else offset_x + w - 40
                objects.append(CanvasObject(
                    type=ObjectType.DOOR,
                    x=door_x,
                    y=offset_y + h / 2 - 20,
                    width=40,
                    stroke_color="#22c55e",
                    layer_id="cad",
                ))
        
        offset_x += w + 50
    
    return {"objects": [obj.model_dump() for obj in objects]}


@router.post("/templates/flowchart")
async def generate_flowchart(template: FlowchartTemplate):
    """Generate flowchart objects from a template"""
    objects = []
    
    for node in template.nodes:
        # Node shape
        if node.shape == "diamond":
            objects.append(CanvasObject(
                type=ObjectType.RECTANGLE,
                x=node.x - 40,
                y=node.y - 25,
                width=80,
                height=50,
                stroke_color="#f59e0b",
                stroke_width=2,
                layer_id="diagram",
            ))
        elif node.shape == "ellipse":
            objects.append(CanvasObject(
                type=ObjectType.ELLIPSE,
                x=node.x - 50,
                y=node.y - 20,
                width=100,
                height=40,
                stroke_color="#8b5cf6",
                stroke_width=2,
                layer_id="diagram",
            ))
        else:
            objects.append(CanvasObject(
                type=ObjectType.RECTANGLE,
                x=node.x - 50,
                y=node.y - 20,
                width=100,
                height=40,
                stroke_color="#8b5cf6",
                stroke_width=2,
                layer_id="diagram",
            ))
        
        # Node label
        objects.append(CanvasObject(
            type=ObjectType.TEXT,
            text=node.label,
            x=node.x - 40,
            y=node.y + 5,
            font_size=12,
            stroke_color="#e2e8f0",
            layer_id="text",
        ))
    
    # Connections
    node_map = {n.id: n for n in template.nodes}
    for conn in template.connections:
        from_node = node_map.get(conn.from_id)
        to_node = node_map.get(conn.to_id)
        if from_node and to_node:
            objects.append(CanvasObject(
                type=ObjectType.ARROW,
                x1=from_node.x,
                y1=from_node.y + 25,
                x2=to_node.x,
                y2=to_node.y - 25,
                stroke_color="#6366f1",
                stroke_width=2,
                layer_id="diagram",
            ))
    
    return {"objects": [obj.model_dump() for obj in objects]}


# ═══════════════════════════════════════════════════════════════
# AI ASSIST ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/ai/status")
async def get_ai_status():
    """Get AI assist status"""
    return {
        "success": True,
        "enabled": canvas_ai_assist.enabled,
        "mode": "observer-assistant"
    }

@router.post("/ai/enable")
async def enable_ai():
    """Enable AI assist"""
    canvas_ai_assist.enabled = True
    return {"success": True, "enabled": True}

@router.post("/ai/disable")
async def disable_ai():
    """Disable AI assist"""
    canvas_ai_assist.enabled = False
    return {"success": True, "enabled": False}

@router.post("/ai/discuss")
async def ai_discuss(request: DiscussRequest):
    """AI-assisted discussion"""
    if not canvas_ai_assist.enabled:
        raise HTTPException(status_code=400, detail="AI assist is disabled")
    return canvas_ai_assist.discuss(request.topic, request.position, request.snapshot, request.context_objects)

@router.post("/ai/draw")
async def ai_draw(request: DrawRequest):
    """AI-assisted drawing"""
    if not canvas_ai_assist.enabled:
        raise HTTPException(status_code=400, detail="AI assist is disabled")
    return canvas_ai_assist.draw(request.description, request.position, request.snapshot, request.context_objects)

@router.post("/ai/plan")
async def ai_plan(request: PlanRequest):
    """AI-assisted planning"""
    if not canvas_ai_assist.enabled:
        raise HTTPException(status_code=400, detail="AI assist is disabled")
    return canvas_ai_assist.plan(request.goal, request.steps, request.position, request.snapshot, request.context_objects)

@router.post("/ai/design")
async def ai_design(request: DesignRequest):
    """AI-assisted design"""
    if not canvas_ai_assist.enabled:
        raise HTTPException(status_code=400, detail="AI assist is disabled")
    return canvas_ai_assist.design(request.design_type, request.specs, request.position, request.snapshot, request.context_objects)

@router.post("/ai/brainstorm")
async def ai_brainstorm(request: BrainstormRequest):
    """AI-assisted brainstorming"""
    if not canvas_ai_assist.enabled:
        raise HTTPException(status_code=400, detail="AI assist is disabled")
    return canvas_ai_assist.brainstorm(request.central_idea, request.branches, request.position, request.snapshot, request.context_objects)

@router.post("/ai/annotate")
async def ai_annotate(request: AnnotateRequest):
    """AI-assisted annotation"""
    if not canvas_ai_assist.enabled:
        raise HTTPException(status_code=400, detail="AI assist is disabled")
    return canvas_ai_assist.annotate(request.target, request.note, request.position, request.snapshot, request.context_objects)

@router.post("/ai/ask")
async def ai_ask(request: AskRequest):
    """AI-assisted question asking"""
    if not canvas_ai_assist.enabled:
        raise HTTPException(status_code=400, detail="AI assist is disabled")
    return canvas_ai_assist.ask_question(request.question, request.options, request.position, request.snapshot, request.context_objects)


# ═══════════════════════════════════════════════════════════════
# UTILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Agent Amigos Chalk Board",
        "sessions_count": len(state_manager.sessions),
    }
