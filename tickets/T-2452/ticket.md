---
id: T-2452
title: _dispatch exceeds ARCH001 line threshold (found while T-2443 touched it)
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/__main__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`src/frob/__main__.py::_dispatch` is already at 81 lines on `main` --
over ARCH001's 60-line threshold (T-2443 discovered this while adding
one small `if argv[0] == "check": ...` branch, which the gate then
attributed to that diff even though the function was already over
threshold beforehand). Split the argv-routing special-cases (bind,
agent, worktree, sync-skills, release publish, refactor) out of
`_dispatch` into smaller per-verb dispatch helpers so the function
itself drops back under 60 lines, mirroring the existing
`_is_quality_bind`/`_is_release_publish` extraction pattern already used
for two of these special cases.
