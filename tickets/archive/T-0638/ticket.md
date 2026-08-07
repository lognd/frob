---
id: T-0638
title: 'frob deprecated CLI subcommand: list deprecations with sunset/ticket status'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0576
tier: ticket
sprint: null
scope:
- src/frob/app/**
- src/frob/__main__.py
- README.md
- docs/modules/gates.md
- tests/test_deprecated_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_deprecated_runner.py
  reason: CLI test coverage for the new frob deprecated subcommand, same pattern as
    T-0412/T-0563's tests/test_debt_runner.py
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_deprecated_runner.py::TestDeprecatedRunner::test_json_mode_lists_deprecated_entries
- tests/test_deprecated_runner.py::TestDeprecatedRunner::test_no_deprecations_logs_clean_message
- tests/test_deprecated_runner.py::TestDeprecatedRunner::test_human_mode_reports_past_sunset_status
- tests/test_deprecated_runner.py::TestDeprecatedRunner::test_human_mode_reports_orphaned_status_for_closed_ticket
designated_repro_test: null
acceptance:
- text: GIVEN a repo with frob:deprecated directives WHEN frob deprecated runs THEN
    each deprecation prints with its DEPR status and the README command table includes
    the new command
  evidence:
  - tests/test_deprecated_runner.py::TestDeprecatedRunner::test_json_mode_lists_deprecated_entries
  - tests/test_deprecated_runner.py::TestDeprecatedRunner::test_no_deprecations_logs_clean_message
  - tests/test_deprecated_runner.py::TestDeprecatedRunner::test_human_mode_reports_past_sunset_status
  - tests/test_deprecated_runner.py::TestDeprecatedRunner::test_human_mode_reports_orphaned_status_for_closed_ticket
threat: null
component: null
---
T-0576 landed the frob:deprecated directive and DEPR001-004 gates plus the list_deprecated API, but no CLI surface. Add a frob deprecated subcommand (App/AppConfig runner pattern) listing every deprecation with since/sunset/ticket/status (in-window vs past-sunset vs orphaned), plus the README command-table row and count bump so DOC005 stays green. Was T-0638 (ex-draft, id lost at land) in T-0576's worktree; drafts still do not survive land (T-0637).