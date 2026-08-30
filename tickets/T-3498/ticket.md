---
id: T-3498
title: 'macOS-only: scope glob accepts a semicolon-joined entry (bucket E, T-3488)'
state: in-progress
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_tickets.py
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-3498: fix belongs in _first_invalid_scope_glob itself (src/frob/tickets/_models.py),
    the function tests/test_tickets.py::TestScopeGlobValidation exercises'
  actor: logan
  at: '2026-08-30'
body_changes:
- mode: append
  reason: 'T-3498: BUG002 waiver -- test already passes at main on this host''s Python
    3.10'
  actor: logan
  at: '2026-08-30'
  old_length: 1111
  new_length: 1853
evidence:
- tests/test_tickets.py::TestScopeGlobValidation::test_semicolon_joined_entry_is_invalid
- tests/test_tickets.py::TestScopeGlobValidation::test_new_ticket_refuses_a_semicolon_joined_scope
- tests/test_tickets.py::TestScopeGlobValidation::test_every_existing_valid_form_still_passes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while characterizing T-3488's macOS-only CI set (bucket E, 3 tests).

MEASURED (GitHub Actions run 33311990183, macos-latest): 3 tests in
tests/test_tickets.py::TestScopeGlobValidation fail: a ";"-joined scope
entry (e.g. "src/a;src/b") is REFUSED (raises) on Linux but ACCEPTED
(no raise) on macOS -- assertions read "DID NOT RAISE" and
"assert None == 'src/...;src/...'".

Suspected root causes: a shlex/posix-mode difference in how the CLI
splits/validates a --scope argument between platforms, or a glob
library (e.g. pathlib.Path.match / fnmatch / wcmatch) that treats ";"
differently depending on the platform branch it takes (posix vs
non-posix mode). Needs measuring: reproduce the exact scope-validation
call path and diff its behavior on posix=True vs posix=False (shlex),
or whatever glob validator is in play.

Fix shape: the validation must refuse a ";"-joined scope entry
identically on every platform (a scope glob containing ";" is not a
valid single glob and should never silently split/accept) -- this is a
correctness bug, not a genuine platform difference to declare a
boundary around.

frob:waive BUG002 reason="T-3498 fixes a macOS-only defect (T-3488 bucket E): _first_invalid_scope_glob relied solely on pathlib.Path.glob's version-dependent ValueError to reject a ';'-joined scope entry, which raises on this host's Python 3.10 but was measured NOT to raise on macOS CI's own Python (run 33311990183). The designated repro test therefore already passes at main on this Linux/Python-3.10 host and can only genuinely fail-then-pass on the macOS/Python build that exhibits the gap, which this implementer cannot dispatch from a Linux worktree. Evidence is confirmatory-only on this host by the nature of the defect (a version-dependent stdlib validator), not a weak test -- same shape as T-3488/T-3496's own BUG002 waivers."