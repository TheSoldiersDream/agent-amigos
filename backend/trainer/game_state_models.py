from typing import List, Optional

from pydantic import BaseModel


class PlayerState(BaseModel):
    health: Optional[int] = None
    ammo: Optional[int] = None
    stamina: Optional[int] = None
    xp: Optional[int] = None
    position: Optional[tuple] = None  # (x, y, z)


class EnemyState(BaseModel):
    id: str
    health: Optional[int] = None
    position: Optional[tuple] = None


class GameWorldState(BaseModel):
    player: PlayerState
    enemies: List[EnemyState] = []
    enemy_count: int = 0


class MemoryWatchItem(BaseModel):
    address: int
    label: Optional[str] = None
    type: str = "int"
    frozen: bool = False


class MemoryWatchList(BaseModel):
    items: List[MemoryWatchItem] = []
