---
id: T-4658
title: 'Ids are assigned once at new: renumbering inside a worktree is refused'
state: in-progress
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-4652
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_renumber_v2.py
- tests/unit/test_ids_assigned_once.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.535.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/test_ids_assigned_once.py::test_renumber_refused_inside_worktree
- tests/unit/test_ids_assigned_once.py::test_concurrent_new_allocates_distinct_ids
designated_repro_test: null
acceptance:
- text: Given a checkout under .claude/worktrees/, when a renumber is attempted, then
    it is refused with a named, logged error and the ledger is unchanged.
  evidence:
  - tests/unit/test_ids_assigned_once.py::test_renumber_refused_inside_worktree
- text: 'POSITIVE CONTROL: tests/unit/test_ids_assigned_once.py::test_renumber_refused_inside_worktree
    constructs a worktree-shaped checkout and asserts the refusal. It FAILS on dev
    today (the renumber succeeds and rewrites ids) and passes after this leaf.'
  evidence:
  - tests/unit/test_ids_assigned_once.py::test_renumber_refused_inside_worktree
- text: Given two concurrent `frob ticket new` calls in the root, when both allocate,
    then they receive distinct ids and neither rewrites the other's; tests/unit/test_ids_assigned_once.py::test_concurrent_new_allocates_distinct_ids
    proves it.
  evidence:
  - tests/unit/test_ids_assigned_once.py::test_concurrent_new_allocates_distinct_ids
- text: draft promotion happens only at publish time on dev; the land never renumbers
    inside the worktree
  evidence:
  - tests/unit/test_ids_assigned_once.py::test_renumber_refused_inside_worktree
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Kernel decoupling leaf (LEDGER story). ~2 points.

Measured this week: draft ids were renumbered INSIDE worktrees, and concurrent agents raced each other's renumbers. src/frob/tickets/_new_renumber.py (1807 lines) and _renumber_v2.py (441) can both rewrite an id from any cwd.

Make the rule structural: an id is allocated exactly once, at `frob ticket new`, in the root checkout. Renumbering from inside a worktree is REFUSED with a named error that says so. Draft promotion stays a root/ledger operation (see the sibling promotion leaf).

Log the allocation (id, cwd, root) at INFO and every refusal at WARNING with the detected worktree path.