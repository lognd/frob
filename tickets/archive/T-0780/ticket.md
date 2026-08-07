---
id: T-0780
title: 'security: serve daemon feeds peer-writable lease branch names into git argv
  -- validate + ''--'' terminator'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/_daemon.py
- src/frob/tickets/_leases.py
- tests/test_serve_daemon.py
- tests/test_tickets_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_drops_a_dash_prefixed_branch
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_drops_a_dash_prefixed_worktree
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_still_admits_a_legitimate_branch
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_admits_detached_head_sentinel
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_resolve_lease_treats_an_evil_branch_as_no_lease
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_rejection_is_logged_once_per_process
- tests/test_serve_daemon.py::TestPollRebaseBotLeaseInjectionGuard::test_evil_lease_branch_never_reaches_git_argv
designated_repro_test: null
acceptance:
- text: GIVEN a lease JSON with branch or worktree starting with a dash or containing
    a git-invalid ref shape WHEN read_all_leases loads it THEN the record is rejected
    and logged, never admitted; GIVEN daemon merge-base/merge-tree invocations THEN
    ref operands follow a -- terminator; a regression test injects a crafted evil
    lease and asserts no git call receives it
  evidence:
  - tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_drops_a_dash_prefixed_branch
  - tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_drops_a_dash_prefixed_worktree
  - tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_still_admits_a_legitimate_branch
  - tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_admits_detached_head_sentinel
  - tests/test_tickets_leases.py::TestLeaseShapeValidation::test_resolve_lease_treats_an_evil_branch_as_no_lease
  - tests/test_tickets_leases.py::TestLeaseShapeValidation::test_rejection_is_logged_once_per_process
  - tests/test_serve_daemon.py::TestPollRebaseBotLeaseInjectionGuard::test_evil_lease_branch_never_reaches_git_argv
threat: elevation-of-privilege
component: null
---
Audit M1 (docs/audits/frob-blindspots-2026-07-23.md): poll_rebase_bot passes lease-JSON branch strings verbatim into git merge-base/merge-tree argv with no -- terminator and no ref validation. Any local process able to write under the shared .git common dir (every co-located worktree agent) can drop evil.json with branch='--output=...' and the unattended daemon executes git option injection. Fix both layers: (1) read_all_leases/resolve_lease validate branch/worktree shape (reject leading dash; git check-ref-format-conformant allowlist) and drop+log failures; (2) daemon git calls put -- before ref operands. NOTE: also coordinate with T-0778 (guard wiring) and the M2 lease-TTL ticket -- same files, serialize dispatch.