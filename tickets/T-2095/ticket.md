---
id: T-2095
title: A scope narrowing in a worktree is invisible to the fleet until land, so releasing
  a lease cannot unblock anyone
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given ticket A narrows its scope in its worktree to release path P, when ticket
    B whose scope needs only P runs frob ticket start, then B starts successfully
    without waiting for A to land -- this test MUST fail against current main
  evidence: []
- text: given a narrowing is published, when main and the worktree copies are compared,
    then no worktree has written main ticket file directly and the shared root is
    not left dirty
  evidence: []
- text: given ticket A WIDENS its scope in its worktree, when the fleet reads leases,
    then the widening does NOT silently take effect by the same path -- only narrowing
    is monotone-safe and only narrowing may use it
  evidence: []
threat: null
component: tickets
labels:
- fleet-blocking
anchor: false
anchor_reason: null
---
## The defect

`frob ticket scope <id> --remove` performed inside a worktree writes only
that worktree's copy of `tickets/T-####/ticket.md`. The cross-ticket lease
check reads MAIN's copy. So a narrowing does not take effect for any other
agent until the ticket LANDS.

Narrowing scope is precisely the action an agent takes to unblock others. It
is the one action that cannot reach them.

## Measured evidence, captured live

T-2079's agent narrowed early in its work and told me so. At that moment:

    # main's copy of tickets/T-2079/ticket.md
    scope:
    - src/frob/tickets/**
    - src/frob/app/ticket_runner/**
    scope_breadth_ack: false

    # .claude/worktrees/t-2079's copy of the same file
    scope:
    - docs/modules/tickets.md
    - src/frob/tickets/_leases.py
    - src/frob/tickets/_store.py
    - src/frob/tickets/_models.py
    - tests/test_ticket_ownership_guard.py

Consequence: T-2093 -- CRITICAL, a poll loop in `refuse_if_land_in_progress`
that runs on the live dispatch path and can hang any `frob ticket` verb --
could not `ticket start` at all. Its agent read the broad scope, correctly
refused to force past the lease per the playbook, and stopped. It reported
`src/frob/app/ticket_runner/**` as blocking it, a glob T-2079 had already
removed and never needed.

I then chased T-2079's agent about its scope. It pushed back with the actual
list and was right. Both of us were reading a real file; they were different
files.

## Second, independent occurrence the same day

T-1669 declared `src/frob/tickets/**`, `src/frob/app/ticket_runner/**` and
`tests/**`. T-2076 -- critical, fully implemented, evidenced, land-parity
clean with a genuine FAILED_AT_PARENT repro -- was refused with
`CrossTicketLeakage` and recorded `frob ticket block T-2076 --by T-1669`.
T-1669's agent had narrowed HOURS earlier and, by its own account, never
needed `_land.py` at all. The finished critical ticket sat unlandable
anyway.

Two criticals, two different tickets, same mechanism, one day.

## Why "declare narrower scopes" is not the fix

Both dispatch briefs explicitly instructed named paths over `**` globs and
gave the reason. Both agents DID narrow. The narrowing simply had no effect
on anyone else. Briefing harder cannot fix an invisibility problem -- and per
the standing audit rule, when a written rule was followed and the failure
happened anyway, the rule was never the lever.

Note this is the mirror of an already-known asymmetry: narrowing a scope ON
MAIN does not reach a worktree either, because the lease check reads each
worktree's own `ticket.md`. Neither direction propagates. The lease is
computed from whichever copy the reader happens to hold.

## DO NOT FIX IT THIS WAY

- **Do not have the worktree write main's ticket file directly.** That is
  precisely the two-writers-to-one-record hazard the ownership model exists
  to prevent (T-2079's own subject), and it is how a `kind` field was lost.
  Whatever the mechanism, main's copy must stay main's to write.
- **Do not auto-land or auto-commit ledger edits to main from a worktree**
  as a side effect of `scope --remove`. A dirty or concurrently-written root
  DirtyMain-blocks every land in the fleet; this session already lost a
  finished ticket's land that way.
- **Do not make the lease check read every worktree's copy** and union or
  intersect them. That turns one file read into an N-worktree scan on a hot
  path, and it is ambiguous which copy is authoritative when they disagree
  -- which is the actual bug.
- **Do not "solve" it by refusing broad scopes at start.** That is a
  separate, real improvement (T-2094) and it does NOT fix this: a ticket
  that legitimately starts broad and narrows later still cannot publish the
  narrowing.
- **Do not treat a stale `blocked_by` record as self-healing.** T-2076's
  block persisted after its blocker narrowed, and had to be cleared by hand
  via the store API because no unblock verb exists.

## Acceptance direction

The first test must fail against current main: an agent narrows a ticket's
scope in its worktree; a second ticket whose scope overlaps only the REMOVED
paths must then be able to `ticket start`, and today it cannot.

Whatever the mechanism -- publishing scope changes through the same
lease/side-channel the cross-worktree lease check already consults, rather
than through the ticket file; or a narrowing-only fast path that is safe
precisely because it can only RELEASE claims -- note that narrowing is
monotone in the safe direction. Releasing a claim can never create a
conflict, only clear one, which is what makes a narrow-only publication path
tractable where a general one is not.
