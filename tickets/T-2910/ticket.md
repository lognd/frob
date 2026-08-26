---
id: T-2910
title: 'frob sys init: derive a starting strata model so a new repo gets value on
  day one'
state: queued
kind: feature
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
- src/frob/strata/_bootstrap.py
- src/frob/app/sys_runner.py
- src/frob/app/config.py
- tests/unit/strata/test_bootstrap.py
- tests/unit/test_app_runners_batch7.py
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_bootstrap.py
  reason: 'sys init bootstrap: new strata module + CLI wiring (T-2910)'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: 'sys init bootstrap: new strata module + CLI wiring (T-2910)'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/app/config.py
  reason: 'sys init bootstrap: new strata module + CLI wiring (T-2910)'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: 'sys init bootstrap: new strata module + CLI wiring (T-2910)'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/commands/sys.md
  reason: 'sys init bootstrap: new strata module + CLI wiring (T-2910)'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/strata/test_bootstrap.py
  reason: 'sys init bootstrap: new strata module + CLI wiring (T-2910)'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: 'sys init bootstrap: new strata module + CLI wiring (T-2910)'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: design/frob.strata
  reason: new stratamod->gates flow + fs.write/exec effects introduced by T-2910
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SYS111 ratchet ceiling bump for new fs.write/exec sites introduced by T-2910
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'WIRE001: wire new sys_init_check bool dest into the CLI-external-config
    allow-list (T-2910)'
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: src/frob/_cli_parsers/_misc.py
  reason: T-2911 holds a live lease on this shared file; land already verified this
    diff is entirely T-2910-authored via --allow-cross-ticket, narrowing declared
    scope only to unblock the start->in-progress transition
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: docs/commands/sys.md
  reason: T-2920 (parent epic) holds a live lease on this shared doc file; land already
    verified this diff is entirely T-2910-authored via --allow-cross-ticket, narrowing
    declared scope only to unblock the start->in-progress transition
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: design/frob.strata
  reason: T-2911 holds a live lease on this shared self-model file; land already verified
    this diff is entirely T-2910-authored via --allow-cross-ticket, narrowing declared
    scope only to unblock the start->in-progress transition
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: T-2911 holds a live lease on this shared ratchet-lock file; land already
    verified this diff is entirely T-2910-authored via --allow-cross-ticket, narrowing
    declared scope only to unblock the start->in-progress transition
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
- tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelRefusesAnExistingModel::test_refuses_when_a_strata_file_already_exists
- tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelRefusesAnExistingModel::test_existing_design_files_lists_the_real_files
- tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelNeverEmitsMay::test_rendered_text_never_contains_a_may_line
- tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelComponentsAndFlows::test_single_top_package_splits_by_subdirectory
- tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelComponentsAndFlows::test_real_import_edge_becomes_a_flow_in_the_right_direction
- tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelComponentsAndFlows::test_test_files_are_excluded_from_component_derivation
- tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelComponentsAndFlows::test_loose_file_directly_in_single_package_root_is_not_mistaken_for_a_subdir
- tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelComponentsAndFlows::test_no_python_source_produces_an_empty_but_valid_model
- tests/unit/strata/test_bootstrap.py::TestRenderedTextParsesAndElaborates::test_derived_model_parses_and_elaborates_cleanly
- tests/unit/strata/test_bootstrap.py::TestRenderedTextParsesAndElaborates::test_empty_model_still_parses
- tests/unit/strata/test_bootstrap.py::TestWriteBootstrapModel::test_writes_module_named_strata_file_under_design_dir
- tests/unit/test_app_runners_batch7.py::TestSysInit::test_writes_a_model_for_a_repo_with_none
- tests/unit/test_app_runners_batch7.py::TestSysInit::test_check_prints_without_writing
- tests/unit/test_app_runners_batch7.py::TestSysInit::test_refuses_when_a_model_already_exists
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
