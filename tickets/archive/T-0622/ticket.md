---
id: T-0622
title: 'arch: logging discipline checks (ARCH1xx) -- unlogged error path, unlogged
  boundary, print-as-diagnostic'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0330
tier: ticket
sprint: null
scope:
- src/frob/arch/_logging_checks.py
- docs/modules/arch.md
- tests/unit/test_arch.py
- src/frob/arch/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_models.py
  reason: extend shared ArchCategory for logging-discipline categories (already committed
    on main via f2fa96f3)
  actor: logan
  at: '2026-07-26'
evidence:
- tests/unit/test_arch.py::TestUnloggedErrorPath::test_catch_with_no_nearby_log_call_flagged
- tests/unit/test_arch.py::TestUnloggedErrorPath::test_catch_with_nearby_log_call_not_flagged
- tests/unit/test_arch.py::TestUnloggedBoundary::test_public_entry_point_with_no_log_call_flagged
- tests/unit/test_arch.py::TestUnloggedBoundary::test_boundary_call_with_no_nearby_log_call_flagged
- tests/unit/test_arch.py::TestUnloggedBoundary::test_private_function_not_flagged
- tests/unit/test_arch.py::TestPrintAsDiagnostic::test_print_call_flagged
- tests/unit/test_arch.py::TestPrintAsDiagnostic::test_print_call_in_cli_module_not_flagged
- tests/unit/test_arch.py::TestRunLoggingChecks::test_combines_all_three_checks
designated_repro_test: null
threat: null
component: null
---
unlogged error path: except/raise/return-Err block with no log call inside it. unlogged boundary: public entry point / subprocess call / network call / filesystem call site with no log statement in its immediate scope. print-as-diagnostic: print() call used where a module logger call is expected (not a CLI-output module). Must coincide with strata's observability-of-flow split per CLAUDE.md note -- these checks are logging-IN-CODE only, no runtime/flow correlation. Acceptance: fixture per sub-check; docs updated including the strata/arch boundary note.