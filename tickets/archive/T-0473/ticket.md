---
id: T-0473
title: 'scope-lease is worktree-local: frob ticket start in an isolated worktree never
  reaches main, so collision-aware doable (T-0453) is inert across parallel agents'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_leases.py
- src/frob/tickets/__init__.py
- tests/test_tickets_lease.py
- tests/test_ticket_leases_cross_worktree.py
- docs/modules/tickets.md
- tickets.md
- pyproject.toml
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_leases.py
  reason: 'T-0473: shared cross-worktree lease side-channel + doable wiring'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: 'T-0473: shared cross-worktree lease side-channel + doable wiring'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_tickets_lease.py
  reason: 'T-0473: shared cross-worktree lease side-channel + doable wiring'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_ticket_leases_cross_worktree.py
  reason: 'T-0473: shared cross-worktree lease side-channel + doable wiring'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-0473: shared cross-worktree lease side-channel + doable wiring'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tickets.md
  reason: 'T-0473: shared cross-worktree lease side-channel + doable wiring'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: 'T-0473: REL001 minor version bump for the new public frob.tickets._leases
    API'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: 'T-0473: REL001 minor version bump for the new public frob.tickets._leases
    API'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: 'T-0473: uv.lock updates alongside the pyproject.toml version bump'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_ticket_leases_cross_worktree.py::TestGitCommonDir::test_shared_across_linked_worktrees
- tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_lease_written_in_one_worktree_seen_in_another
- tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_doable_in_second_worktree_hides_colliding_ticket
- tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_release_on_close_removes_the_lease
- tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_stale_lease_for_a_removed_worktree_is_skipped
- tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_scope_mutation_refreshes_the_lease
designated_repro_test: null
threat: null
component: null
---
