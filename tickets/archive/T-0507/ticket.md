---
id: T-0507
title: Extend worktree-lease guard to frob release stamp and frob ack
state: done
kind: security
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/release/
- src/frob/app/
- tests/test_release_worktree_lease.py
- tests/test_ack_worktree_lease.py
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_release_worktree_lease.py
  reason: new test files for the extended worktree-lease guard
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_ack_worktree_lease.py
  reason: new test files for the extended worktree-lease guard
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tickets-archive.md
  reason: 'sequential single-worktree dispatch: T-0519''s committed tickets-archive.md
    still shows in the diff-vs-main SCOPE001 check (T-0431 precedent)'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_release_worktree_lease.py::TestStampWorktreeLease::test_mismatched_lease_refuses
- tests/test_release_worktree_lease.py::TestStampWorktreeLease::test_no_lease_succeeds
- tests/test_ack_worktree_lease.py::TestAckWorktreeLease::test_mismatched_lease_refuses
- tests/test_ack_worktree_lease.py::TestAckWorktreeLease::test_no_lease_reaches_normal_ack_failure
designated_repro_test: null
threat: null
component: null
---
