# OpenWork Workflow Template: Bugfix Triage

## Purpose

Quickly diagnose and resolve a defect with minimal risk and clear validation.

## When to Use

- User reports a broken feature or error
- Tests are failing and root cause is unknown
- Repro steps are unclear or incomplete

## Inputs

- Error message or screenshot
- Reproduction steps (if any)
- Affected environment (OS, browser, version)
- Recent changes (commits, releases)

## Outputs

- Root cause summary
- Minimal fix (code change)
- Verification evidence (tests/logs)
- Follow-up tasks (if any)

## Suggested Session Prompt

"Triage and fix the reported bug. Reproduce, identify root cause, apply minimal fix, and verify with tests or logs."

## Workflow Steps (Todos)

1. Collect reproduction details and environment.
2. Reproduce the issue locally and capture logs.
3. Identify the smallest failing component or path.
4. Confirm root cause with targeted inspection.
5. Implement minimal fix; avoid unrelated refactors.
6. Add or update a test covering the failure.
7. Verify fix with tests and runtime check.
8. Document impact and any follow-up items.

## Permissions

- Request approval before running destructive or long-running tasks.
- Ask before altering configuration or secrets.

## Notes

- Prefer smallest diff with clear rollback path.
