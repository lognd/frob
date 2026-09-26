---
id: T-6540
title: 'detect_frameworks only sniffs the repo root: follow workspace members so web
  families run on monorepos'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: T-5140
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/webapp/__init__.py
- src/frob/lang/_project_detect.py
- tests/unit/test_webapp_workspace_detection.py
- docs/modules/webapp.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Source: logand.app-v2 FROBLEMS.md (peer coordinator report, 2026-09-26, frob 0.531.1.dev332). Reproduction lives in that repo (read-only for frob agents); the frob-side positive control must be a fixture here.

F-394: on a workspace monorepo (root package.json `workspaces` + uv `[tool.uv.workspace] members`), `detect_frameworks(Path('.'))` returns an empty set while `frontend/` -> {vite} and `backend/` -> {fastapi}; a11y and compliance report 0.00s and zero WEBSEC/A11Y ids in 9945 lines -- the families are silently off for exactly the polyglot layout they target. Deliver: detection walks npm `workspaces`, pnpm-workspace.yaml, uv/pyproject workspace members and `[refs.entrypoint]` dirs, runs each family per member with the member as root, and the summary names the members it scanned; positive control: a two-member fixture repo yields both frameworks and a planted finding in each.
