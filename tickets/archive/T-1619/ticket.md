---
id: T-1619
title: 'Land has no exclusive lease: a concurrent frob ticket new corrupts it mid-staging'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/**
- tests/**
- docs/**
- src/frob/tickets/_land.py
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'TICK009: narrowing my own over-broad filing-time scope to the files this
    ticket actually names'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_land.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_ticket_leases.py
  reason: narrow tests/** and docs/** to the exact files touched by the T-1619 implementation
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/tickets.md
  reason: narrow tests/** and docs/** to the exact files touched by the T-1619 implementation
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_allows_when_no_lock_file
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_refuses_while_land_lock_held
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_allows_after_a_killed_lands_lock_is_os_released
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_belt_and_braces_process_scan_without_the_lock_file
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_concurrent_land_and_ticket_new_cannot_corrupt_the_ledger
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_retire_on_proof_removes_worktree_and_deletes_its_branch
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_worktree_branch_name_returns_none_for_an_unregistered_path
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_delete_worktree_branch_is_a_logged_no_op_for_none
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_retire_on_proof_refuses_and_touches_nothing_when_unverified
designated_repro_test: null
threat: null
component: null
---
A land reads main's working tree at precheck and records main's tip for its unwind path. Any concurrent write to main breaks it, and frob's own commands are the most likely writers:

- Uncommitted edits in main -> the land refuses with DirtyMain, mid-chain.
- A NEW COMMIT on main while the land stages -> tip drift (T-0907), the land refuses to unwind, and it leaves its REL001 version bump STAGED for someone to clean up by hand.

Both happened on 2026-08-05, and the second was caused by `frob ticket new` -- which auto-commits the ledger. So "file a ticket" and "land a ticket" are mutually destructive operations with no interlock between them, and nothing warns you. The operator is expected to just know, which is the same tribal-knowledge failure T-1130 closed for ledger auto-commit.

Fix: a land takes an exclusive repository lease for its duration, and every other ledger-writing verb (new, close, drop, fail, requeue, block, scope, evidence, kind, ...) either refuses with a clear "a land is in progress for T-####, retry after it completes" or waits on it. The lease must be crash-safe -- a killed land cannot leave the repo permanently locked -- which is the same shape as the existing worktree-lease liveness probing (frob.tickets._leases), so reuse that rather than inventing a second mechanism.

Also fix the partial-staging residue: when a land aborts after staging its REL001 bump, it should unstage what it staged, or say exactly what it left behind. Today it prints a refusal and leaves four files staged, and the operator has to work out that `git reset --hard HEAD` is safe only because the land did not complete.

Acceptance: with a land running, `frob ticket new` must not be able to corrupt it -- proven by a test that runs both concurrently.