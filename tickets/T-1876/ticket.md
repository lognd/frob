---
id: T-1876
title: A lease survives its agent's death with no liveness check, blocking every ticket
  in its scope indefinitely
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
A lease survives the death of the agent holding it, with nothing to
detect or reclaim it, and it blocks every other ticket in its scope
indefinitely.

MEASURED, 2026-08-08:

    .git/frob-leases/T-1820.json   recorded_at 10:51:38Z
                                   worktree .claude/worktrees/refusal-attrib
    refusal-attrib last commit     07:42

The agent had been gone for hours. The lease held
`src/frob/_cli_parsers/_quality.py` and blocked T-1556, T-1557, T-1584,
T-1656 and T-1661 the entire time. `frob ticket doable` listed T-1820
under "In-flight (leased, already being worked)", which is exactly what a
coordinator scanning the queue needs it NOT to say about abandoned work.
Deleting the lease file by hand unblocked all five immediately.

WHAT IS NOT WRONG HERE, stated so nobody "fixes" it: an agent's
in-progress state is committed on ITS OWN BRANCH, while main's ledger
stays `queued` until the land. Confirmed:

    git show sweep-regress:tickets/T-1870/ticket.md   state: in-progress
    tickets/T-1870/ticket.md (on main)                state: queued

So on main the lease file is the ONLY authority for "someone is working
this", and `frob ticket show` rendering `[in-progress@<worktree>]` from
it is correct. Do NOT change that. The lease is load-bearing precisely
because the ledger cannot know yet.

That is also what makes this bug matter: if the lease is the only signal,
a stale lease is indistinguishable from live work, and there is no second
source to cross-check against.

REQUIRED:

1. A liveness check on leases. T-1739 already built one for
   `frob worktree sweep` -- reuse it, do not write a second. The natural
   signal is the holding worktree's last-commit age, which is what a
   human ends up eyeballing anyway.
2. Surface staleness where the decision is made: `frob ticket doable`
   should mark a lease whose worktree looks dead rather than presenting
   it identically to live work. A warning a coordinator sees at dispatch
   time is worth more than a reaper that runs on a schedule.
3. Decide reclamation policy explicitly, and prefer the conservative
   one: FLAG, do not auto-release. Auto-releasing a lease whose agent is
   merely slow would let two worktrees edit the same file, which is the
   exact failure T-1868 is filed against. A loud "this lease looks
   abandoned, here is the command" beats a silent reclaim.
4. Provide that command. There is still no wired verb to release a lease
   -- T-1777 covers exactly this gap. Today the only remedy is deleting
   a file from `.git/frob-leases/` by hand, which is undiscoverable and
   which no documentation mentions.

RELATED: T-1868 (scope --add bypasses the lease-conflict check) is the
same subsystem -- the lease store drifting out of agreement with reality
and nothing reconciling it. Coordinate; these may share a fix site.
Anchor tickets make it worse: T-1820 is a permanent WIRE001 follow_up
anchor that can never legitimately close, so its lease could never be
released by the normal land path no matter how long anyone waited.
