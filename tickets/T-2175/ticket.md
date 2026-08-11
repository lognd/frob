---
id: T-2175
title: 'release-lease refuses a genuinely orphaned lease and its error message asserts
  ''a process holds it'' when zero processes do: the canned LeaseWorktreeMismatch
  text describes conditions it never checked'
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/worktree_runner.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_leases.py
  reason: repro + fix test for release-lease's holder-dead detection, CLI entry in
    worktree_runner.py
  actor: logan
  at: '2026-08-11'
evidence:
- tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_releases_a_scope_diverged_lease
- tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_releases_an_orphaned_lease
- tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_exits_1_for_a_live_worktree
designated_repro_test: tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_releases_a_scope_diverged_lease
threat: null
component: null
anchor: false
anchor_reason: null
---
