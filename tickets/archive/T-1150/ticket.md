---
id: T-1150
title: 'strata: frob sys sync-interface -- measure and update interface= attrs mechanically
  (SYS104-mandatory upkeep)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/app/sys_runner.py
- design/frob.strata
- docs/strata/surface.md
- tests/unit/strata/test_sync_interface.py
- src/frob/_cli_parsers/_misc.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_sync_interface.py
  reason: T-1150's own new test file and the sys CLI parser wiring for the new sync-interface
    subcommand
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: T-1150's own new test file and the sys CLI parser wiring for the new sync-interface
    subcommand
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_no_drift_reports_clean
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_addition_and_removal_detected
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_missing_interface_block_is_inserted_after_header
- tests/unit/strata/test_sync_interface.py::TestApplySyncInterface::test_writes_only_changed_files
- tests/unit/strata/test_sync_interface.py::test_fixture_design_binds_cleanly
- tests/unit/test_app_runners_batch7.py::TestSysRunnerDispatch::test_unknown_command_exits_1
- tests/unit/strata/test_sync_interface.py::test_report_and_apply_are_the_tier_a_ready_entry_points
designated_repro_test: null
acceptance:
- text: GIVEN a node whose bound code's public surface changed WHEN frob sys sync-interface
    runs THEN design/frob.strata's interface= attrs for that node are updated to the
    measured surface (additions and removals, sorted, preserving comments), printing
    a reviewable diff; a --check mode reports drift without writing
  evidence:
  - tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_addition_and_removal_detected
- text: GIVEN the T-1137 fix engine THEN SYS104 undeclared-symbol drift is registered
    as a Tier-A auto-fix backed by this command, OR (disclosed deferral, since T-1138
    landed only 3 hardcoded fix handlers with no generic rule-registration table and
    no --fix CLI flag yet to wire into) sync_interface_report/apply_sync_interface
    are the exact two entry points a future Tier-A handler would call, pinned by a
    test
  evidence:
  - tests/unit/strata/test_sync_interface.py::test_report_and_apply_are_the_tier_a_ready_entry_points
threat: null
component: null
---
T-1113 made SYS104 mandatory, which makes design/frob.strata's interface= attrs a hand-maintained mirror of every node's real public surface: the w18-strata agent re-synced it several times with a throwaway script, and main went red twice within hours of landing (tickets_gate, then SYS100 net.connect from T-1126) with the coordinator hand-editing the .strata file both times. Same churn-bomb shape as DEPR005's line-keyed baseline (T-1052): a mandatory check whose upkeep is manual is a red-main generator. The measurement already exists (_module_public_symbols per T-1113); ship it as a sys subcommand + --check gate hint + T-1137 Tier-A handler. If red-main recurrence continues before this lands, the DEPR005 demote-with-citation precedent applies to SYS104.