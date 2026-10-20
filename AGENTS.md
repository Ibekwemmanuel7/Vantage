# Vantage repository workflow

## GitHub updates

User preference recorded 20 October 2026: for authorized Vantage implementation
work, commit and push completed, verified code and documentation to GitHub as
part of the task. Do not leave completed changes local-only by default.

- Fetch the remote and inspect branch state before publishing. Use the current
  appropriate branch; use the `codex/` prefix when creating a new branch.
- Stage only task-related changes. Preserve unrelated user work and remote
  commits. Do not force-push or rewrite shared history.
- Keep generated imagery, model binaries, caches, private field/calendar
  records, feedback databases and credentials outside Git. Preserve attribution
  and dataset limitations in published documentation.
- Run checks appropriate to the changes and report the actual commit, branch,
  push result and remaining dependencies. If pushing fails, state that clearly.

This preference authorizes GitHub updates, not public service deployment,
contacting prospective partners or publishing unsupported performance claims.

## Product boundary

Uganda is the active development priority; Texas is deferred and separate.
Vantage does not inherit CropSight code or validation. Forestry stays with
Vepris. Maintain the Lillie US backlink. Do not diagnose causes from imagery
alone or prescribe irrigation.
