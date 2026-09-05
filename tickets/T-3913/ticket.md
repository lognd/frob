---
id: T-3913
title: 'post-land sweep regression from T-3906: 1 new (rule, file) identit(ies), 1
  finding(s) (DEPR003)'
state: queued
kind: bug
origin: agent
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/fmt_runner.py
findings:
- - DEPR003
  - src/frob/app/fmt_runner.py
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
The deferred post-land unscoped sweep (T-1684) for T-3906 at commit 9f0a0051541d9f4930b68103eb63b04b19bb831b found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- DEPR003  src/frob/app/fmt_runner.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DEPR003  src/frob/app/fmt_runner.py  -> attributed to T-3906 (commit 9f0a0051541d, already closed/dropped -- filed below) via src/frob/app/fmt_runner.py::_render_fmt_report

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.