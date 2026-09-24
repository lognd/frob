---
id: T-3067
title: 'Curated landing: preserve the 2-7 real work commits per ticket, squash the
  9-21 bookkeeping commits, classify by paths touched'
state: done
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: strata-vmodel
runs_last: false
milestone: 0.535.0
points: 8
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-3067
branch: t-3067
scope:
- src/frob/tickets/_land_squash.py
- tests/unit/tickets/test_land_squash.py
- docs/guides/landing.md
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: 'curated landing: keep real work commits, squash the rest'
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/tickets/test_land_squash.py
  reason: 'curated landing: keep real work commits, squash the rest'
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/guides/landing.md
  reason: 'curated landing: keep real work commits, squash the rest'
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: cross-link the new docs/guides/landing.md from the existing guides list,
    same REF002-avoidance pattern every other guide entry already uses
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: sprint
  old_value: v0.532.0
  new_value: backlog
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-15'
- field: milestone
  old_value: v0.532.0
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-15'
- field: sprint
  old_value: backlog
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: milestone
  old_value: 1.0.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: sprint
  old_value: null
  new_value: strata-vmodel
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: null
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/unit/tickets/test_land_squash.py::TestIsBookkeepingCommit::test_pure_ticket_ledger_paths_are_bookkeeping
- tests/unit/tickets/test_land_squash.py::TestIsBookkeepingCommit::test_pure_frob_cache_paths_are_bookkeeping
- tests/unit/tickets/test_land_squash.py::TestIsBookkeepingCommit::test_mixed_ledger_and_real_paths_is_not_bookkeeping
- tests/unit/tickets/test_land_squash.py::TestIsBookkeepingCommit::test_pure_source_change_is_not_bookkeeping
- tests/unit/tickets/test_land_squash.py::TestIsBookkeepingCommit::test_empty_path_set_is_not_bookkeeping
- tests/unit/tickets/test_land_squash.py::TestClassifyTicketCommits::test_partitions_real_work_from_bookkeeping_preserving_order
- tests/unit/tickets/test_land_squash.py::TestClassifyTicketCommits::test_empty_input_returns_two_empty_tuples
- tests/unit/tickets/test_land_squash.py::TestClassifyTicketCommits::test_all_real_work_no_bookkeeping
- tests/unit/tickets/test_land_squash.py::TestClassifyTicketCommits::test_all_bookkeeping_no_real_work
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Unblock log
- 2026-09-24: unblocked by T-3053 -- stale edge: T-3053 is the unrelated CAS/update-ref redesign (kernel decoupling); curated landing does not depend on it (measured 2026-09-24)