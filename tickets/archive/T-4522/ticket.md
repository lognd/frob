---
id: T-4522
title: 'flatten single-child verb groups: agent env, claude sync, natives build, narrative
  move, worktree sweep'
state: done
kind: ux
origin: agent
created: '2026-09-16'
priority: low
parent: T-2994
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: v0.534.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_misc.py
- tests/unit/test_cli_single_child_groups.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/_core.py
  reason: collides with T-4523's live lease on _core.py (scaffold pool leaves); agent/worktree
    flattening deferred, narrative parser lives in _root.py/narrative/_cli.py (out
    of scope anyway)
  actor: logan
  at: '2026-09-16'
evidence:
- tests/unit/test_cli_single_child_groups.py::TestClaudeGroupFlattened::test_bare_claude_defaults_to_sync
- tests/unit/test_cli_single_child_groups.py::TestNativesGroupFlattened::test_bare_natives_defaults_to_build
designated_repro_test: null
acceptance:
- text: GIVEN frob agent, frob claude, frob natives, frob narrative, frob worktree
    WHEN invoked without a subverb THEN each runs what its single child ran, and the
    old two-word spelling keeps working as a documented alias for one release
  evidence:
  - tests/unit/test_cli_single_child_groups.py::TestClaudeGroupFlattened::test_bare_claude_defaults_to_sync
  - tests/unit/test_cli_single_child_groups.py::TestNativesGroupFlattened::test_bare_natives_defaults_to_build
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-16: five groups wrap exactly one child, so the group name carries no information (agent env 75 doc refs, natives build 121). Polish, not bloat removal; do after the group-deletion decision ticket.