---
id: T-4359
title: Wire proc.stderr into parse_ruff_json's new stderr param in _run_ruff
state: done
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/_python.py
- tests/unit/test_check.py
- tests/system/test_cli_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_check.py
  reason: add regression tests for the ruff stderr wiring (T-4359)
  actor: logan
  at: '2026-09-09'
- op: add
  glob: tests/system/test_cli_check.py
  reason: add regression tests for the ruff stderr wiring (T-4359)
  actor: logan
  at: '2026-09-09'
evidence:
- tests/unit/test_check.py::TestRunRuffToolAbsent::test_missing_ruff_reports_unmeasured
- tests/unit/test_check.py::TestRunRuffToolAbsent::test_unparseable_output_still_errors
- tests/system/test_cli_check.py::TestCheckRuffAbsentFromTargetProject::test_missing_ruff_reports_unmeasured_not_error
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4358 added an optional stderr= param to parse_ruff_json/parse_ruff so the parser can call tool_absent_from_project and report a target-project-absent ruff as UNMEASURED instead of a hard ERROR (T-4354 doctrine). T-4358's own scope was src/frob/process/parsers/ruff.py and ty.py only, so the one real production call site that needs it -- frob.check._python._run_ruff, which currently calls parse_ruff_json(proc.stdout, exit_code=proc.returncode) without stderr -- was left unwired. ty's equivalent caller in the same file already concatenates proc.stdout + proc.stderr before calling parse_ty, so ty needs no change; ruff's caller needs the analogous proc.stderr threaded through as the new stderr= kwarg for the T-4358 fix to actually take effect on the real macOS CI path (the ~14 T-4352-shaped fixture failures). Fix: change the parse_ruff_json call in _run_ruff to pass stderr=proc.stderr, and add/adjust a check/_python.py-level test asserting a fixture project without ruff installed reports UNMEASURED rather than FAIL.