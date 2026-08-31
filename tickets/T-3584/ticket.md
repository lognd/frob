---
id: T-3584
title: flaky JSONDecodeError in test_unpinned_polyglot_runs_python_stage (ubuntu,
  frob check --json empty stdout)
state: in-progress
kind: bug
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'mark no-behavior-change: diagnosability-only fix'
  actor: logan
  at: '2026-08-31'
  old_length: 454
  new_length: 665
evidence:
- tests/system/test_cli_check.py::TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33385515507. tests/system/test_cli_check.py::TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage (ubuntu): json.decoder.JSONDecodeError: Expecting value: line 1 column 1 -- the 'frob check --json' invocation returned empty stdout. Run it 10x locally; if it never fails, make the test print the raw stderr on decode failure (diagnosability, the T-3578 pattern) and treat as CI-transient; if it fails locally, diagnose and fix the actual cause.

frob:no-behavior-change reason="only changes the failure-path error message (json.JSONDecodeError -> AssertionError with returncode/stdout/stderr); does not change the test's pass/fail outcome on a clean run"
