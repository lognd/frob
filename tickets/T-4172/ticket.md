---
id: T-4172
title: 'a scope lease outlives its ticket and blocks new work: lease files live outside
  the ledger and nothing reconciles the two when they disagree'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a lease file whose ticket state is terminal, when a new ticket with
    a colliding scope starts, then it is not blocked and the stale lease is reported
  evidence: []
- text: given a lease whose ticket is genuinely in-progress, when a colliding scope
    starts, then it is still blocked exactly as today
  evidence: []
- text: given a ticket leaving in-progress by any supported path, when the transition
    completes, then its lease file is removed
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A SCOPE LEASE SURVIVES ITS TICKET, AND A CONSUMER IS HARD-BLOCKED BY ONE RIGHT
NOW. Reported as logand.app-v2 F-372: `frob ticket start` refuses a new ticket
because its scope "collides with in-progress T-0056's lease", while T-0056 reads
`done` everywhere queryable -- full done report, land evidence, and no live
worktree. They cannot narrow around the contended file because it is the file the
ticket exists to add, and the playbook forbids the two available workarounds. They
are stopped.

THE MECHANISM IS IN OUR OWN MODULE DOCSTRING, src/frob/tickets/_leases.py. The
lease deliberately does NOT live in the ledger:

    One small JSON file per held ticket id [under the git common dir]
    ... independent of and in addition to the ledger -- `frob.tickets.
    transition` writes/removes it exactly when a ticket enters/leaves
    IN_PROGRESS

That independence is the whole design -- it exists so a lease is visible across
worktrees, which a per-branch ledger file cannot be. The consequence is that
LEASE STATE AND TICKET STATE CAN DISAGREE, and nothing reconciles them. If the
removal does not happen -- a transition through a path that writes state without
calling `transition`, an interrupted land, a failed unlink -- the lease outlives
the ticket forever and no amount of querying the ledger will reveal it, because
the ledger is not where it lives.

FIRST-PARTY CONFIRMATION, MEASURED HERE 2026-09-07. Two lease files exist under
this repository's git common dir, and one is stale:

    T-3799.json   ticket state: in-progress   -- legitimate
    T-3811.json   ticket state: QUEUED        -- STALE

T-3811 holds a scope lease while its ticket is queued. It is not in progress; it
may never have started or may have been requeued. Either way `transition` should
have removed that file and did not. So this is not a consumer-only defect, and
our own fleet status has been reporting those two as "reclaimable" for the entire
session without anyone establishing that one of them is simply wrong.

IT ALSO EXPLAINS TWO LEAKS I HAVE BEEN WORKING AROUND. T-3936 and T-4124 have
both shown as leased-with-no-worktree for hours. I narrowed T-3936's scope by hand
to release a file blocking another ticket, and treated it as a scoping problem.
Given this mechanism, the honest diagnosis may be the same stale-lease bug, and
scope-narrowing was a workaround for it rather than a fix.

THE MESSAGE IS ALSO WRONG, WHICH IS WHAT MAKES IT UNDIAGNOSABLE. The refusal
asserts a ticket is IN-PROGRESS when the ledger says it is done. The check has
both facts available and reports only one of them. Had it said "a lease file
exists for T-0056, whose ticket state is done -- the lease is stale", the
consumer would have had a diagnosis instead of a dead end. That is the third
refusal-message defect this drive: correct to refuse, wrong about why.

WHAT TO DO
  1. RECONCILE LEASE AGAINST TICKET STATE at the point of collision. A lease whose
     ticket is terminal (done or dropped) is stale by definition -- do not block on
     it. This is the fix; everything else is hardening.
  2. Say so in the message when the two disagree, and name the stale file's path
     so it can be removed by hand in the meantime.
  3. Find out HOW the removal is missed. Enumerate every path that takes a ticket
     out of IN_PROGRESS and confirm each goes through `transition`. A land that
     writes terminal state directly would produce exactly this, and this repo has
     a recorded incident of a timed-out land marking a ticket done outside the
     normal path.
  4. Provide a reclaim path that does not require deleting files by hand from the
     git common dir. Fleet status already classifies leases as reclaimable; make
     that actionable rather than descriptive.

MUST-FIRE FIXTURE:   a lease file whose ticket state is terminal does not block a
                     new ticket from starting, and the stale lease is reported.
MUST-STAY-QUIET:     a lease whose ticket genuinely IS in-progress still blocks a
                     colliding scope, exactly as today -- this is the guard's
                     whole purpose and must not be weakened to fix the stale case.
THIRD FIXTURE:       a ticket leaving IN_PROGRESS by any supported path removes
                     its lease file, proven per path rather than for one.

ACCEPTANCE
- Terminal-ticket leases no longer block, and are reported as stale.
- The refusal message names the disagreement and the file when it occurs.
- Every exit path from IN_PROGRESS enumerated and proven to remove the lease.
- A supported reclaim path exists that is not manual file deletion.
- All three fixtures committed.
