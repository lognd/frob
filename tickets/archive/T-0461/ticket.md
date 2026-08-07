---
id: T-0461
title: 'render migration sweep: route every command group through frob.render (graph/ticket/vet/sys/deploy/release/outline/xref/dup/arch/docs/exports/bind/perf/mutate/stats/serve/scaffold),
  one leaf per group under T-0448'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
- src/frob/app/
- tests/test_app.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_app.py
  reason: T-0461 app work maps to tests/test_app.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/unit/test_app_runners_batch5.py::TestStatsRunner::test_text_mode_prints_report
- tests/unit/test_app_runners_batch5.py::TestBindRunner::test_list_bindings_text_mode
- tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_stamp_success_writes_manifest
- tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_profile_then_heat_shows_hot_function
- tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_heat_json_output_is_valid_json
- tests/system/test_cli_sys_export.py::TestCliSysExport::test_k8s_export_is_valid_yaml
- tests/system/test_cli_sys_doc.py::TestSysDocCli::test_renders_matrix_for_default_view
- tests/system/test_cli_vet.py::TestHookMode::test_old_package_passes
- tests/test_mutate.py::test_run_mutations_survivors_when_tests_weak
designated_repro_test: null
threat: null
component: null
---
