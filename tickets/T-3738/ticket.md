---
id: T-3738
title: fix win32 hang in TestWireGate git subprocess calls
state: in-progress
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/gates_suite/test_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 waiver: unreproducible win32-only hang, per T-3730/T-3735 precedent'
  actor: logan
  at: '2026-09-03'
  old_length: 529
  new_length: 1081
evidence:
- tests/gates_suite/test_wire.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 33739420656 (windows): pytest_timeout watchdog stuck at tests/gates_suite/test_wire.py::TestWireGate::test_wire. TestWireGate's raw subprocess.run git calls (add/commit/checkout) had no timeout=, no GIT_TERMINAL_PROMPT=0, and no -c commit.gpgsign=false on commit -- the exact win32 hang class T-3730/T-3735 fixed in tests/system/test_cli_doctor.py (an inherited global commit.gpgsign=true or credential-helper prompt can block a bare git commit forever with no bound). Bound every subprocess.run in this file the same way.

frob:waive BUG002 reason="win32-only hang: reproduces ONLY on the windows-latest CI runner; WSL has no windows to run against, so the designated repro test necessarily passes at the parent commit here the same as at the fix. Fix reasoned from code: every raw git subprocess.run call in TestWireGate now carries timeout=30, GIT_TERMINAL_PROMPT=0, and -c commit.gpgsign=false on commit, removing the same unbound-subprocess/interactive-prompt hang vectors T-3730/T-3735 closed in test_cli_doctor.py. CI is the verifier for the next windows-latest run."