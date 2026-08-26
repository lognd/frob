---
id: T-2903
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2645):
  1 new (rule, file) identit(ies), 1 finding(s) (WIRE002)'
state: in-progress
kind: bug
origin: agent
created: '2026-08-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_unlanded.py
findings:
- - WIRE002
  - src/frob/tickets/_unlanded.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: measurement showing WIRE002 already fixed by landed T-2914
  actor: logan
  at: '2026-08-26'
  old_length: 1254
  new_length: 1989
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2645) at commit 380581507d2ed8722a553baf5229faf5d108c1d3 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- WIRE002  src/frob/tickets/_unlanded.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- WIRE002  src/frob/tickets/_unlanded.py  -> attributed to T-2645 (commit 1e422acb1ff3, already closed/dropped -- filed below) via src/frob/tickets/_unlanded.py::_SCRATCH_FILE_BY_SUFFIX

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

Measured on current main (worktree HEAD, merged from main) via `frob
check --only wire` (WIRE002): zero WIRE002 findings anywhere in the
repo today, including src/frob/tickets/_unlanded.py.

T-2903's blamed commit (380581507, 2026-08-25 19:32:01, immediately
after T-2645 landed at 1e422acb1, 19:31:02) is real -- T-2645 did
introduce a WIRE001-waived-without-follow_up gap on
_unlanded.py::_remove_scratch_file. But T-2914 ("WIRE002: T-2645's
WIRE001 waiver on _unlanded.py::_remove_scratch_file missing
follow_up", commit 4c5feadc6, landed 2026-08-25 23:30:44) already fixed
exactly this finding, before this triage started. Re-measurement
confirms clean. Dropping as absorbed by the already-landed fix rather
than duplicating it.
