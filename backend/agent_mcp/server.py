from __future__ import annotations

import inspect
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Mapping

from fastmcp import FastMCP
from fastmcp.tools.tool import Tool, ToolResult
from mcp.types import TextContent

# Fix imports for sibling directories
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

AGENT_AMIGOS_TOOLS = {}
try:
    from agent_init import TOOLS as AGENT_AMIGOS_TOOLS
except Exception as e:
    logging.error(f"Failed to load AGENT_AMIGOS_TOOLS: {e}")
    AGENT_AMIGOS_TOOLS = {}

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = Path(os.environ.get("MCP_LOG_DIR", str(BASE_DIR / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_LEVEL = os.environ.get("MCP_LOG_LEVEL", "WARNING").upper()

def _configure_logging() -> logging.Logger:
    log_path = LOG_DIR / "mcp_server.log"
    level = getattr(logging, LOG_LEVEL, logging.WARNING)

    logger = logging.getLogger("agent_amigos.mcp")
    logger.setLevel(level)
    logger.propagate = False

    # Remove any inherited handlers to prevent stdout/stderr noise.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(file_handler)

    # Quiet down third-party loggers.
    logging.getLogger("fastmcp").setLevel(level)
    logging.getLogger("mcp").setLevel(level)

    return logger


LOGGER = _configure_logging()
TOOLS_SPEC_PATH = BASE_DIR / "tools.json"
DEFAULT_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
}


class AgentTool(Tool):
    """Wrap a callable so FastMCP can execute it."""

    fn: Callable[..., Any]

    async def run(self, arguments: Dict[str, Any]) -> ToolResult:  # type: ignore[override]
        try:
            result = self.fn(**arguments)
            if inspect.isawaitable(result):
                result = await result
        except TypeError as exc:
            raise ValueError(
                f"Tool '{self.name}' received invalid arguments: {exc}. Provided args: {arguments}."
            ) from exc
        except Exception as exc:  # pragma: no cover - tool implementation errors
            LOGGER.exception("Tool '%s' execution failed", self.name)
            return ToolResult(
                content=[TextContent(type="text", text=f"Error: {exc}")],
                structured_content={"success": False, "error": str(exc)},
                meta={"tool": self.name, "status": "error"},
            )

        normalized = _normalize(result)
        text = _format_result(normalized)
        structured = normalized if isinstance(normalized, dict) else None

        return ToolResult(
            content=[TextContent(type="text", text=text)],
            structured_content=structured,
            meta={"tool": self.name, "status": "ok"},
        )


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _normalize(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _format_result(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, indent=2, ensure_ascii=False)
    except TypeError:
        return str(value)


def _load_tool_specs(path: Path) -> Mapping[str, Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Unable to locate MCP tool specification file at {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {entry["name"]: entry for entry in data}


def _register_tools(server: FastMCP) -> None:
    specs = _load_tool_specs(TOOLS_SPEC_PATH)
    
    # VS Code Copilot Chat performs best with <= 128 tools.
    # We will prioritize core tools and cap the total count.
    MAX_TOOLS = 128
    registered_count = 0
    
    # Priority tool sets to register first
    priority_prefixes = ["web_", "scrape_", "google_", "read_", "write_", "screenshot", "click", "type_", "run_"]
    
    sorted_tool_names = sorted(AGENT_AMIGOS_TOOLS.keys(), key=lambda n: not any(n.startswith(p) for p in priority_prefixes))

    for name in sorted_tool_names:
        if registered_count >= MAX_TOOLS:
            LOGGER.warning("Reached MAX_TOOLS limit (128). Skipping remaining implementation tools.")
            break

        func, requires_approval, fallback_description = AGENT_AMIGOS_TOOLS[name]
        spec = specs.get(name)
        if not spec:
            continue

        spec_requires = bool(spec.get("requires_approval", requires_approval))
        description = spec.get("description") or fallback_description or name
        if spec_requires:
            description = f"{description} (requires approval)"

        category = spec.get("category")
        parameters = spec.get("parameters") or {"type": "object"}

        tool = AgentTool(
            name=name,
            description=description,
            parameters=parameters,
            output_schema=DEFAULT_OUTPUT_SCHEMA,
            annotations=None,
            serializer=None,
            tags={category} if category else set(),
            meta={
                "category": category or "general",
                "requiresApproval": spec_requires,
                "source": "Agent Amigos",
            },
            fn=func,
        )
        server.add_tool(tool)
        registered_count += 1

    # ChalkBoard / Plugin tools (only if we have room)
    try:
        from chalkboard import chalkboard_controller
        # fetch chalkboard tool specs
        cb_tools = chalkboard_controller.get_mcp_tools()
        for cb in cb_tools:
            if registered_count >= MAX_TOOLS:
                LOGGER.warning("Reached MAX_TOOLS limit (128). Skipping remaining plugin tools.")
                break

            # Wrap each chalkboard tool into an AgentTool
            _AgentTool = AgentTool
            def _make_fn(_tool_name):
                def _fn(**arguments):
                    # call the chalkboard controller handler
                    return chalkboard_controller.handle_mcp_tool_call(_tool_name, arguments)
                return _fn

            tool = _AgentTool(
                name=cb["name"],
                description=cb.get("description", "ChalkBoard tool"),
                parameters=cb.get("parameters", {"type":"object"}),
                output_schema=DEFAULT_OUTPUT_SCHEMA,
                annotations=None,
                serializer=None,
                tags={cb.get("category") or "chalkboard"},
                meta={"category": cb.get("category", "visual"), "source": "ChalkBoard"},
                fn=_make_fn(cb["name"]),
            )
            server.add_tool(tool)
            registered_count += 1
            LOGGER.info("Registered ChalkBoard MCP tool: %s", cb["name"])
    except Exception:
        # If chalkboard package not available or fails, ignore silently
        pass


def _build_server() -> FastMCP:
    instructions = (
        "Expose Agent Amigos' local-computer automation powers (keyboard, mouse, web, files, media). "
        "Tools generally return JSON describing execution results."
    )
    server = FastMCP(name="Agent Amigos", instructions=instructions, version="1.0.0")
    _register_tools(server)
    return server


SERVER = _build_server()


def run() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio").strip() or "stdio"
    SERVER.run(transport=transport)


if __name__ == "__main__":
    run()
