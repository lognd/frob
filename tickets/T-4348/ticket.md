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
