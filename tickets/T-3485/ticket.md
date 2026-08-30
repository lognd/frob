---
id: T-3485
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2691):
  1 new (rule, file) identit(ies), 1 finding(s) (DOC006)'
state: done
kind: bug
origin: agent
created: '2026-08-30'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- changelog.d/T-2691.md
- tests/test_docptr_gate.py
findings:
- - DOC006
  - changelog.d/T-2691.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_docptr_gate.py
  reason: adding a regression test pinned to changelog.d/T-2691.md's own DOC006 zero,
    independent of unrelated repo-wide findings
  actor: logan
  at: '2026-08-30'
evidence:
- tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_changelog_d_fragment_doc006_zero
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: bcd838750d2b6cb10c2a4b622e27c02d82fe5162
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2691) at commit 3ee857bfca0f62082e44e49071c9cf8ee4f9c58b found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- DOC006  changelog.d/T-2691.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC006  changelog.d/T-2691.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.