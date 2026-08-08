---
id: T-1875
title: Orphaned lease outlives in-progress state and frob ticket show reports it over
  the ledger
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
- src/frob/app/ticket_runner/_query.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
A lease file outlived its ticket's in-progress state, and `frob ticket
show` reported the LEASE's view instead of the LEDGER's -- so the tool
displayed a state that contradicted the committed ledger for five hours.

MEASURED, 2026-08-08:

    tickets/T-1820/ticket.md          state: queued
    frob ticket show T-1820           [in-progress@refusal-attrib]
    .git/frob-leases/T-1820.json      recorded_at 10:51:38Z, worktree
                                      .claude/worktrees/refusal-attrib

The `refusal-attrib` worktree's last commit was 07:42; its agent had
been gone for hours. `frob ticket doable` listed T-1820 under "In-flight
(leased, already being worked)" the whole time, and the lease blocked
`src/frob/_cli_parsers/_quality.py` for T-1556, T-1557, T-1584, T-1656
and T-1661. Removing the orphaned lease file made `show` immediately
report `queued` and unblocked all five.

TWO DISTINCT DEFECTS, and the second is the serious one:

1. LEASE NOT RELEASED. A ticket left `in-progress` without its lease
   being cleaned up. Reproduce the exact route before fixing -- likely
   candidates are an agent dying mid-ticket, or a state transition path
   (requeue/anchor/fail) that does not go through the release. Note that
   `frob ticket requeue T-1820` refused with "T-1820 is queued, not
   in-progress", which proves the LEDGER had already moved on while the
   lease had not: the two stores disagreed and nothing detected it.

2. `show` TRUSTS THE LEASE OVER THE LEDGER. This is the part that makes
   a gate lie. The committed ledger is the source of truth for a
   ticket's state; a lease is a local, untracked, best-effort
   coordination artifact in `.git/`. When they disagree, the ledger must
   win and the disagreement must be REPORTED, never silently rendered as
   fact. A queued ticket displayed as in-progress is indistinguishable
   to a coordinator from a ticket someone is actively working -- which
   is exactly why nobody touched it for five hours.

REQUIRED:

- Release the lease on EVERY transition out of `in-progress`, not just
  the land/close happy path. Audit each transition verb.
- Make `frob ticket show` and `doable` read state from the ledger. Where
  a lease exists for a non-in-progress ticket, surface it as an
  INCONSISTENCY ("orphaned lease held by <worktree>, ticket is queued"),
  not as the ticket's state.
- Add a staleness/liveness check so an orphaned lease is detectable
  without a human diffing two stores by hand. T-1739 already built a
  liveness check for `frob worktree sweep`; reuse it rather than writing
  a second one.
- There is still NO wired verb to release a lease -- T-1777 covers that
  gap and is the natural companion fix. The only remedy today is
  deleting a file from `.git/frob-leases/` by hand, which is not a
  workflow anyone should have to discover.

RELATED: T-1868 (scope --add bypasses the lease-conflict check) is the
same subsystem and the same class of failure -- the lease store and the
ledger drifting apart with nothing reconciling them. Coordinate; these
may share a fix site.
