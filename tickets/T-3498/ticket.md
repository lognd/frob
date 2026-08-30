---
id: T-3498
title: 'macOS-only: scope glob accepts a semicolon-joined entry (bucket E, T-3488)'
state: queued
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