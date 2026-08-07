---
id: T-0563
title: 'RENDER001 straggler burndown: migrate the 14 remaining bare prints (7 runner
  files) and promote the gate to ERROR'
state: done
kind: feature
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_json_mode_prints_json_and_errors_exit_1
- tests/unit/test_app_runners.py::TestGitlogRunner::test_json_mode_prints_json
- tests/test_debt_runner.py::TestDebtRunner::test_json_mode_lists_debt_entries
- tests/test_gates.py::TestRenderLintGate::test_bare_print_fires
designated_repro_test: null
threat: null
component: null
---
T-0459 landed RENDER001 warn-first with 14 bare print/stdout call sites remaining in check_runner, clean_runner, debt_runner, doctor_runner, gitlog_runner, registry_runner, test_runner (exact list in T-0459's Done report). Migrate them to frob.render, then flip RENDER001 to error severity so the output layer cannot rot. Scope: those 7 files + src/frob/gates/_render_lint.py + tests.