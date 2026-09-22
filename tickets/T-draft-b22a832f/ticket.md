---
id: T-draft-b22a832f
title: 'post-land sweep regression from T-4645: 4 new (rule, file) identit(ies) (COV002,
  PLACE001)'
state: queued
kind: bug
origin: agent
created: '2026-09-22'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/gates_suite/test_fix_engine.py
- tests/narrative/test_docarch002_fix.py
- tests/ticket_land_suite/test_dirt_ownership.py
- tests/ticket_land_suite/test_wip.py
findings:
- - COV002
  - tests/narrative/test_docarch002_fix.py
- - COV002
  - tests/ticket_land_suite/test_dirt_ownership.py
- - COV002
  - tests/ticket_land_suite/test_wip.py
- - PLACE001
  - tests/gates_suite/test_fix_engine.py
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
The deferred post-land unscoped sweep (T-1684) for T-4645 at commit 0180a356f63196fbb0755af39980abe34763497c found 4 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- COV002  tests/narrative/test_docarch002_fix.py
- COV002  tests/ticket_land_suite/test_dirt_ownership.py
- COV002  tests/ticket_land_suite/test_wip.py
- PLACE001  tests/gates_suite/test_fix_engine.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV002  tests/narrative/test_docarch002_fix.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/ticket_land_suite/test_dirt_ownership.py  -> attributed to T-4645 (commit 0180a356f631, already closed/dropped -- filed below) via tests/ticket_land_suite/test_dirt_ownership.py::TestDirtOwnedByNoOpenTicket
- COV002  tests/ticket_land_suite/test_wip.py  -> attributed to T-4645 (commit 0180a356f631, already closed/dropped -- filed below) via tests/ticket_land_suite/test_wip.py::TestWipCommitNormalizationOnlyDirty
- PLACE001  tests/gates_suite/test_fix_engine.py  -> attributed to T-4694 (commit 27270000ea71, already closed/dropped -- filed below) via tests/gates_suite/test_fix_engine.py::TestFixEngineScopeLease

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.