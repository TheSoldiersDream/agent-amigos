
try:
    import agent_init
except ImportError:
    print("Could not import agent_init")

from core.tool_registry import get_tool_registry

registry = get_tool_registry()
tools = registry.list_tools()
print(f"Registered tools: {len(tools)}")
if "map_control" in tools:
    print("✅ map_control is registered")
else:
    print("❌ map_control is NOT registered")

metadata = registry.get_tools_metadata()
if "map_control" in metadata:
    print(f"Metadata: {metadata['map_control']}")
