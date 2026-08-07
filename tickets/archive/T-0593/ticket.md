---
id: T-0593
title: 'COV003: T-0583/T-0585 evidence references pytest node ids that do not exist
  in the repo'
state: dropped
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Dropped (2026-07-22): stale-worktree-base artifact -- the flagged COV003 node ids collect cleanly on main (verified by the filing agent after merging main); resolved elsewhere, nothing to do.

Found while working T-draft-f8aabdf0 (REG008 conformance sweep). frob check --ticket flags 6 COV003 errors: T-0583 evidence tests/test_graph.py::TestCallGraph::test_build_call_graph_sees_through_memoize_per_run_wrapper and T-0585 evidence (3 tests in test_logging_module.py/test_render.py) do not resolve to any collected test even after deleting .frob/pytest-collect.json and re-collecting fresh (0 items collected for each). Both tickets are marked done on main. Needs investigation: either the tests were removed/renamed after the ticket closed, or the evidence was recorded without ever actually being collected.

## Failure log
- 2026-07-22 attempt 1: resolved by main's later commits (INV-037..040/test_graph.py/test_logging_module.py additions) merged into this worktree after filing -- the flagged pytest node ids now collect cleanly, was a stale-worktree-base artifact, not a real gap