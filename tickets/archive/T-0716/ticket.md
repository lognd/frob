---
id: T-0716
title: 'ticket list: overlay live lease state so worktree-started tickets show in-progress
  on main'
state: done
kind: ux
origin: human
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_live_lease_decorated
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_stale_lease_undecorated
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_ledger_in_progress_undecorated
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_no_root_never_decorates
designated_repro_test: null
acceptance:
- text: GIVEN a queued ticket with a live lease from an existing worktree WHEN frob
    ticket list runs on main THEN it renders in-progress@worktree; GIVEN the lease
    is stale THEN it renders plain queued
  evidence:
  - tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_live_lease_decorated
  - tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_stale_lease_undecorated
  - tests/test_tickets_lease_overlay.py::TestDisplayState::test_ledger_in_progress_undecorated
  - tests/test_tickets_lease_overlay.py::TestDisplayState::test_no_root_never_decorates
threat: null
component: null
---
User observation 2026-07-22: with six tickets actively being worked in agent worktrees, frob ticket list on main showed them all as queued -- start writes the WORKTREE ledger, main only learns state at land. The shared truth for actively-worked is the lease (.git/frob-leases, already consulted by doable to skip claimed tickets) but list ignores it entirely (observed: 1 in-progress in the ledger vs 10 live lease files). Fix by OVERLAY, not write-through (writing main's ledger from worktrees is exactly the corruption class T-0633/T-0682 just fixed): frob ticket list derives display state as ledger-state + live-lease decoration -- a queued ticket with a live, non-stale lease renders as in-progress@<worktree-basename> (distinct marker from ledger-recorded in-progress); stale leases render nothing here (T-0714 moves their diagnostics to check/doctor -- coordinate, do not duplicate). Same overlay for frob ticket show. Tests: fixture with a lease pointing at an existing worktree dir -> decorated; missing dir (stale) -> undecorated.