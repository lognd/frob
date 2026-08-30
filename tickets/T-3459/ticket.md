---
id: T-3459
title: rapid-sweep land-path regression filing still hits WorktreeLeaseViolation under
  a leased agent shell
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3379.

T-3379 fixed the WorktreeLeaseViolation self-deadlock for
`_file_regression_ticket` calls made through `frob.verify._worker.
run_coalesced_verification` (wrapped the filing call in the new
`frob.tickets._worktree_guard.unleased_root_env`).

The SAME class of failure is still reachable through
`frob.app.ticket_runner._rapid_sweep`'s OWN land-path call sites
(currently around lines 3894/3898 in that file, inside the red-batch
handling `frob ticket land` runs synchronously) -- these also call
`_file_regression_ticket(root, ...)` from inside a dispatched agent's
shell, with `FROB_WORKTREE` still ambient and naming that agent's
leased worktree while the filing write targets the shared root.

Candidate fix: wrap those call sites in the same
`frob.tickets._worktree_guard.unleased_root_env()` context manager
T-3379 added, or thread the exemption through `_dispose_to_existing_
duplicate_or_none`'s own `WorktreeLeaseViolation` branch so it retries
under an unleased root instead of falling through to the terminal
"could NOT be filed" log.
