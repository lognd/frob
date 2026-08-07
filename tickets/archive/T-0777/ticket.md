---
id: T-0777
title: wire resolve_lease pinning into frob check's --ticket resolution entry point
state: dropped
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-0766 added `frob.tickets._leases.resolve_lease(root, ticket_id,
invoking_worktree)`: a pinned, per-ticket lease resolution primitive that
reads exactly one ticket's own lease file (never scans/iterates across all
recorded leases) and fails loudly (`NoLeaseForTicket` /
`LeaseWorktreeMismatch`) instead of ever borrowing a sibling ticket's lease.

Investigation while working T-0766 found that `frob check --ticket T-XXXX`
(src/frob/app/check_runner.py, src/frob/gates/__init__.py's `active_ticket`/
`_resolve_ticket`) currently performs NO cross-worktree lease consultation
at all -- `active_ticket` resolves the ticket id purely from `--ticket` or
the branch name, and `_worktree_guard.enforce_worktree_lease` (the
FROB_WORKTREE env-var check) is wired into `ack_runner.py`, `gates/
_coverage.py`, and `gates/_baseline.py`, but NOT into `check_runner.py` at
all. Neither path currently calls `resolve_lease`.

This ticket did not reproduce the exact T-0695 incident mechanism inside
this codebase's current `check` code path in the time available -- it is
possible the incident predates a since-landed fix, or the actual cross-talk
happened one level up (dispatcher/coordinator tooling outside this repo).
Regardless, `resolve_lease` is a real, useful hardening primitive now
available and should be wired in as defense in depth:

- Call `resolve_lease(root, ticket.id, root)` from `_resolve_ticket`
  (gates/__init__.py) or `check_runner.py` when `--ticket` is explicit,
  and surface a loud, actionable failure (naming `frob ticket start`) if
  it errs, rather than silently proceeding with whatever the local ledger
  says.
- Consider also wiring `enforce_worktree_lease` into `check_runner.py`
  for symmetry with `ack_runner.py`/`gates/_coverage.py`/`gates/
  _baseline.py`, since it is currently the one mutating/gating entry point
  missing it.

Scope: src/frob/app/check_runner.py, src/frob/gates/__init__.py (the
`active_ticket`/`_resolve_ticket` region only).

## Drop reason
- 2026-07-26: already implemented by T-0787: ticket_lease_pin in gates/__init__.py wired via _refuse_ticket_lease_mismatch in check_runner.py run(), with regression coverage in tests/test_tickets_leases.py (verified against main tip c5a13a68) (absorbed by T-0787)