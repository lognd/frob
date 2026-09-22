---
id: T-5330
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-5204):
  3 new (rule, file) identit(ies) (COV003, TEST001, TICK010)'
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
- .git/frob-leases/T-4645.json
- src/frob/tickets/_leases.py
- tests/test_tickets.py
findings:
- - COV003
  - tests/test_tickets.py
- - TEST001
  - src/frob/tickets/_leases.py
- - TICK010
  - /home/logan/projects/frob/.git/frob-leases/T-4645.json
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-5204) at commit 50cca5b66fdfe13533d9914428b0f145300548f7 found 7 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- COV003  tests/test_tickets.py
- TEST001  src/frob/tickets/_leases.py
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4645.json

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV003  tests/test_tickets.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- FMT001  strata-core/src/graph/vmodel/closure.rs  -> attributed to T-5204 (commit 50cca5b66fdf, already open -- not re-filed) via strata-core/src/graph/vmodel/closure.rs::check_no_orphan_requirements -> strata-core/src/graph/vmodel/closure.rs::closure_reaches_level
- FMT001  strata-core/src/graph/vmodel/mod.rs  -> attributed to T-5204 (commit 50cca5b66fdf, already open -- not re-filed) via strata-core/src/graph/vmodel/mod.rs::v_model_schema
- FMT001  strata-core/src/lib.rs  -> attributed to T-5204 (commit 50cca5b66fdf, already open -- not re-filed) via strata-core/src/lib.rs::propagated_demand_impl -> strata-core/src/lib.rs::DemandEdge
- FMT001  strata-core/src/parse/mod.rs  -> attributed to T-5204 (commit 50cca5b66fdf, already open -- not re-filed) via strata-core/src/parse/mod.rs::parse_source_impl -> strata-core/src/parse/mod.rs::tests.ok
- TEST001  src/frob/tickets/_leases.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4645.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.