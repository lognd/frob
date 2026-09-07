---
id: T-4264
title: 'drive the posix gate errors to zero: formatter drift, two stale acks, a broken
  tests edge, a missing doc edge, three unreachable bindings, and a waiver whose symref
  does not match'
state: in-progress
kind: bug
origin: human
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/vet/_bare_toolchain.py
- src/frob/check/_python.py
- src/frob/lang/_walk_bash.py
- tests/test_lang.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: scripts/artifact_smoke.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout_evidence.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/gates/_coverage_sites.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/gates/_debt_deprecated.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/graph/dsl.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/testing/_runners.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: strata-core/src/parse/grammar_flow.rs
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/system/test_artifact_smoke.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/test_ci_workflow_actions_pinned.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/test_hook_frob_suggest.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/test_mutate.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/test_refs_gate.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/test_serve_daemon.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/test_serve_socket.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/test_tickets_acceptance.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/test_tickets_evidence_removal.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/gates/test_version_coupling.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/strata/test_selfconform_kinds.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/test_artifact_smoke_script.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/test_dependency_pins.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/test_graph_cache.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/test_new_ticket_scope_overlap_warning.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/test_release_workflow_gate.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/test_runtime_deps.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/test_ticket_accept_evidence_hint_t4106.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/test_ticket_close_evidence_cmd_repeat_t4108.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/test_ticket_runner_base_forward_t4105.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/test_verify_language_buckets.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/verify/test_worker.py
  reason: widen scope to the files the integration run formatter finding names so
    the ruff-format commit is covered by this ticket rather than tripping SCOPE001/COV002
    on out-of-scope reformatted files
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: scripts/artifact_smoke.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: src/frob/_cli_parsers/_ticket/_closeout_evidence.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: src/frob/gates/_coverage_sites.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: src/frob/gates/_debt_deprecated.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: src/frob/graph/dsl.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: src/frob/testing/_runners.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: strata-core/src/parse/grammar_flow.rs
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/system/test_artifact_smoke.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/test_ci_workflow_actions_pinned.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/test_hook_frob_suggest.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/test_mutate.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/test_refs_gate.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/test_serve_daemon.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/test_serve_socket.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/test_ticket_work_and_land_finish.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/test_tickets_acceptance.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/test_tickets_evidence_removal.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/gates/test_version_coupling.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/graph/test_dsl.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/strata/test_selfconform_kinds.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/test_artifact_smoke_script.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/test_dependency_pins.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/test_graph_cache.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/test_new_ticket_scope_overlap_warning.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/test_release_workflow_gate.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/test_runtime_deps.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/test_ticket_accept_evidence_hint_t4106.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/test_ticket_close_evidence_cmd_repeat_t4108.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/test_ticket_runner_base_forward_t4105.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/test_verify_language_buckets.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/verify/test_worker.py
  reason: 'revert: widening scope to these files opened a SCOPE002 closure cascade
    (186 distinct missing-file violations, promoted to error in frob.toml) that is
    disproportionate to a mechanical reformat; splitting the formatter fix so only
    already-in-scope files land under T-4264 and filing a separate ticket for the
    rest'
  actor: logan
  at: '2026-09-07'
designated_repro_test: null
acceptance:
- text: given the integration run's own unscoped gate invocation, when it runs on
    the fixed tree, then it reports zero errors apart from any that belong to tickets
    still in flight
  evidence: []
- text: given the formatter, when it runs on the fixed tree, then it reports no files
    needing reformatting
  evidence: []
- text: given the type-check refusal helper's rule finding, when it is resolved, then
    the resolution addresses why the existing waiver's symref did not match rather
    than adding a second waiver
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DRIVE THE POSIX GATE ERRORS TO ZERO. This is the release blocker. Measured from
the first integration run that has ever seen the current tree.

THE TEST SUITE IS ALREADY GREEN. That run collected 13,668 tests and failed
zero. The job still exits non-zero because the gate step reports 19 errors and
the formatter reports work to do. Do not go looking for test failures; there are
none on this platform.

THE EXACT SET, taken from the run's own tool summary and finding lines.

  FORMATTER: 33 files would be reformatted. Run the project's format verb rather
  than reformatting by hand, and commit the result as its own change.

  DRIFT001, two sites: a gate entry point and the rule-registry scan both have
  digests that moved since their last acknowledgement, one with four dependents
  and one with twelve. These are acknowledgement updates, not code fixes, and
  the finding text names the exact command for each. Read what actually changed
  before acknowledging; an ack is an assertion that the dependents are still
  correct, not a way to silence the gate.

  DRIFT002, one site: a tests edge from the ruff autofix helper names a test that
  no longer resolves. Find where that test went and repoint the edge.

  COV001, one site: a public constant in the bare-toolchain module has no doc
  edge.

  COV006, three sites: the bash walker's tests bind private symbols the call
  graph cannot reach from the test bodies. Check whether the tests genuinely
  exercise those symbols. If they do and the graph simply cannot see it, that is
  a waiver with a real reason. If they do not, bind a symbol they actually call.

  ARCH103, one site: a touched-files type-check refusal helper mixes input and
  output, string formatting, and three decision points. NOTE FIRST that a waiver
  for this rule already exists in the same file, on a neighbouring symbol, and
  the run reports it as NOT APPLIED because the symrefs do not match even after
  separator normalisation. Determine whether the intent was to cover this symbol
  and the waiver simply names the wrong one. If so the fix is the waiver's
  symref, not a refactor. That same file also carries an unmatched waiver
  reported by the waiver gate as matching zero findings, which is the other half
  of the same mismatch; resolve both together.

THE THIRTEEN REMAINING COV003 ERRORS ARE NOT YOURS TO FIX. They belong to two
tickets whose evidence names tests that exist only in unlanded worktrees, so the
ledger on the integration branch cites tests the branch does not have. They clear
when those tickets land, and their owners are already working them. Do not touch
those tickets, do not edit their evidence, and do not delete their ledger
entries. If your own run still shows them at the end, say so and leave them.

VERIFY THE WAY THE INTEGRATION RUN DOES. A scoped gate run proves nothing about
the unscoped total that the job actually computes. Before you claim zero, run the
gates the way the job runs them and quote the summary line.
