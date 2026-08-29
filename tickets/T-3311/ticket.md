---
id: T-3311
title: Collapse the three divergent external-tool spawn conventions into one resolution
  helper
state: queued
kind: feature
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_bug_repro.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/refactor/_verify.py
- src/frob/perf/_profile.py
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
T-3276 built the doctor.py inventory/preflight side (ToolCategory, ExternalToolStatus, scan_external_tools, _EXTERNAL_TOOLS) but its declared scope was doctor.py only. The three divergent spawn conventions T-3276 measured are still live: sys.executable -m pytest (gates/_bug_repro.py, CORRECT), uv run pytest (app/ticket_runner/_verify.py), bare pytest --collect-only (refactor/_verify.py), and bare python (perf/_profile.py, T-3268's own fix target). Collapse these into one resolution helper (frob._EXTERNAL_TOOLS-aware, sys.executable-based per T-3268's adopted convention) that every spawn site calls, with a loud typed Result error on a REQUIRED tool's absence. Coordinate with T-3268 if still open.