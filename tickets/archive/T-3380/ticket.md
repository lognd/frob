---
id: T-3380
title: ruff format repo-wide sweep (81 files, no owning gate)
state: done
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/root-write-guard.py
- src/frob/_cli_parsers/_ops.py
- src/frob/app/stats_runner.py
- src/frob/app/status_runner.py
- src/frob/app/sys_runner.py
- src/frob/app/ticket_runner/_query.py
- src/frob/findings.py
- src/frob/gates/_lexical_selfcheck.py
- src/frob/gates/_models.py
- src/frob/gates/_mutation_evidence.py
- src/frob/gates/_port_selfcheck.py
- src/frob/gates/_tdd_order.py
- src/frob/gates/_version_coupling.py
- src/frob/gates/_walk_lint.py
- src/frob/ghio.py
- src/frob/graph/dsl.py
- src/frob/graph/reach.py
- src/frob/process/_lock.py
- src/frob/serve/_socketd.py
- src/frob/stats/_agentic.py
- src/frob/strata/_selfconform.py
- src/frob/strata/_selfconform_core_rules.py
- src/frob/strata/_selfconform_kinds.py
- src/frob/strata/_selfconform_models.py
- src/frob/strata/_selfconform_surface_rules.py
- src/frob/tickets/_archive.py
- src/frob/tickets/_done_report.py
- src/frob/tickets/_land_compose.py
- src/frob/tickets/_land_release.py
- src/frob/tickets/_models.py
- src/frob/tickets/_reporting.py
- src/frob/tickets/_store.py
- src/frob/vet/_capability_registry/_dangerous_ops_bash_csharp.py
- src/frob/vet/_capability_registry/_matrix.py
- src/frob/vet/_supplychain.py
- tests/gates/test_comment_placement.py
- tests/integration/test_interfaces.py
- tests/system/test_cli_perf.py
- tests/test_check_runner.py
- tests/test_ci_report.py
- tests/test_ci_validity.py
- tests/test_gates.py
- tests/test_gates_vmodel.py
- tests/test_ghio.py
- tests/test_graph_reach.py
- tests/test_measure_evidence_reach.py
- tests/test_mutate.py
- tests/test_refs_gate.py
- tests/test_status.py
- tests/test_ticket_land_lint_diff_attribution.py
- tests/test_ticket_land_ty_diff_attribution.py
- tests/test_tickets_cmd_evidence.py
- tests/test_tickets_no_scope.py
- tests/test_vet.py
- tests/test_vet_capability.py
- tests/test_walk_lint_gate.py
- tests/unit/gates/test_lock_producer.py
- tests/unit/gates/test_refs.py
- tests/unit/gates/test_version_coupling.py
- tests/unit/graph/test_dsl_markdown_waive.py
- tests/unit/strata/test_bootstrap.py
- tests/unit/strata/test_shrink.py
- tests/unit/strata/test_vmodel_authoring.py
- tests/unit/strata/test_vmodel_check.py
- tests/unit/test_app_runners_batch7.py
- tests/unit/test_close_blocked_by_guard.py
- tests/unit/test_doctor.py
- tests/unit/test_land_finish_idempotent.py
- tests/unit/test_land_release_out_of_tree.py
- tests/unit/test_land_stage_flip.py
- tests/unit/test_lang_strata_entity_arch.py
- tests/unit/test_rapid_debt.py
- tests/unit/test_reporting_t3285_fenced_subheadings.py
- tests/unit/test_ticket_restore.py
- tests/unit/test_wire001_atexit_register.py
- tests/unit/test_wire001_property_attribute_access.py
- tests/unit/verify/test_quarantine.py
- tests/unit/verify/test_verify_runner.py
scope_breadth_ack: true
scope_breadth_ack_reason: 'a repo-wide ruff format --check failure has no natural
  narrower scope -- gate:FMT only scans diff-touched frob: directive lines per its
  own scope-note and never catches this; the sweep itself is purely mechanical (ruff
  format .)'
no_scope_declared: true
no_scope_declared_reason: mechanical ruff-format sweep across many files owned by
  other in-progress tickets; scope enforced at land time via the sweep's own touched-file
  diff, not a pre-declared write lease -- a repo-wide glob collides with every other
  series' scope
scope_changes:
- op: remove
  glob: '**/*.py'
  reason: mechanical ruff-format sweep across many files owned by other in-progress
    tickets; scope enforced at land time via the sweep's own touched-file diff, not
    a pre-declared write lease -- a repo-wide glob collides with every other series'
    scope
  actor: logan
  at: '2026-08-29'
- op: add
  glob: .claude/hooks/root-write-guard.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/_cli_parsers/_ops.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/stats_runner.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/status_runner.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/findings.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_lexical_selfcheck.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_models.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_mutation_evidence.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_port_selfcheck.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_tdd_order.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_version_coupling.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_walk_lint.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/ghio.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/graph/dsl.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/graph/reach.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/process/_lock.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/serve/_socketd.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/stats/_agentic.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/strata/_selfconform_core_rules.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/strata/_selfconform_kinds.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/strata/_selfconform_models.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/strata/_selfconform_surface_rules.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/_archive.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/_done_report.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/_land_compose.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/_land_release.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/_models.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/_reporting.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/_store.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/vet/_capability_registry/_dangerous_ops_bash_csharp.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/vet/_capability_registry/_matrix.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/vet/_supplychain.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/gates/test_comment_placement.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/integration/test_interfaces.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/system/test_cli_perf.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_check_runner.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_ci_report.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_ci_validity.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_gates.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_gates_vmodel.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_ghio.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_graph_reach.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_measure_evidence_reach.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_mutate.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_refs_gate.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_status.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_ticket_land_lint_diff_attribution.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_ticket_land_ty_diff_attribution.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_tickets_cmd_evidence.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_tickets_no_scope.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_vet.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_vet_capability.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_walk_lint_gate.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/gates/test_lock_producer.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/gates/test_refs.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/gates/test_version_coupling.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/graph/test_dsl_markdown_waive.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/strata/test_bootstrap.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/strata/test_shrink.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/strata/test_vmodel_authoring.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/strata/test_vmodel_check.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_close_blocked_by_guard.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_doctor.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_land_finish_idempotent.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_land_release_out_of_tree.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_land_stage_flip.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_lang_strata_entity_arch.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_rapid_debt.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_reporting_t3285_fenced_subheadings.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_ticket_restore.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_wire001_atexit_register.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_wire001_property_attribute_access.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/verify/test_quarantine.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/verify/test_verify_runner.py
  reason: exact touched-file set of the ruff format sweep, measured after running
    ruff format .
  actor: logan
  at: '2026-08-29'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): pure ruff-format whitespace/style sweep, no
    logic changes'
  actor: logan
  at: '2026-08-29'
  old_length: 648
  new_length: 740
evidence:
- tests/test_ghio.py::TestPreflight::test_not_installed
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 6a7ac4e40e33394dfda8414fcfc8613a4a02f201
---
ruff format --check . measured 81 files needing reformatting on current main. gate:FMT (FMT001) only scans frob: directive-comment lines touched by the current diff -- it never scans the whole tree -- so this drift was invisible to frob check and accumulated unowned. Fix: run ruff format . and land the 81-file diff as one standalone sweep, on its own commit, nothing batched with it. frob fmt --check (the repo's own directive-line formatter) separately flags 5 Rust files (frob-core/src/*.rs, strata-core/src/**/*.rs) -- disjoint from ruff format's 81 Python files, confirmed zero overlap, so the two tools cannot fight each other on this sweep.

frob:no-behavior-change reason="pure ruff-format whitespace/style sweep, no logic changes"