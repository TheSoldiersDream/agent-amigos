"""
Spatial Reasoning Engine
========================

Plans room layouts, adjacency, orientation BEFORE drawing.
Creates Design Plan Objects that guide execution.

No random sketching allowed.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RoomType(Enum):
    """Standard room types with typical characteristics"""
    LIVING_ROOM = "living_room"
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    DINING = "dining"
    OFFICE = "office"
    GARAGE = "garage"
    UTILITY = "utility"
    BALCONY = "balcony"
    PORCH = "porch"


class Orientation(Enum):
    """Cardinal directions for solar/wind optimization"""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


@dataclass
class Room:
    """Spatial definition of a room"""
    name: str
    type: RoomType
    width: float  # meters
    height: float  # meters
    preferred_orientation: Optional[Orientation] = None
    natural_light: bool = True
    ventilation: bool = True
    adjacency_preferences: List[str] = field(default_factory=list)
    adjacency_constraints: List[str] = field(default_factory=list)
    x: Optional[float] = None  # Canvas coordinates (computed)
    y: Optional[float] = None
    
    def area(self) -> float:
        return self.width * self.height


@dataclass
class Connection:
    """Connection between two rooms (door, opening, etc)"""
    room1: str
    room2: str
    type: str = "door"  # door, opening, hallway
    width: float = 0.9  # meters


@dataclass
class DesignPlan:
    """
    Complete spatial design plan.
    Created by SpatialReasoning, executed by DrawingExecutor.
    """
    goal: str
    rooms: List[Room]
    connections: List[Connection]
    total_area: float
    layout_strategy: str  # "linear", "L-shape", "U-shape", "cluster"
    site_orientation: Orientation
    design_principles: List[str]
    scale: float = 10.0  # pixels per meter
    
    def get_room(self, name: str) -> Optional[Room]:
        """Find room by name"""
        for room in self.rooms:
            if room.name == name:
                return room
        return None


class SpatialReasoning:
    """
    Analyzes design goals and creates spatial plans.
    
    Considers:
    - Room adjacency (kitchen near dining)
    - Orientation (bedrooms away from afternoon sun)
    - Circulation (logical flow through house)
    - Climate adaptation (tropical ventilation, etc)
    """
    
    def __init__(self):
        # Standard room sizes (meters)
        self.typical_sizes = {
            RoomType.LIVING_ROOM: (4.5, 5.0),
            RoomType.BEDROOM: (3.5, 4.0),
            RoomType.KITCHEN: (3.0, 3.5),
            RoomType.BATHROOM: (2.0, 2.5),
            RoomType.DINING: (3.0, 3.5),
            RoomType.OFFICE: (3.0, 3.0),
            RoomType.BALCONY: (2.0, 4.0),
            RoomType.PORCH: (2.0, 3.0),
        }
        
        # Adjacency rules (what should be near what)
        self.adjacency_rules = {
            "kitchen": ["dining", "utility"],
            "dining": ["kitchen", "living_room"],
            "bathroom": ["bedroom"],
            "living_room": ["dining", "porch", "balcony"],
            "bedroom": ["bathroom"],
        }
        
        # Separation rules (what should NOT be adjacent)
        self.separation_rules = {
            "bedroom": ["kitchen", "garage"],
            "living_room": ["bathroom", "utility"],
        }
    
    def analyze_goal(self, goal: str) -> Dict[str, Any]:
        """
        Parse natural language goal into design requirements.
        
        Examples:
        - "2 bedroom tropical house with good airflow"
        - "Small office with separate entrance"
        - "Family home with open kitchen"
        """
        goal_lower = goal.lower()
        
        analysis = {
            "room_requirements": [],
            "special_features": [],
            "climate_type": None,
            "style": None,
            "priorities": []
        }
        
        # Detect room quantities
        if "bedroom" in goal_lower:
            count = self._extract_number(goal_lower, "bedroom")
            for i in range(count):
                analysis["room_requirements"].append({
                    "type": RoomType.BEDROOM,
                    "name": f"Bedroom {i+1}" if count > 1 else "Bedroom"
                })
        
        if "bathroom" in goal_lower:
            count = self._extract_number(goal_lower, "bathroom")
            for i in range(count):
                analysis["room_requirements"].append({
                    "type": RoomType.BATHROOM,
                    "name": f"Bathroom {i+1}" if count > 1 else "Bathroom"
                })
        
        # Standard rooms (usually implied)
        if "bedroom" in goal_lower or "house" in goal_lower:
            analysis["room_requirements"].extend([
                {"type": RoomType.LIVING_ROOM, "name": "Living Room"},
                {"type": RoomType.KITCHEN, "name": "Kitchen"},
            ])
        
        # Special features
        if "airflow" in goal_lower or "ventilation" in goal_lower or "tropical" in goal_lower:
            analysis["special_features"].append("cross_ventilation")
            analysis["climate_type"] = "tropical"
            analysis["priorities"].append("natural_ventilation")
        
        if "open" in goal_lower:
            analysis["special_features"].append("open_plan")
            analysis["priorities"].append("spatial_flow")
        
        if "balcony" in goal_lower or "deck" in goal_lower:
            analysis["room_requirements"].append({
                "type": RoomType.BALCONY,
                "name": "Balcony"
            })
        
        if "office" in goal_lower:
            analysis["room_requirements"].append({
                "type": RoomType.OFFICE,
                "name": "Office"
            })
        
        # Climate detection
        if "tropical" in goal_lower:
            analysis["climate_type"] = "tropical"
        elif "cold" in goal_lower or "winter" in goal_lower:
            analysis["climate_type"] = "cold"
        
        logger.info(f"📋 Goal analysis: {len(analysis['room_requirements'])} rooms, {analysis['special_features']}")
        return analysis
    
    def create_design_plan(self, goal: str) -> DesignPlan:
        """
        Create complete spatial design plan from goal.
        This is the main entry point for spatial reasoning.
        """
        analysis = self.analyze_goal(goal)
        
        # Create room objects
        rooms = []
        for req in analysis["room_requirements"]:
            room_type = req["type"]
            name = req["name"]
            
            # Get typical size for room type
            if room_type in self.typical_sizes:
                width, height = self.typical_sizes[room_type]
            else:
                width, height = 3.5, 3.5
            
            # Apply climate adaptations
            if analysis["climate_type"] == "tropical":
                # Tropical rooms need better ventilation - slightly larger
                width *= 1.1
                height *= 1.1
            
            room = Room(
                name=name,
                type=room_type,
                width=width,
                height=height,
                natural_light=True,
                ventilation=True
            )
            
            # Set adjacency preferences
            room_type_str = room_type.value
            if room_type_str in self.adjacency_rules:
                room.adjacency_preferences = self.adjacency_rules[room_type_str]
            
            # Set separation constraints
            if room_type_str in self.separation_rules:
                room.adjacency_constraints = self.separation_rules[room_type_str]
            
            # Orientation preferences
            if room_type == RoomType.LIVING_ROOM:
                room.preferred_orientation = Orientation.NORTH  # Avoid harsh sun
            elif room_type == RoomType.BEDROOM:
                room.preferred_orientation = Orientation.EAST  # Morning light
            elif room_type == RoomType.KITCHEN:
                room.preferred_orientation = Orientation.EAST  # Morning light for cooking
            
            rooms.append(room)
        
        # Calculate total area
        total_area = sum(room.area() for room in rooms)
        
        # Determine layout strategy
        layout_strategy = self._determine_layout_strategy(rooms, analysis)
        
        # Create connections between rooms
        connections = self._plan_connections(rooms, analysis)
        
        # Assign canvas coordinates
        self._assign_positions(rooms, layout_strategy, analysis)
        
        # Design principles for this plan
        principles = self._extract_design_principles(analysis)
        
        plan = DesignPlan(
            goal=goal,
            rooms=rooms,
            connections=connections,
            total_area=total_area,
            layout_strategy=layout_strategy,
            site_orientation=Orientation.NORTH,
            design_principles=principles
        )
        
        logger.info(f"✓ Created design plan: {len(rooms)} rooms, {total_area:.1f}m², {layout_strategy} layout")
        return plan
    
    def _extract_number(self, text: str, keyword: str) -> int:
        """Extract number before keyword (e.g., '2 bedroom' -> 2)"""
        words = text.split()
        for i, word in enumerate(words):
            if keyword in word and i > 0:
                prev = words[i-1]
                if prev.isdigit():
                    return int(prev)
                # Handle text numbers
                num_map = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
                if prev in num_map:
                    return num_map[prev]
        return 1  # Default to 1 if not specified
    
    def _determine_layout_strategy(self, rooms: List[Room], analysis: Dict) -> str:
        """Decide overall layout strategy based on rooms and features"""
        room_count = len(rooms)
        
        if "open_plan" in analysis["special_features"]:
            return "open_cluster"
        
        if room_count <= 3:
            return "linear"
        elif room_count <= 5:
            return "L-shape"
        else:
            return "cluster"
    
    def _plan_connections(self, rooms: List[Room], analysis: Dict) -> List[Connection]:
        """Plan doors and connections between rooms"""
        connections = []
        
        # Living room connects to most rooms
        living = next((r for r in rooms if r.type == RoomType.LIVING_ROOM), None)
        if living:
            for room in rooms:
                if room != living and room.type != RoomType.BATHROOM:
                    connections.append(Connection(living.name, room.name, "opening"))
        
        # Kitchen connects to dining (if exists)
        kitchen = next((r for r in rooms if r.type == RoomType.KITCHEN), None)
        dining = next((r for r in rooms if r.type == RoomType.DINING), None)
        if kitchen and dining:
            connections.append(Connection(kitchen.name, dining.name, "opening"))
        
        # Each bedroom connects to bathroom
        bedrooms = [r for r in rooms if r.type == RoomType.BEDROOM]
        bathroom = next((r for r in rooms if r.type == RoomType.BATHROOM), None)
        if bathroom:
            for bedroom in bedrooms:
                connections.append(Connection(bedroom.name, bathroom.name, "door"))
        
        return connections
    
    def _assign_positions(self, rooms: List[Room], layout: str, analysis: Dict):
        """Assign canvas coordinates based on layout strategy"""
        canvas_width = 800
        canvas_height = 600
        margin = 50
        scale = 10  # pixels per meter
        
        if layout == "linear":
            x = margin
            y = canvas_height / 2
            for room in rooms:
                room.x = x
                room.y = y - (room.height * scale / 2)
                x += room.width * scale + 10
        
        elif layout == "L-shape":
            # Place main rooms horizontally
            x = margin
            y = canvas_height / 2
            for i, room in enumerate(rooms[:3]):
                room.x = x
                room.y = y
                x += room.width * scale + 10
            
            # Place remaining rooms vertically
            x = margin
            y = canvas_height / 2 + 150
            for room in rooms[3:]:
                room.x = x
                room.y = y
                y += room.height * scale + 10
        
        elif layout == "cluster" or layout == "open_cluster":
            # Grid layout
            cols = 3
            x = margin
            y = margin
            col = 0
            for room in rooms:
                room.x = x
                room.y = y
                x += room.width * scale + 20
                col += 1
                if col >= cols:
                    col = 0
                    x = margin
                    y += room.height * scale + 20
    
    def _extract_design_principles(self, analysis: Dict) -> List[str]:
        """Extract design principles from analysis"""
        principles = []
        
        if "cross_ventilation" in analysis["special_features"]:
            principles.append("Cross ventilation through opposed openings")
        
        if "open_plan" in analysis["special_features"]:
            principles.append("Open spatial flow between living areas")
        
        if analysis["climate_type"] == "tropical":
            principles.append("High ceilings and large windows for tropical climate")
            principles.append("Shaded outdoor spaces")
        
        if "natural_ventilation" in analysis["priorities"]:
            principles.append("Natural airflow prioritized over AC")
        
        return principles
