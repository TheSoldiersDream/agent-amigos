# OpenWork Workflow Template: QA & Validation

## Purpose

Validate functionality against acceptance criteria with a repeatable test checklist.

## When to Use

- Before release
- After a bugfix or refactor
- For regression testing on key flows

## Inputs

- Acceptance criteria
- Test environments
- Known risk areas

## Outputs

- Test checklist and results
- Defects discovered (if any)
- Release readiness assessment

## Suggested Session Prompt

"Validate the changes against acceptance criteria and document results."

## Workflow Steps (Todos)

1. Identify critical user journeys and edge cases.
2. Build a concise test checklist.
3. Run tests and capture evidence (logs/screenshots).
4. Record defects with reproduction steps.
5. Retest after fixes and confirm closure.
6. Provide a release readiness summary.

## Permissions

- Ask before running destructive tests or load tests.

## Notes

- Prefer repeatable checklists for future regressions.
