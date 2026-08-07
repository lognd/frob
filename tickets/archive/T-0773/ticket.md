---
id: T-0773
title: 'tickets: memoize git-common-dir/lease reads per CLI invocation (dozens of
  identical rev-parse spawns per command)'
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_leases.py
- src/frob/tickets/__init__.py
- tests/test_tickets_leases.py
- tests/system/test_spawn_budget.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/system/test_spawn_budget.py
  reason: T-0773's own ticket text names these two strict-xfail budget locks as an
    explicit land obligation (remove the xfail markers once the memoization fix lands);
    the tests are tagged to this ticket and must be edited as part of it
  actor: logan
  at: '2026-07-23'
evidence:
- tests/system/test_spawn_budget.py::test_ticket_list_spawns_each_argv_at_most_once
- tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once
- tests/system/test_spawn_budget.py::test_ticket_show_spawns_each_argv_at_most_once
- tests/test_tickets_leases.py::TestResolveLease::test_resolves_own_ticket_own_worktree
- tests/test_tickets_leases.py::TestResolveLease::test_never_returns_a_sibling_tickets_lease
- tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_new_lease_file_written_by_a_sibling_process_is_seen_next_call
- tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_lease_file_removed_by_a_sibling_process_is_seen_next_call
- tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_unchanged_lease_file_content_is_reused_from_cache
designated_repro_test: null
acceptance:
- text: GIVEN one frob ticket list/doable/show invocation WHEN it completes THEN git
    rev-parse --git-common-dir was spawned at most once and the lease directory was
    read at most once for that invocation; a regression test counts spawns
  evidence:
  - tests/system/test_spawn_budget.py::test_ticket_list_spawns_each_argv_at_most_once
  - tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once
threat: null
component: null
---
User observation 2026-07-22: a single frob ticket command spawns git rev-parse --git-common-dir dozens of times and re-reads/re-judges every lease file each time (the same stale-lease WARNING printed 4+ times per command). Cause: read_all_leases -> leases_dir -> git_common_dir runs an uncached subprocess per call, and callers (_cross_worktree_leases via doable ordering, display_state per ticket row, sweep/check paths) call read_all_leases repeatedly within one invocation. Fix: memoize git_common_dir per (root) for the process lifetime (safe: the common dir cannot move mid-invocation) and thread one lease snapshot through a single CLI invocation instead of re-reading per ticket. Keep the WARNING-on-stale behavior but emit each stale lease once per invocation.