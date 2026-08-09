---
id: T-1889
title: 'post-land sweep regression from T-1885: 1 new error(s) (ARCH001)'
state: done
kind: bug
origin: agent
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/refactor/_verify.py
- docs/commands/refactor.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/commands/refactor.md
  reason: T-1889 fix touches this function's doc anchor and its regression tests
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_refactor.py
  reason: T-1889 fix touches this function's doc anchor and its regression tests
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: tests/test_refactor.py
  reason: 'narrow back: whole-file scope pulled in unrelated symbols; T-1889 only
    needs its own three verify tests, covered via frob:tests directives already, not
    scope closure'
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_refactor.py::TestVerify::test_import_resolution_catches_syntax_error
- tests/test_refactor.py::TestVerify::test_import_resolution_catches_dangling_reference
- tests/test_refactor.py::TestVerify::test_pytest_collect_reports_failure
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1885 at commit 63de87f14c7776731f11eeb926ecb88f9de43a2e found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- ARCH001  src/frob/refactor/_verify.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH001  src/frob/refactor/_verify.py  -> attributed to T-1885 (commit 63de87f14c77, already closed/dropped -- filed below) via src/frob/refactor/_verify.py::verify_import_resolution

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.
frob:no-behavior-change reason="The ARCH001 fix extracts the parse/skip loop out of verify_import_resolution into the private helper _parse_touched_python_files. The public signature, return type and observable behavior of verify_import_resolution are unchanged by construction -- this is a T-1616 structural refactor whose proof is the static ARCH gate no longer reporting the long-function finding, not a behavioral test. The bound evidence therefore correctly PASSES at main as well as at the fix."