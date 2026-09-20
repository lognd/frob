---
id: T-4559
title: 'post-land sweep regression from T-4495: 3 new (rule, file) identit(ies) (AFFECT001,
  COV002, PERF003)'
state: dropped
kind: bug
origin: agent
created: '2026-09-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_effects.py
- tests/unit/strata/test_selfconform.py
findings:
- - AFFECT001
  - src/frob/strata/_effects.py
- - COV002
  - tests/unit/strata/test_selfconform.py
- - PERF003
  - src/frob/strata/_effects.py
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
The deferred post-land unscoped sweep (T-1684) for T-4495 at commit e4a459f9d1f4e64dbe66b8ab3b9c4d982e8bf9d9 found 3 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- AFFECT001  src/frob/strata/_effects.py
- COV002  tests/unit/strata/test_selfconform.py
- PERF003  src/frob/strata/_effects.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- AFFECT001  src/frob/strata/_effects.py  -> attributed to T-4495 (commit e4a459f9d1f4, already closed/dropped -- filed below) via src/frob/strata/_effects.py::_capability_ratchet_growth_finding -> src/frob/strata/_effects.py::_write_capability_ratchet_lock_entry
- COV002  tests/unit/strata/test_selfconform.py  -> attributed to T-4495 (commit e4a459f9d1f4, already closed/dropped -- filed below) via tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet
- PERF003  src/frob/strata/_effects.py  -> attributed to T-4495 (commit e4a459f9d1f4, already closed/dropped -- filed below) via src/frob/strata/_effects.py::_capability_ratchet_growth_finding -> src/frob/strata/_effects.py::_write_capability_ratchet_lock_entry

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-09-19: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (AFFECT001 src/frob/strata/_effects.py, COV002 tests/unit/strata/test_selfconform.py, PERF003 src/frob/strata/_effects.py) is absent from a direct re-check of exactly the 824 named (rule, file) identit(ies) (not a full sweep) that completed with no failed/silent tool stage at doable's deferred sweep (T-2521: this drop only fires when that measurement itself completed -- no budget deferral, no failed/silent tool stage -- never on an unmeasured or partial run), i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
