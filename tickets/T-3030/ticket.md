---
id: T-3030
title: _STAGE_GROUPS missing milestone/env_var_docs/root_asset_dirs/profile_boundary
  gates
state: in-progress
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/__init__.py
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
Found while root-causing T-3019 (spurious REF001/PRE001/SCOPE001 on a
clean project). tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
fails on unmodified main, independently of T-3019's fix:
`_STAGE_GROUPS` (src/frob/check/__init__.py) does not cover 4 gates that
exist in `frob.gates._ALL_GATES`: milestone, env_var_docs,
root_asset_dirs, profile_boundary. An agent looping every listed
`--only` group (the documented pattern for a FROB_AGENT foreground
budget, playbook sec 3b) silently never runs these four gates at all.

Repro: `python -c "from frob.check import _STAGE_GROUPS; from frob.gates
import _ALL_GATES; print(_ALL_GATES - frozenset().union(*_STAGE_GROUPS.
values()))"` from a worktree with natives built.

Out of T-3019's declared scope (src/frob/gates/_refs.py,
src/frob/check/_python.py) -- this is `_STAGE_GROUPS` membership in
src/frob/check/__init__.py, unrelated to the REF001/PRE001/SCOPE001
rules T-3019 owns.
