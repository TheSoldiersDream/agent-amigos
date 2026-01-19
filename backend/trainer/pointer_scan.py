from typing import List, Optional

from .process_manager import get_attached_process
from .memory_writer import read_memory


def find_pointers(base: int, offset_depth: int = 1) -> List[List[int]]:
    """Very lightweight, best-effort pointer discovery stub.

    In a full trainer this would recursively walk heaps and modules.
    Here we just return a single-level chain rooted at the given base.
    """

    if offset_depth <= 0:
        return []

    return [[base]]


def resolve_pointer_chain(chain: List[int], type: str = "int") -> Optional[int]:
    """Resolve a simple pointer chain and return the final address.

    This delegates actual reading to read_memory; if any step fails,
    None is returned.
    """

    if not chain:
        return None

    current = chain[0]
    for offset in chain[1:]:
        try:
            value = read_memory(current, type)["value"]
        except Exception:
            return None
        current = int(value) + int(offset)

    return current
