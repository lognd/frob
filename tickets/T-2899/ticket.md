---
id: T-2899
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2361):
  1 new (rule, file) identit(ies), 2 finding(s) (I001)'
state: done
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
- tests/unit/verify/test_backpressure.py
findings:
- - I001
  - /home/logan/projects/frob/tests/unit/verify/test_backpressure.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): I001 (ruff import-sort) is a pure formatting
    fix -- ruff check --fix reordered two local import blocks in test_backpressure.py''s
    new T-2361 test methods; no runtime behavior changed, evidence tests pass identically
    before and after'
  actor: logan
  at: '2026-08-25'
  old_length: 1268
  new_length: 1534
evidence:
- tests/unit/verify/test_backpressure.py::TestEffectiveProfileOrStandard::test_ok_passes_through
- tests/unit/verify/test_backpressure.py::TestEffectiveProfileOrStandard::test_err_falls_back_to_standard
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2361) at commit 7100396e8bf5f1beea1f6697cc29a4386b30b8bc found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- I001  /home/logan/projects/frob/tests/unit/verify/test_backpressure.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- I001  /home/logan/projects/frob/tests/unit/verify/test_backpressure.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:no-behavior-change reason="I001 (ruff import-sort) is a pure formatting fix -- ruff check --fix reordered two local import blocks in test_backpressure.py's new T-2361 test methods; no runtime behavior changed, evidence tests pass identically before and after"