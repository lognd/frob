---
id: T-3599
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3077):
  2 new (rule, file) identit(ies) (COV003, WIRE002)'
state: queued
kind: bug
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_fix_engine_journal.py
- tests/unit/test_wire001_multiprocessing_target.py
findings:
- - COV003
  - tests/unit/test_wire001_multiprocessing_target.py
- - WIRE002
  - tests/unit/test_fix_engine_journal.py
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3077) at commit 60a5061856048429dc11362b590dd1ab5574ab43 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- COV003  tests/unit/test_wire001_multiprocessing_target.py
- WIRE002  tests/unit/test_fix_engine_journal.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV003  tests/unit/test_wire001_multiprocessing_target.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE002  tests/unit/test_fix_engine_journal.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.