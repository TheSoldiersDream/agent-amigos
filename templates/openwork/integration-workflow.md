# OpenWork Workflow Template: Integration Workflow

## Purpose

Integrate an external system or tool into Agent Amigos with safe defaults and clear validation.

## When to Use

- Adding a new API or SDK
- Wiring a new tool into the agent tool registry
- Connecting external services or MCP servers

## Inputs

- Integration target (name, docs, endpoints)
- Authentication requirements
- Expected data flow and responsibilities
- Success and failure cases

## Outputs

- Integration design summary
- Working implementation with safeguards
- Tests or validation steps
- Updated documentation

## Suggested Session Prompt

"Integrate the external system with clear boundaries, minimal risk, and verified behavior."

## Workflow Steps (Todos)

1. Review integration docs and constraints.
2. Define responsibility boundaries and data flow.
3. Add configuration (env vars, defaults, fallbacks).
4. Implement integration entry points and wrappers.
5. Add logging and error handling.
6. Validate with a smoke test or sample request.
7. Update documentation and usage guidance.
8. List follow-up risks and hardening tasks.

## Permissions

- Request approval before storing secrets.
- Ask before enabling network calls in production.

## Notes

- Prefer feature flags for risky integrations.
