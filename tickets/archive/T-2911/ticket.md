---
id: T-2911
title: 'frob status: show movement (burned/promoted/closed) so a large finding count
  does not read as no progress'
state: done
kind: ux
origin: human
created: '2026-08-25'
priority: high
parent: T-2920
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/status.py
- src/frob/app/status_runner.py
- src/frob/_cli_parsers/_status.py
- src/frob/_cli_parsers/_misc.py
- src/frob/__main__.py
- tests/test_status.py
- docs/modules/cli.md
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/status.py
  reason: 'new frob status subcommand: findings/verify/ticket movement summary'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/app/status_runner.py
  reason: 'new frob status subcommand: findings/verify/ticket movement summary'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/_cli_parsers/_status.py
  reason: 'new frob status subcommand: findings/verify/ticket movement summary'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: 'new frob status subcommand: findings/verify/ticket movement summary'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/__main__.py
  reason: 'new frob status subcommand: findings/verify/ticket movement summary'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_status.py
  reason: 'new frob status subcommand: findings/verify/ticket movement summary'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/cli.md
  reason: 'new frob status subcommand: findings/verify/ticket movement summary'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: design/frob.strata
  reason: declare exec capability via for new tests/test_status.py (SELFAUDIT001/SYS100)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: bump exec ratchet ceiling for new test_status.py subprocess call (SYS111)
  actor: logan
  at: '2026-08-26'
triage_changes:
- field: parent
  old_value: null
  new_value: T-2907
  reason: 'T-2907 strata redesign: bootstrap and progress-surface are children of
    the derive-not-declare program'
  actor: logan
  at: '2026-08-25'
- field: parent
  old_value: T-2907
  new_value: T-2920
  reason: 'user corrected the premise: auto-deriving may=/code= makes the ceiling
    equal whatever the code does, defeating the shrink-the-interface purpose; superseded
    by the shrink-only ratchet design'
  actor: logan
  at: '2026-08-25'
evidence:
- tests/test_status.py::TestComputeFindingsMovement::test_must_not_invent_missing_baseline
- tests/test_status.py::TestComputeFindingsMovement::test_must_not_invent_stale_baseline
- tests/test_status.py::TestComputeFindingsMovement::test_must_not_invent_no_current_run
- tests/test_status.py::TestComputeFindingsMovement::test_must_show_healed_and_introduced
- tests/test_status.py::TestComputeFindingsMovement::test_must_show_pure_healing_is_positive_net
- tests/test_status.py::TestComputeFindingsMovement::test_honest_zero_when_nothing_moved
- tests/test_status.py::TestFindingsMovementModel::test_defaults_are_unmeasured_shaped
- tests/test_status.py::TestBuildStatusReportIntegration::test_no_baseline_reports_unmeasured_findings
- tests/test_status.py::TestBuildStatusReportIntegration::test_stamped_baseline_with_no_tree_change_is_a_real_zero
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: d00670e056d3a124ed2211d77c3d5ada33f16601
---
