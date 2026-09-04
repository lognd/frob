---
id: T-3791
title: fix win32 test_cli_test frob-test-cli failures
state: in-progress
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_test.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/*.py tests/system/test_cli_test.py
  reason: correct malformed single-glob scope into a proper entry (test-only ticket,
    no src/frob/app change needed)
  actor: logan
  at: '2026-09-04'
- op: add
  glob: tests/system/test_cli_test.py
  reason: correct malformed single-glob scope into a proper entry (test-only ticket,
    no src/frob/app change needed)
  actor: logan
  at: '2026-09-04'
body_changes:
- mode: append
  reason: 'BUG002 waiver: win32-only PATH-resolution defect, cannot repro on Linux
    CI'
  actor: logan
  at: '2026-09-04'
  old_length: 183
  new_length: 888
evidence:
- tests/system/test_cli_test.py::TestFrobTest::test_all_runs_full_suite
- tests/system/test_cli_test.py::TestFrobTest::test_selects_bound_test_for_touched_symbol
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
win32 CI: tests/system/test_cli_test.py::TestFrobTest::test_all_runs_full_suite and test_selects_bound_test_for_touched_symbol fail. Root cause TBD via winrun. Part of win32 CI drain.

frob:waive BUG002 reason="win32-only defect confirmed via winrun; the test fixture's frob.toml hardcoded command=[\"python\", ...], a bare PATH lookup that resolves to whatever python happens to be first on PATH -- on the win32 runner that resolves to a bare pyenv-style interpreter with no pytest installed, not the venv this suite actually runs under, so the spawned runner failed with 'No module named pytest'. On Linux the first python on PATH already IS the running venv's interpreter, so the pre-fix test also passed at the parent commit. Fixed by pinning the fixture's runner command to sys.executable. No Linux-repro-at-parent-commit test can demonstrate a win32-only PATH-resolution mismatch."
