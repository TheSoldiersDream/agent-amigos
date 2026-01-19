# Autonomy Controller

This module implements a persistence-based controller for autonomous actions in the AgentAmigos server.

## How it works

- Stores `agent.config.json` in the project root and writes logs to `logs/autonomous-agent.log`.
- Provides an API to read and update autonomy config via `/agent/autonomy`.
- Provides endpoints to record user consent (`/agent/autonomy/consent`), trigger a kill switch (`/agent/autonomy/kill`), and read logs (`/agent/autonomy/log`).

## Integration

1. Import the `autonomy_controller` in your tool execution code (e.g., in agent_init or tool router).
2. Call `guard_tool_execution(tool_name, details)` before executing the tool to ensure autonomy policy allows it.
3. Use `autonomy_controller.log_action` to log decisions and results.

## Notes

This implementation provides a minimal integration point; you may want to expand mappings in `agent_init.map_tool_to_action` to map tools to categories more accurately for your toolset.
