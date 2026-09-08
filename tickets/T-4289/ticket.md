---
id: T-4289
title: the daemon idle-termination change introduced a cyclic lock-acquisition order
  and pushed the file past the size threshold
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/serve/_daemon.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the two lock-acquisition paths in the daemon, when they are examined,
    then the report names them concretely and states whether the reported cycle is
    real before any reordering is done
  evidence: []
- text: given the fix, when the architecture gate runs unscoped, then no cyclic lock-acquisition
    order is reported and the idle-termination behaviour still works as specified
  evidence: []
- text: given the size finding, when it is resolved, then the resolution follows from
    the lock fix or from a real seam in the module rather than from shedding lines
    to clear a threshold
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A CYCLIC LOCK-ACQUISITION ORDER WAS INTRODUCED INTO THE SERVE DAEMON BY
YESTERDAY'S IDLE-TERMINATION CHANGE, AND THE SAME CHANGE PUSHED THE FILE PAST THE
SIZE THRESHOLD. Both were caught by the first self-gate run this tree has ever
completed, on the macos leg.

THE CYCLE IS THE SERIOUS HALF. The architecture gate reports a cyclic
lock-acquisition order between the new last-useful-work lock and the daemon's
pre-existing lock: one path takes them in one order and another path takes them
in the opposite order. That is the textbook precondition for a deadlock, and it
sits in a long-lived background process that other processes wait on. It is not a
style finding.

TREAT THE GATE'S CLAIM AS A HYPOTHESIS AND CONFIRM IT AGAINST THE CODE. Establish
the two acquisition paths concretely and say which functions they are, rather
than reordering statements until the finding stops firing. If the cycle is real,
the fix is a consistent global ordering of the two locks, or the elimination of
one of them -- the tracking this change added may not need a separate lock at
all, since it is recording a timestamp that a single existing lock could already
protect. Prefer removing a lock to ordering two.

THE SIZE FINDING IS SECOND AND SHOULD NOT DRIVE THE DESIGN. The file is now two
lines over the threshold. Do NOT extract a module solely to get under a limit
while a deadlock is unresolved; fix the cycle first and see what the file looks
like afterwards, since removing a lock may remove the lines with it. If a split
is still needed, split at a seam the module actually has rather than at whatever
boundary happens to shed two lines.

CONTEXT WORTH KNOWING. The change that introduced this was itself correct and
requested: the daemon must self-terminate after an idle hour, with idleness
defined by work performed rather than by poll iterations, because an instance was
found running nineteen hours while doing nothing useful. Nothing here argues for
undoing that. The tracking simply needs to be implemented without a second lock
taken in an inconsistent order.

VERIFY BY THE GATE THE JOB RUNS, UNSCOPED. A scoped run proves nothing about the
unscoped total, and this repository has already had a fix reported clean against
a subset of gates that the full run still failed.
