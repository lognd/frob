---
id: T-2950
title: 'frob status takes 5m41s: an adoption surface nobody will wait for, and it
  exceeds the 200s foreground budget'
state: done
kind: ux
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/status_runner.py
- src/frob/tickets/*ticket_flow*
- tests/test_status.py
- docs/modules/cli.md
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/_cli_parsers/_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/status_runner.py
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/tickets/*ticket_flow*
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_status.py
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/cli.md
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/status_runner.py
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/tickets/*ticket_flow*
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_status.py
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/cli.md
  reason: narrow to frob status hot path per T-2950
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/config.py
  reason: CLI-flag forwarding for --tickets/status_tickets requires touching AppConfig
    and its external-forwarding field list
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/_config_external.py
  reason: CLI-flag forwarding for --tickets/status_tickets requires touching AppConfig
    and its external-forwarding field list
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/_cli_parsers/_status.py
  reason: add --tickets flag to the frob status CLI parser
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_status.py::TestComputeFindingsMovement::test_must_not_invent_missing_baseline
- tests/test_status.py::TestBuildStatusReportIntegration::test_no_baseline_reports_unmeasured_findings
- tests/test_status.py::TestBuildStatusReportIntegration::test_stamped_baseline_with_no_tree_change_is_a_real_zero
- tests/test_status.py::TestRunEndToEnd::test_run_prints_human_text_by_default
- tests/test_status.py::TestRunEndToEnd::test_run_prints_json_when_requested
- tests/test_status.py::TestRunEndToEnd::test_default_cfg_skips_ticket_flow_and_says_so
- tests/test_status.py::TestAddStatusParser::test_registers_status_subcommand_with_expected_flags
- tests/test_status.py::TestAddStatusParser::test_bare_status_has_no_op_defaults
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
