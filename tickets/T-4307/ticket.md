---
id: T-4307
title: Land-format gate belongs to no stage group so --only cannot reach it
state: queued
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
- src/frob/check/__init__.py
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
A GATE ADDED TODAY IS ABSENT FROM EVERY STAGE GROUP, SO NO `--only` INVOCATION CAN
REACH IT AND THE COVERAGE TEST THAT GUARDS EXACTLY THIS IS FAILING.

MEASURED, REPRODUCED LOCALLY AND IN CI. The stage-group coverage test asserts that
every tool and gate name lands in at least one group. It fails with a single extra
item on the left: the land-formatting gate. It is registered in the full gate set
but belongs to no group.

WHY THIS MATTERS BEYOND THE RED TEST, in the test's own words: an agent looping
every listed group must reach full coverage, not a silently-shrinking subset of the
real vocabulary. A gate reachable only by an unscoped run is a gate that
selective runs quietly skip -- the gate still exists, still passes its own unit
tests, and simply never executes on the paths people actually invoke. That is the
same absent-versus-zero confusion this project keeps paying for.

THE FIX IS TO PLACE IT IN THE RIGHT GROUP, NOT TO RELAX THE ASSERTION. Look at
what the existing groups mean and which one this gate genuinely belongs to --
it checks formatting of the current diff at land time, so there is very likely an
existing group whose members do comparable work. Choose by what the group is FOR,
and if no group fits, say so explicitly rather than dropping it into whichever one
is nearest.

THEN LOOK AT THE GENERAL CASE, because this is the second wiring gap from the same
gate's introduction and the cost was a red integration run rather than a caught
mistake at authoring time. Registering a gate and grouping it are two separate
edits, and nothing requires the second. Consider whether group membership can be
made part of declaring a gate rather than a parallel list that must be kept in
sync -- a single source of truth would make this class of omission impossible
instead of merely tested-for. If that is a larger change than this ticket should
carry, file it rather than building it, and record why.

VERIFY by running the named stage-group coverage test to green and quoting the
result, and confirm the gate is reachable by an actual `--only` invocation naming
the group you chose. Other failures in the suite are not yours.
