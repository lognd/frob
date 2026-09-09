---
id: T-4348
title: Orphaned-lock detector reports 153 historical residue findings on a healthy
  tree
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: high
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
- mode: append
  reason: Record the measured breakdown plus the detector's false data-loss claim
    on draft ids
  actor: logan
  at: '2026-09-08'
  old_length: 2785
  new_length: 6113
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE NEW ORPHANED-LOCK DETECTOR FIRES ONE HUNDRED AND FIFTY-THREE TIMES ON ITS
FIRST RUN, WHICH WILL BURY THE ONE SIGNAL IT WAS BUILT TO SURFACE.

MEASURED ON MAIN. Counting lock files whose id has no ticket in either the active
ledger or the archive gives 153. The detector that just landed reports exactly
this class. It was built because a lost ticket left its lock behind as the sole
evidence, and that loss went unnoticed for hours -- so the detector is right and
useful. The problem is the denominator it starts from.

THESE 153 ARE ALMOST CERTAINLY HISTORICAL RESIDUE, NOT LOSSES. The ids arrive in
consecutive blocks and their lock files cluster inside a twelve-minute window one
month ago. A sampled id has no commit anywhere in history -- it was allocated and
never produced a committed ticket. That is the signature of an allocation or
renumbering churn, not of many independent losses, and this repository has a
recorded incident of exactly that shape where a bare renumber rewrote every id at
once. Confirm this before acting on it: sample several ids from different blocks
and check whether any ever existed in git. If some DID exist and were lost, that
is a much more serious finding and this ticket becomes a recovery job -- say so
rather than assuming residue.

WHY THIS MATTERS RATHER THAN BEING COSMETIC. A detector whose first run emits 153
findings teaches its reader to ignore it. That is the same wrong-incentive shape
this project measured with an unwaivable rule earlier today: five implementers
each wrote an excuse into a Done report because the rule's cheapest clearing
action was prose. A signal that fires 153 times on a healthy tree is worse than
no signal, because it looks like coverage.

DECIDE HOW TO SEPARATE PRE-EXISTING RESIDUE FROM A FRESH LOSS, and record the
reasoning. Candidates worth weighing rather than picking the first: an age
threshold, so only a recently-orphaned lock reports; a recorded baseline of known
residue, so anything new stands out; or simply retiring the residue by deleting
locks confirmed to predate a cutover and to have never existed in git. The last is
attractive because it makes the detector's steady state genuinely zero, but it
deletes state -- so only do it against ids you have positively confirmed never
existed, and say how you confirmed it.

THE STEADY STATE SHOULD BE ZERO. Whatever you choose, the goal is that a single
new finding is visible on sight. If the design cannot reach zero on a healthy
tree, say why and what the residual number means.

DO NOT WEAKEN THE DETECTION ITSELF. The fresh-loss case must still report -- that
is the whole point, and it was validated against a real lost id. Verify both
directions after your change: the known residue is silent, and a newly orphaned
lock still reports.



## The residue is benign -- measured, not assumed (coordinator)

The ticket asks whether any orphaned-lock id ever existed in git, because if any
did, this becomes a recovery job rather than a noise problem. Answered by walking
all 153 and checking each against full history (`git log --all -- tickets/<id>`):

    total orphaned locks .................. 153
    never existed in git anywhere ......... 138
    existed at some point .................  15

ALL FIFTEEN of the survivors are `T-draft-*` ids. A draft is promoted to a real
numbered ticket as part of its normal lifecycle, so its draft-id lock is left
behind by design -- expected residue, not loss. One of them even carries a
`-stale-mirror` suffix, which is mirroring bookkeeping rather than a ticket.

SO NO REAL TICKET WAS LOST. This is a reporting-noise problem only, and the
recovery branch of this ticket can be closed off without work.

TWO THINGS THAT FOLLOW, and they shape the fix:

FIRST, the 138 that never existed are the SAME allocate-then-never-write shape
that was fixed today at the creation path (a success line printed before the write
was durable, with a rollback able to delete the just-written directory). These are
its historical instances. Nothing to recover -- there was never any content -- but
it means the steady-state count is a backlog of a defect that is now fixed at
source, which is exactly the kind of residue a baseline or age threshold is FOR.

SECOND, the draft-id class is not residue of a defect at all and will keep
recurring on every promotion. That argues those should not be reported as orphans
in the first place, rather than being swept into a one-time baseline: a rule that
re-accumulates findings during normal operation has not been fixed. Handle the two
classes differently and say how.

Retiring the 138 by deletion is defensible now that they are confirmed to have
never existed -- there is provably no content behind them. If you take that route,
confirm each id individually rather than deleting by date range, and say how you
confirmed it.

### The message itself over-claims, observed live

While appending this note the detector fired against a draft id and reported, in
full:

  "ticket <id> exists in NEITHER the active ledger nor the archive, and its
   per-ticket lock is not held by any live process. This is the forensic signature
   of a ticket lost after `frob ticket new` printed success but the write was later
   rolled back by a concurrent land -- investigate before removing the lock file,
   it is the only remaining evidence of what was lost"

That id is one of the fifteen confirmed above to have EXISTED in git and been
promoted normally. Nothing was lost. So the message states a specific, alarming
conclusion that is false for an entire class of the findings it produces, and it
instructs the reader to investigate before removing the only evidence -- which is
exactly the expensive response the finding does not warrant here.

A detector that names a cause must be right about the cause. Either narrow the
message to what is actually known (a lock exists with no ticket and no live
holder) and let the reader draw the conclusion, or establish the draft-versus-lost
distinction before speaking. The current wording would send someone hunting for
lost work that never existed, 153 times.
