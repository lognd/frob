---
id: T-4546
title: 'flatten the remaining single-child verb groups: agent env, worktree sweep
  (in _core.py) and narrative move (frob/narrative/_cli.py + _root.py)'
state: queued
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
- src/frob/_cli_parsers/_core.py
- src/frob/narrative/_cli.py
- src/frob/_cli_parsers/_root.py
- tests/unit/test_cli_single_child_groups.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN frob agent, frob worktree, frob narrative WHEN invoked without a subverb
    THEN each runs what its single child ran, the two-word spelling stays as a documented
    alias, and tests/unit/test_cli_single_child_groups.py covers all five groups
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4522 flattened claude and natives; agent env and worktree sweep live in src/frob/_cli_parsers/_core.py (leased by T-4523 at the time) and narrative move's parser is src/frob/narrative/_cli.py wired from _root.py (leased by T-4520). Same mechanism as T-4522: default the dispatch dest to the single child and mirror the child's flags onto the group parser.