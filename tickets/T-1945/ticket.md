---
id: T-1945
title: Bulk-reformat the 77 ruff-format + 265 frob-fmt drifted files (deferred from
  T-1928)
state: done
kind: feature
origin: human
created: '2026-08-09'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_app.py
- tests/test_capability_registry.py
- tests/test_check_runner.py
- tests/test_coverage_wait_shared.py
- tests/test_doc012_promotion.py
- tests/test_docenum_gate.py
- tests/test_gates_fix_engine.py
- tests/test_gates_suppress.py
- tests/test_graph_imports.py
- tests/test_hook_diagnosis_nudge.py
- tests/test_land_verify_claims_outcome.py
- tests/test_lang_conformance_gate.py
- tests/test_pii_structural_gate.py
- tests/test_refactor.py
- tests/test_release.py
- tests/test_scaffold_worktree_lease_hook.py
- tests/test_serve_tools_daemon_bypass.py
- tests/test_telemetry.py
- tests/test_testing.py
- tests/test_tick012_gate.py
evidence_scope:
- tests/test_app.py
- tests/test_capability_registry.py
- tests/test_check_runner.py
- tests/test_coverage_wait_shared.py
- tests/test_doc012_promotion.py
- tests/test_docenum_gate.py
- tests/test_gates.py
- tests/test_gates_fix_engine.py
- tests/test_gates_suppress.py
- tests/test_graph.py
- tests/test_graph_imports.py
- tests/test_hook_diagnosis_nudge.py
- tests/test_land_verify_claims_outcome.py
- tests/test_lang_conformance_gate.py
- tests/test_pii_structural_gate.py
- tests/test_refactor.py
- tests/test_release.py
- tests/test_scaffold_worktree_lease_hook.py
- tests/test_serve_tools_daemon_bypass.py
- tests/test_telemetry.py
- tests/test_testing.py
- tests/test_tick012_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: '**/*.py'
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: tests/unit/strata/litmus/**
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/conftest.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_app.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_capability_registry.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_check_runner.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_coverage_wait_shared.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_doc012_promotion.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_docenum_gate.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_gates.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_gates_fix_engine.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_gates_suppress.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_graph.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_graph_imports.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_hook_diagnosis_nudge.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_land_verify_claims_outcome.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_lang_conformance_gate.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_pii_structural_gate.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_refactor.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_release.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_scaffold_worktree_lease_hook.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_serve_tools_daemon_bypass.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_telemetry.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_testing.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: '''tests/test_tick012_gate.py'''
  reason: 'batch 1 of the ruff-format reformat: 23 files under tests/ top-level, excludes
    T-1606-owned test_gates_fmt_directives.py/test_lang.py'
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/conftest.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_app.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_capability_registry.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_check_runner.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_coverage_wait_shared.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_doc012_promotion.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_docenum_gate.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_gates.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_gates_fix_engine.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_gates_suppress.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_graph.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_graph_imports.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_hook_diagnosis_nudge.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_land_verify_claims_outcome.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_lang_conformance_gate.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_pii_structural_gate.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_refactor.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_release.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_scaffold_worktree_lease_hook.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_serve_tools_daemon_bypass.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_telemetry.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_testing.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: '''tests/test_tick012_gate.py'''
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_app.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_capability_registry.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_check_runner.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_coverage_wait_shared.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_doc012_promotion.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_docenum_gate.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_gates_fix_engine.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_gates_suppress.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_graph_imports.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_hook_diagnosis_nudge.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_land_verify_claims_outcome.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_lang_conformance_gate.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_pii_structural_gate.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_refactor.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_release.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_scaffold_worktree_lease_hook.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_serve_tools_daemon_bypass.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_telemetry.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_testing.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_tick012_gate.py
  reason: fix earlier quoting bug in --add; re-add clean globs, dropping T-1654-owned
    files
  actor: logan
  at: '2026-08-20'
evidence:
- tests/test_app.py::TestRunCoverageWait::test_coverage_lock_path_is_under_frob_dir
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells
- tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean
- tests/test_coverage_wait_shared.py::TestTreeDigest::test_identical_hashes_produce_identical_digest
- tests/test_doc012_promotion.py::TestDoc012PromotedToError::test_undocumented_subcommand_is_now_error
- tests/test_docenum_gate.py::TestDocenum001Gate::test_stale_claimed_list_fires
- tests/test_gates.py::TestMutationEvidencePackageReexports::test_must_still_pass_violations_importable_from_package
- tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression
- tests/test_gates_suppress.py::TestSuppressionDialects::test_registers_ty_mypy_ruff
- tests/test_graph.py::TestDigests::test_reformat_identical_digests
- tests/test_graph_imports.py::TestBuildImportGraph::test_resolves_a_real_intra_repo_import_edge
- tests/test_hook_diagnosis_nudge.py::test_nudges_on_diagnosis_and_prints_system_message
- tests/test_land_verify_claims_outcome.py::TestClaimsReverifyOutcomeDistinguishesSkipFromPass::test_unmeasured_passing_ids_and_check_gates_is_surfaced_as_skipped
- tests/test_lang_conformance_gate.py::TestLangConformanceGate::test_real_registry_is_clean
- tests/test_pii_structural_gate.py::TestFieldNames::test_password_field_fires
- tests/test_refactor.py::TestResolveSymbol::test_resolves_top_level_function
- tests/test_release.py::test_stamp_and_no_change_is_none
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_installs_pre_commit_and_pre_merge_commit
- tests/test_serve_tools_daemon_bypass.py::TestFrobDoableTicketsRevalidation::test_resolved_sweep_ticket_is_dropped_before_listing
- tests/test_telemetry.py::test_append_event_writes_one_json_line
- tests/test_testing.py::TestSelect::test_direct_hit
- tests/test_tick012_gate.py::TestTick012LeaseScopeDrift::test_stale_superset_path_fires
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 2c3a7620d274b71aefefa7ff728d6953b222ff29
---
T-1928 measured, on a clean main tree (2026-08-10), three genuinely
different things all named "fmt" that answer different questions:

- `frob check --only fmt` (gate:FMT / FMT001): diff-scoped by
  construction (`fmt_gate`, src/frob/gates/_todo_fmt.py, only inspects
  `frob:` directive-comment lines the CURRENT DIFF touches). On a clean
  tree this is correctly 0 errors in ~0s -- it did no work because there
  was no diff to examine, not because the repo is formatted.
- `ruff format --check .` (the "ruff-format" tool inside `frob check`'s
  unscoped lint stage, src/frob/check/_python.py::_ruff_format_result):
  77 .py files with real ruff code-style drift, repo-wide.
- `frob fmt --check` (standalone CLI, src/frob/app/fmt_runner.py): 265
  files (215 .py + 49 .strata) needing `frob:` directive-comment
  line-wrap canonicalization, repo-wide -- a DIFFERENT concern from ruff
  code style. Overlap between the two .py lists is only 7 files out of
  215/77 -- these are almost entirely disjoint drift populations, not
  the same drift measured two ways.

T-1928's explicit non-goal was "do not open with a mass reformat" (a
265+77-file reformat commit is unreviewable and collides with every live
worktree). Per T-1928's acceptance [4], recording that decision here
explicitly rather than leaving it implicit in a passing gate:

DECISION (2026-08-10): the 77-file ruff-format drift and the 265-file
frob-fmt drift are ACCEPTED, KNOWN, UNACTIONED debt for now. Neither is
silently "fixed" by T-1928 (which only adds disclosure, per its own
non-goal). This ticket tracks the actual bulk-reformat work, to be
sequenced separately, deliberately, when the live `.claude/worktrees/*`
count is low enough that a large mechanical diff will not collide with
concurrent agents' in-flight work. Suggested shape when picked up: two
separate commits (ruff-format's 77 files; frob-fmt's 265 files), not one
combined diff, since they are different tools fixing different concerns
and either could regress independently.