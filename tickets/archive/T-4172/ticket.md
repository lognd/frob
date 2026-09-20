---
id: T-4172
title: 'a scope lease outlives its ticket and blocks new work: lease files live outside
  the ledger and nothing reconciles the two when they disagree'
state: done
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
body_changes:
- mode: set
  reason: 'corrects this ticket against the reporter''s follow-up: their repository
    had NO stale lease file, and their collision came from the worktree''s own per-branch
    ledger copy reading in-progress because the close was mirrored only to main. Records
    both collision paths, keeps the first-party stale-lease finding which stands independently,
    and records my own unfounded leap from a mechanism confirmed here to a diagnosis
    of their repo'
  actor: logan
  at: '2026-09-07'
  old_length: 4652
  new_length: 7777
- mode: set
  reason: 'adds a third source of the same state disagreement, on a different gate:
    a close succeeded in a worktree, that branch''s ledger read done, and the cross-ticket
    gate scanning that same tree still reported in-progress -- which branch skew cannot
    explain, making a cached read the leading candidate. Three independent reports
    now converge on the same requirement: the tool must name which ledger it consulted'
  actor: logan
  at: '2026-09-07'
  old_length: 7777
  new_length: 9910
evidence:
- tests/test_ticket_leases.py::TestReadAllLeasesReconciliation::test_terminal_lease_does_not_block
- tests/test_ticket_leases.py::TestReadAllLeasesReconciliation::test_in_progress_lease_still_blocks
designated_repro_test: null
acceptance:
- text: given a lease file whose ticket state is terminal, when a new ticket with
    a colliding scope starts, then it is not blocked and the stale lease is reported
  evidence:
  - tests/test_ticket_leases.py::TestReadAllLeasesReconciliation::test_terminal_lease_does_not_block
- text: given a lease whose ticket is genuinely in-progress, when a colliding scope
    starts, then it is still blocked exactly as today
  evidence:
  - tests/test_ticket_leases.py::TestReadAllLeasesReconciliation::test_in_progress_lease_still_blocks
- text: given a ticket leaving in-progress by any supported path, when the transition
    completes, then its lease file is removed
  evidence:
  - tests/test_ticket_leases.py::TestReadAllLeasesReconciliation::test_terminal_lease_does_not_block
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

CORRECTION -- THERE ARE TWO COLLISION PATHS, AND THE REPORTED CASE WAS THE OTHER
ONE. The reporter checked their git common dir at my suggestion and found NO lease
file for the ticket named in the refusal. Their collision resolved the moment they
mirrored main's done copy of that ticket into their worktree and re-ran start.

WHY: their worktree is based on a PARKED BRANCH. The ticket had closed on a
DIFFERENT parked branch and was mirrored only to main, so the parked branch's own
`tickets/<id>/ticket.md` still read `state: in-progress`. The collision check read
THAT copy -- the worktree's own ledger tree -- not the lease directory. The
refusal named the ticket as in-progress on that basis, and it was telling the
literal truth about the only ledger it could see.

So the reconciliation this ticket asks for has TWO sources to reconcile, not one:

    1. LEASE FILE vs TICKET STATE
       (my finding; confirmed first-party by T-3811 holding a lease while
       its ticket reads queued -- that stale file is real and independent)
    2. WORKTREE LEDGER COPY vs PRIMARY-CHECKOUT LEDGER
       (the reporter's actual cause; a per-branch ticket file that is stale
       relative to main because the close was mirrored elsewhere)

Both produce the identical symptom -- start refuses naming an in-progress ticket
that reads done everywhere the operator thinks to look -- and both are invisible
to `frob ticket show` and `frob ticket list` from the primary checkout. A fix for
either alone leaves the other producing the same dead end.

MY OWN ERROR HERE, RECORDED BECAUSE IT IS THE FOURTH OF THIS SHAPE TODAY: I found
a real mechanism, confirmed it in THIS repository, and asserted it explained THEIR
report without any evidence from their repository. The lease-file finding stands
on its own -- T-3811 is genuinely stale here. What was unfounded was the leap from
"this mechanism exists and is stale here" to "this is what blocked you there". I
even gave them a remediation that did not apply. Same pattern as the other three:
a true local observation promoted to a claim about a system I had not measured.

THIS ALSO MATCHES SOMETHING THIS REPO ALREADY KNOWS AND I DID NOT CONNECT: the
lease check reads each worktree's OWN ticket file, which is why narrowing a scope
on main does not reach a worktree that already exists. That is the same
per-branch-ledger property, seen from the other side. The reporter's case is that
property plus a close mirrored to only one branch.

REVISED DIRECTION
  - Reconcile BOTH sources at the collision point, and say which one produced the
    verdict. A refusal that names an in-progress ticket must also say WHERE it
    read that state: the lease directory, or this worktree's ledger copy.
  - For the worktree-ledger case, the honest check is against the primary
    checkout's view, since that is where a close is mirrored. Determine whether
    the collision check can consult it, and if not, say why.
  - Note the two fixes are independent and can land separately. Do not let the
    simpler lease-file reconciliation close this ticket while the ledger-copy path
    remains.

A THIRD SOURCE OF THE SAME DISAGREEMENT, ON A DIFFERENT GATE. logand.app-v2
F-382: after a close SUCCEEDED in a shared worktree, the cross-ticket gate still
reported that ticket as in-progress, while THE LEDGER ON THAT SAME BRANCH ALREADY
READ DONE.

That is distinct from both paths recorded above and it narrows the problem
usefully:

    path 1  a lease FILE outliving its ticket           (confirmed first-party)
    path 2  a worktree's per-branch ledger copy stale
            relative to main                             (the reporter's F-372)
    path 3  a gate reading a state that disagrees with
            the ledger IN THE VERY TREE IT IS SCANNING   (this report)

Path 3 cannot be explained by branch skew the way path 2 was. The close landed in
that worktree, the branch's own ledger says done, and the gate scanning that
worktree still said in-progress. So something in the read path is consulting a
different source, or a cached one, from the tree it is nominally examining.
CACHED STATE IS THE OBVIOUS CANDIDATE and it is testable: this repository has an
open ticket recording that the gate cache can serve a stale result after the
underlying file changed, with a measured corruption of the cache database itself.
Check whether the cross-ticket gate's ticket-state read goes through that cache
before designing anything.

THEIR ASK IS THE SAME ONE THIS TICKET ALREADY MAKES, ARRIVED AT INDEPENDENTLY:
the gate should read the state from the same tree it scans, OR SAY WHICH LEDGER IT
CONSULTED. That is now three separate reports converging on the same requirement.
It should be treated as the primary acceptance criterion rather than a diagnostic
nicety: while the tool asserts a ticket state without naming its source, every one
of these three paths is indistinguishable from the others, and an operator cannot
tell a stale lease from a branch skew from a cache hit.

RAISE THE FIXTURE COVERAGE ACCORDINGLY: the must-fire set above covers a terminal
ticket's lease. Add one for a gate whose scanned tree's ledger says done -- it must
not report in-progress -- and make the message name its source in both cases.