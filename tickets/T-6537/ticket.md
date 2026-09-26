---
id: T-6537
title: 'land: evidence collection runs pytest through the tool venv python; use the
  repo''s own environment or declare pytest a frob dependency'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: critical
parent: T-5630
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
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
- src/frob/tickets/_land_verify.py
- src/frob/testing/_collect.py
- pyproject.toml
- tests/unit/tickets/test_land_evidence_env.py
- docs/modules/tickets-landing.md
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

F-403(a): in a consumer repo, `frob ticket land` logs 'pytest is NOT importable through ~/.local/share/uv/tools/frob/bin/python' at every collection step and treats ALL evidence as unresolved, so no ticket can land. The tool venv is frob's own; pytest lives in the consumer's environment. Coordinator mitigation 2026-09-26: reinstalled the tool with `--with pytest --with pytest-xdist`.

Deliver: (1) evidence collection and re-verification spawn the CONSUMER repo's test runner (`uv run pytest` / the [testing] runner from frob.toml) from the repo root, never `sys.executable`'s venv; (2) if frob must import pytest itself for node-id parsing, declare it in the `serve`/runtime extras so `uv tool install frob` carries it; (3) doctor reports 'pytest not importable in the repo environment' as a REQUIRED tool finding instead of silently unresolving evidence; (4) positive control: a fixture consumer repo whose venv has pytest while the tool python does not resolves its evidence.
