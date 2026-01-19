"""
🧠🎨 Agent Amigos Chalk Board - Data Models

Pydantic models for Canvas objects, layers, and sessions.

Created by Darrell Buttigieg (@darrellbuttigieg) #thesoldiersdream
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime
import uuid


class ObjectType(str, Enum):
    """Types of drawable objects"""
    PATH = "path"
    LINE = "line"
    ARROW = "arrow"
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    TEXT = "text"
    IMAGE = "image"
    WALL = "wall"
    DOOR = "door"
    WINDOW = "window"
    DIMENSION = "dimension"


class DrawMode(str, Enum):
    """Drawing modes"""
    SKETCH = "sketch"
    DIAGRAM = "diagram"
    CAD = "cad"
    MEDIA = "media"
    TEXT = "text"


class Point(BaseModel):
    """2D point"""
    x: float
    y: float


class CanvasObject(BaseModel):
    """A single drawable object on the chalk board"""
    id: str = Field(default_factory=lambda: f"obj_{uuid.uuid4().hex[:12]}")
    type: ObjectType
    layer_id: str = "default"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Position & Size
    x: Optional[float] = None
    y: Optional[float] = None
    x1: Optional[float] = None
    y1: Optional[float] = None
    x2: Optional[float] = None
    y2: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    points: Optional[List[Point]] = None
    
    # Style
    stroke_color: str = "#ffffff"
    fill_color: str = "transparent"
    stroke_width: float = 2
    opacity: float = 1.0
    
    # Text properties
    text: Optional[str] = None
    font_size: int = 16
    font_family: str = "Inter, sans-serif"
    
    # Image properties
    image_data: Optional[str] = None
    
    # CAD properties
    thickness: Optional[float] = None
    unit: str = "px"
    
    # Metadata
    author_agent: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class Layer(BaseModel):
    """A layer in the chalk board"""
    id: str = Field(default_factory=lambda: f"layer_{uuid.uuid4().hex[:8]}")
    name: str
    visible: bool = True
    locked: bool = False
    color: str = "#94a3b8"
    order: int = 0


class CanvasState(BaseModel):
    """Complete state of a chalk board session"""
    session_id: str = Field(default_factory=lambda: f"session_{uuid.uuid4().hex[:12]}")
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Canvas state
    objects: List[CanvasObject] = Field(default_factory=list)
    layers: List[Layer] = Field(default_factory=list)
    
    # Viewport
    pan_x: float = 0
    pan_y: float = 0
    zoom: float = 1.0
    
    # Settings
    mode: DrawMode = DrawMode.SKETCH
    grid_enabled: bool = False
    snap_to_grid: bool = False
    grid_size: int = 20
    
    # Metadata
    title: Optional[str] = "Untitled"
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class HistoryEntry(BaseModel):
    """A single entry in the undo/redo history"""
    id: str = Field(default_factory=lambda: f"hist_{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str  # "add", "delete", "update", "clear"
    object_ids: List[str] = Field(default_factory=list)
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None


class SessionHistory(BaseModel):
    """History for a chalk board session"""
    session_id: str
    entries: List[HistoryEntry] = Field(default_factory=list)
    current_index: int = -1
    max_entries: int = 100


# ═══════════════════════════════════════════════════════════════
# AGENT COMMAND MODELS
# ═══════════════════════════════════════════════════════════════

class AgentDrawCommand(BaseModel):
    """Command from an agent to draw on the chalk board"""
    id: str = Field(default_factory=lambda: f"cmd_{uuid.uuid4().hex[:8]}")
    agent_id: str
    action: str  # "draw", "add_text", "add_shape", "clear", "set_mode", "thought"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Draw command specifics
    type: Optional[str] = None  # "floor_plan", "flowchart", "poem", "text_block"
    
    # For floor plans
    rooms: Optional[List[Dict[str, Any]]] = None
    scale: float = 1.0
    
    # For flowcharts
    nodes: Optional[List[Dict[str, Any]]] = None
    connections: Optional[List[Dict[str, Any]]] = None
    
    # For text/poems
    text: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    font_size: Optional[int] = None
    color: Optional[str] = None
    font: Optional[str] = None
    line_height: Optional[int] = None
    
    # For shapes
    shape_type: Optional[str] = None
    props: Optional[Dict[str, Any]] = None
    
    # For mode changes
    mode: Optional[DrawMode] = None
    
    # For thoughts
    thought_text: Optional[str] = None


class AgentCommandResponse(BaseModel):
    """Response after processing an agent command"""
    command_id: str
    status: str  # "success", "error", "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════
# EXPORT MODELS
# ═══════════════════════════════════════════════════════════════

class ExportFormat(str, Enum):
    """Supported export formats"""
    PNG = "png"
    SVG = "svg"
    PDF = "pdf"
    DXF = "dxf"
    JSON = "json"


class ExportRequest(BaseModel):
    """Request to export chalk board content"""
    format: ExportFormat
    objects: List[CanvasObject]
    layers: Optional[List[Layer]] = None
    width: int = 1920
    height: int = 1080
    background_color: str = "#1a1a2e"


class ExportResponse(BaseModel):
    """Response with exported content"""
    format: ExportFormat
    filename: str
    content_type: str
    data: Optional[str] = None  # Base64 encoded for binary formats
    download_url: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# TEMPLATE MODELS
# ═══════════════════════════════════════════════════════════════

class FloorPlanRoom(BaseModel):
    """A room in a floor plan"""
    name: str
    width: float  # in meters
    height: float  # in meters
    doors: Optional[List[Dict[str, str]]] = None  # [{"position": "left"}]
    windows: Optional[List[Dict[str, str]]] = None


class FloorPlanTemplate(BaseModel):
    """Template for generating floor plans"""
    id: str = Field(default_factory=lambda: f"fp_{uuid.uuid4().hex[:8]}")
    name: str
    description: Optional[str] = None
    rooms: List[FloorPlanRoom]
    scale: float = 1.0  # 1 meter = 50 pixels at scale 1.0


class FlowchartNode(BaseModel):
    """A node in a flowchart"""
    id: str
    label: str
    shape: str = "rectangle"  # "rectangle", "ellipse", "diamond"
    x: float
    y: float


class FlowchartConnection(BaseModel):
    """A connection between flowchart nodes"""
    from_id: str = Field(alias="from")
    to_id: str = Field(alias="to")
    label: Optional[str] = None

    class Config:
        populate_by_name = True


class FlowchartTemplate(BaseModel):
    """Template for generating flowcharts"""
    id: str = Field(default_factory=lambda: f"fc_{uuid.uuid4().hex[:8]}")
    name: str
    description: Optional[str] = None
    nodes: List[FlowchartNode]
    connections: List[FlowchartConnection]


# ═══════════════════════════════════════════════════════════════
# AI ASSIST MODELS
# ═══════════════════════════════════════════════════════════════

class DiscussRequest(BaseModel):
    topic: str
    position: Optional[Dict[str, int]] = None
    snapshot: Optional[str] = None  # Base64 encoded image
    context_objects: Optional[List[Dict[str, Any]]] = None

class DrawRequest(BaseModel):
    description: str
    position: Optional[Dict[str, int]] = None
    snapshot: Optional[str] = None  # Base64 encoded image
    context_objects: Optional[List[Dict[str, Any]]] = None

class PlanRequest(BaseModel):
    goal: str
    steps: Optional[List[str]] = None
    position: Optional[Dict[str, int]] = None
    snapshot: Optional[str] = None
    context_objects: Optional[List[Dict[str, Any]]] = None

class DesignRequest(BaseModel):
    design_type: str
    specs: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, int]] = None
    snapshot: Optional[str] = None
    context_objects: Optional[List[Dict[str, Any]]] = None

class BrainstormRequest(BaseModel):
    central_idea: str
    branches: Optional[List[str]] = None
    position: Optional[Dict[str, int]] = None
    snapshot: Optional[str] = None
    context_objects: Optional[List[Dict[str, Any]]] = None

class AnnotateRequest(BaseModel):
    target: str
    note: str
    position: Dict[str, int]
    snapshot: Optional[str] = None
    context_objects: Optional[List[Dict[str, Any]]] = None

class AskRequest(BaseModel):
    question: str
    options: List[str]
    position: Optional[Dict[str, int]] = None
    snapshot: Optional[str] = None
    context_objects: Optional[List[Dict[str, Any]]] = None
