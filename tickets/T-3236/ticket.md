---
id: T-3236
title: 'post-land sweep regression from T-2885: 1 new (rule, file) identit(ies) (OPAQUE001)'
state: done
kind: bug
origin: agent
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_vet_capability.py
findings:
- - OPAQUE001
  - tests/test_vet_capability.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_vet_capability.py::TestLeadingCommentDoesNotDefeatDocstringExclusion::test_leading_comment_then_docstring_prose_stays_quiet
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2885 at commit 70e20f4c2ce96e213be651aad923b89ba00ca1e8 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- OPAQUE001  tests/test_vet_capability.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- OPAQUE001  tests/test_vet_capability.py  -> attributed to T-2885 (commit 70e20f4c2ce9, already closed/dropped -- filed below) via tests/test_vet_capability.py::TestLeadingCommentDoesNotDefeatDocstringExclusion

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.