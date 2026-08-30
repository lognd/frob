---
id: T-3432
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3409):
  1 new (rule, file) identit(ies) (DOC006)'
state: done
kind: bug
origin: agent
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/windows-portability.md
findings:
- - DOC006
  - docs/design/windows-portability.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): doc-only fix: docs/design/windows-portability.md''s
    illustrative path.py::symbol_name symref example was shaped like a real file::symbol
    doc pointer, so DOC006 tried to resolve it. Added an inline frob:waive DOC006
    marking it explicitly illustrative (same idiom other docs in this repo already
    use for placeholder shapes) -- no code changed'
  actor: logan
  at: '2026-08-29'
  old_length: 1372
  new_length: 1746
evidence:
- tests/test_docptr_gate.py::TestDoc006Waive::test_waive_suppresses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 81970809889399b9c0eed7ca5e8fe0c09cd048b3
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3409) at commit dbf327edcdd3d3a0648ee932fb65ae8af4910326 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- DOC006  docs/design/windows-portability.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC006  docs/design/windows-portability.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:no-behavior-change reason="doc-only fix: docs/design/windows-portability.md's illustrative path.py::symbol_name symref example was shaped like a real file::symbol doc pointer, so DOC006 tried to resolve it. Added an inline frob:waive DOC006 marking it explicitly illustrative (same idiom other docs in this repo already use for placeholder shapes) -- no code changed"