+++
id = "01M3DG64CCYCERCGN8D5E0V6W3"
title = "detect_frameworks only sniffs the repo root: follow workspace members so web families run on monorepos"
type = "bug"
category = "todo"
priority = "low"
parent = "01M2Y1SS0MVHB8M891RN134SE7"
reporter = "agent"
created = "2026-09-26T00:00:00Z"
updated = "2026-10-09T20:42:40Z"
aliases = ["T-6540"]
labels = ["v1-cluster:B2", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/webapp/__init__.py", "src/frob/lang/_project_detect.py", "tests/unit/test_webapp_workspace_detection.py", "docs/design/crunk.md"]
+++

Source: logand.app-v2 FROBLEMS.md (peer coordinator report, 2026-09-26, frob 0.531.1.dev332). Reproduction lives in that repo (read-only for frob agents); the frob-side positive control must be a fixture here.

F-394: on a workspace monorepo (root package.json `workspaces` + uv `[tool.uv.workspace] members`), `detect_frameworks(Path('.'))` returns an empty set while `frontend/` -> {vite} and `backend/` -> {fastapi}; a11y and compliance report 0.00s and zero WEBSEC/A11Y ids in 9945 lines -- the families are silently off for exactly the polyglot layout they target. Deliver: detection walks npm `workspaces`, pnpm-workspace.yaml, uv/pyproject workspace members and `[refs.entrypoint]` dirs, runs each family per member with the member as root, and the summary names the members it scanned; positive control: a two-member fixture repo yields both frameworks and a planted finding in each.
