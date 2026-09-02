---
id: T-3642
title: 'post-land sweep regression from T-3596: 2 new (rule, file) identit(ies), 2
  finding(s) (LARGE001)'
state: in-progress
kind: bug
origin: agent
created: '2026-09-01'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/_scan.py
- src/frob/refactor/_verify.py
- docs/commands/refactor.md
- tests/test_refactor.py
- src/frob/refactor/_scan_repoint.py
- src/frob/refactor/_verify_import.py
findings:
- - LARGE001
  - src/frob/refactor/_scan.py
- - LARGE001
  - src/frob/refactor/_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/commands/refactor.md
  reason: 'SCOPE002: doc/test coverage closure for the split target packages, plus
    under-captured private-helper call edges into the new sibling modules this LARGE001
    split created'
  actor: logan
  at: '2026-09-01'
- op: add
  glob: tests/test_refactor.py
  reason: 'SCOPE002: doc/test coverage closure for the split target packages, plus
    under-captured private-helper call edges into the new sibling modules this LARGE001
    split created'
  actor: logan
  at: '2026-09-01'
- op: add
  glob: src/frob/refactor/_scan_repoint.py
  reason: 'SCOPE002: doc/test coverage closure for the split target packages, plus
    under-captured private-helper call edges into the new sibling modules this LARGE001
    split created'
  actor: logan
  at: '2026-09-01'
- op: add
  glob: src/frob/refactor/_verify_import.py
  reason: 'SCOPE002: doc/test coverage closure for the split target packages, plus
    under-captured private-helper call edges into the new sibling modules this LARGE001
    split created'
  actor: logan
  at: '2026-09-01'
body_changes:
- mode: append
  reason: 'BUG002 land refusal: this ticket is a pure structural split with no intended
    behavior change, per its own filed nature (LARGE001 post-land-sweep finding);
    mark it explicitly so BUG002 evaluates it correctly'
  actor: logan
  at: '2026-09-01'
  old_length: 1439
  new_length: 1843
evidence:
- tests/test_refactor.py::TestRunSplit::test_split_moves_symbols_and_leaves_reexport_shim
- tests/test_refactor.py::TestVerify::test_check_delta_uses_current_interpreter
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-3596 at commit 4fb806e3d03ec75ad94c7bcbce2a053604b5f8b6 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- LARGE001  src/frob/refactor/_scan.py
- LARGE001  src/frob/refactor/_verify.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- LARGE001  src/frob/refactor/_scan.py  -> attributed to T-3596 (commit 4fb806e3d03e, already closed/dropped -- filed below) via src/frob/refactor/_scan_repoint.py::_bare_name_repoint_op
- LARGE001  src/frob/refactor/_verify.py  -> attributed to T-3596 (commit 4fb806e3d03e, already closed/dropped -- filed below) via src/frob/refactor/_verify.py::_BUILTIN_AND_DUNDER_NAMES

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:no-behavior-change reason="T-3642 is a pure LARGE001 structural split (dogfooding frob refactor split) of _scan.py/_verify.py into sibling modules -- no intended behavior change, only file/symbol relocation with re-export shims for external callers; verified by the full pre-existing tests/test_refactor.py suite staying green (146 passed) after every commit, not a new fail-then-pass repro test."