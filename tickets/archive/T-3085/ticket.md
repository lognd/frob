---
id: T-3085
title: 'post-land sweep regression from T-3065, T-3039, T-3060: 1 new (rule, file)
  identit(ies), 0 finding(s) (I001)'
state: done
kind: bug
origin: agent
created: '2026-08-27'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/verify/test_quarantine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'mark as no-behavior-change: lint-only fix'
  actor: logan
  at: '2026-08-27'
  old_length: 1793
  new_length: 177
- mode: set
  reason: restore original Description+plan destroyed by an earlier --set; keep no-behavior-change
    directive
  actor: logan
  at: '2026-08-27'
  old_length: 177
  new_length: 1996
evidence:
- tests/unit/verify/test_quarantine.py::TestNormalizeFindingPath::test_absolute_and_relative_resolve_identical
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 115af6ed64fc07fb4845daf00df66515c43cb643
---
## Description + plan
The deferred post-land unscoped sweep (T-1684) for T-3065, T-3039, T-3060 at commit 2fa632d1998eb953dddd7f70d11eb6a506203c2d found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 0 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- I001  tests/unit/verify/test_quarantine.py

T-2009: 3 lands (T-3065, T-3039, T-3060) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-3065, T-3039, T-3060 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- I001  tests/unit/verify/test_quarantine.py  -> attributed to T-3065 (commit f451ba87465f, already closed/dropped -- filed below) via tests/unit/verify/test_quarantine.py::TestNormalizeFindingPath

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:no-behavior-change reason="pure import-sort reordering (I001 autofix), no behavior change; the bound test proves the import block still resolves correctly, not a bug-repro"