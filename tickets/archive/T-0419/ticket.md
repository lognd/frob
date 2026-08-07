---
id: T-0419
title: 'frob check TTY UX: live task-list with progress bars (TTY-only, clears on
  completion)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0410
tier: ticket
sprint: null
scope:
- src/frob/app/
- src/frob/check/
- src/frob/logging/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_check.py::TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage
- tests/system/test_cli_check.py::TestCheckPolyglot::test_pinned_check_type_reports_skipped_line
- tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero
- tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta::test_delta_reports_only_new_violation
designated_repro_test: null
threat: null
component: null
---
User UX ask: when frob check runs from a human TTY (isatty), show a LIVE task list with progress bars for the running stages so the human can see what is happening during the slow ~2min run, and have it CLEAR/go-away on completion leaving only the final summary. TTY-ONLY: in non-TTY / piped / CI (not isatty) keep the current plain line-buffered output (no progress bars, no cursor control -- must stay clean for logs/CI capture). Reuse the existing stage set the orchestrator already runs. Do not change the final summary content, only add the ephemeral live progress on TTY.