---
id: T-1006
title: widespread pre-existing test failures block make coverage completion (~118
  fails, non-cov-caused)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_check_coverage_registry.py
- tests/test_coverage.py
- tests/system/test_system.py
- tests/test_makefile_lock_sync.py
- tests/test_registry_reconciliation_evasion.py
- tests/test_ticket_land.py
- tests/test_tickets_review.py
- tests/unit/deploy/test_generate.py
- tests/system/test_cli_exports.py
- tests/unit/strata/test_effects.py
- tests/unit/strata/test_export_golden.py
- tests/test_registry_reconciliation_supply_chain.py
- tests/unit/strata/test_registry_cross_corpus_totality.py
- tests/unit/test_app_runners_batch5.py
- tests/test_registry_exhaustiveness.py
- tests/unit/test_strata_tmlanguage.py
- tests/unit/test_exports.py
- src/frob/tickets/_land.py
- docs/design/registry/check-coverage.yaml
- src/frob/deploy/_generate.py
- tests/golden/frob_export_seccomp.json
- src/frob/app/exports_runner.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_check_coverage_registry.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_coverage.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/system/test_system.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_makefile_lock_sync.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_registry_reconciliation_evasion.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets_review.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/deploy/test_generate.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/system/test_cli_exports.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/strata/test_export_golden.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_registry_reconciliation_supply_chain.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/strata/test_registry_cross_corpus_totality.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/test_app_runners_batch5.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_registry_exhaustiveness.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/test_strata_tmlanguage.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/test_exports.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/tickets/_land.py
  reason: '_do_wip_commit''s `git add -A` sweeps up frob''s own .frob/ scratch

    artifacts (cache.db, derived.lock, prework/*.json, tickets.lock) as real

    staged changes in a fixture repo with no .gitignore for .frob/, defeating

    the CRLF-normalization-only no-op detection this function exists for

    (test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed,

    part of T-1006''s triage). Needs a source fix in _land.py, not just the

    test.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'test_check_coverage_registry.py''s exhaustiveness self-check found 6 gate

    rules (VET-JS004, VET-PY001/2/3, VET-RS001/2) added to the live gate

    registry with no matching CHK-GATE-<rule> entry in

    docs/design/registry/check-coverage.yaml (REG010 drift from a landing

    wave). Fixed via the existing `frob registry audit --sync-gate-rules`

    mechanism, which appends the entries to this exact file.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/deploy/_generate.py
  reason: 'Genuine product bug found while triaging T-1006:

    tests/unit/deploy/test_generate.py::TestSorted::test_privileged_port_grants_cap_net_bind

    fails because node_may_kinds now returns T-0717 mode-qualified

    family.mode kinds (e.g. "net.out") but _CAP_KIND_MAP in

    src/frob/deploy/_generate.py is keyed by the bare coarse family ("net"),

    so a node declaring only a precise mode-qualified may atom silently loses

    its CAP_NET_BIND_SERVICE grant. Fixed by keying the lookup off the

    family prefix.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/golden/frob_export_seccomp.json
  reason: 'tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp

    byte-for-byte compares export_seccomp(design/frob.strata) against the

    committed golden. design/frob.strata has legitimately grown new net.*

    capability declarations on some node(s) since this golden was last

    regenerated (accept/bind/connect/listen/recvfrom/sendto/socket now

    appear as allowed syscalls) -- a real, deterministic exporter output

    drift, not a test bug. Regenerated the golden from the current model.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/exports_runner.py
  reason: 'Genuine product bug found while triaging T-1006:

    tests/system/test_cli_exports.py::TestExportsFlags::test_json_output and

    test_json_modules_have_symbols fail because `frob exports <path> --json`

    corrupts its own JSON payload with a leaked `gitio: spawning (...)` DEBUG

    log line whenever the T-1127 daemon-proxy fast path

    (_try_exports_via_daemon) hits: that helper''s repo_root()/query() calls

    run entirely outside run()''s quiet_stdout_logs() context (which only

    wraps the non-daemon fallback path below it in the same function). Fixed

    by wrapping _try_exports_via_daemon''s body in quiet_stdout_logs() too.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: 'My own tests/unit/test_strata_tmlanguage.py fix (renaming PARSE_RS ->

    PARSE_DIR to match the strata-core/src/parse.rs -> parse/ split) needed

    a matching SYS104 interface= sync on design/frob.strata''s testsuite node

    (mandatory per dispatch instructions: `frob sys sync-interface` before

    land). Ran `frob sys sync-interface` to write the fix.

    '
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_ticket_land.py::TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace
- tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
- tests/test_ticket_land.py::TestMergeConflictOutsideLedger::test_real_conflict_outside_tickets_md_aborts
- tests/test_tickets_review.py::TestCloseStrictMode::test_strict_flag_alone_does_not_gate_without_config
- tests/test_tickets_review.py::TestCloseStrictMode::test_config_gate_alone_does_not_enforce_without_strict_flag
- tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_succeeds_with_matching_approve_review
- tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_succeeds_with_abbreviated_review_commit
- tests/test_registry_reconciliation_evasion.py::TestEvasionExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
- tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
- tests/test_coverage.py::TestPythonCoverageTargets::test_nothing_touched_returns_empty
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
- tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations
- tests/test_makefile_lock_sync.py::test_upload_relocks_after_version_bump
- tests/system/test_system.py::test_sys_audit_hardened_waived_two_user_model_proved
- tests/unit/deploy/test_generate.py::TestSorted::test_privileged_port_grants_cap_net_bind
- tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_is_mutually_navigable
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
- tests/unit/test_app_runners_batch5.py::TestStatsRunner::test_json_mode_prints_json
- tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally
- tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
- tests/system/test_cli_exports.py::TestExportsFlags::test_json_output
- tests/system/test_cli_exports.py::TestExportsFlags::test_json_modules_have_symbols
designated_repro_test: null
threat: null
component: null
---
Found while working T-0997 (coverage pipeline fix): a real, fresh `make
coverage` run in a clean worktree (merged to main tip) shows ~118 test
failures that are NOT caused by coverage instrumentation -- reproduced
several individually WITHOUT --cov and they still fail (e.g.
tests/test_registry_reconciliation_patterns.py::TestExhaustivenessGateOverRealPatterns::test_no_patterns_violations,
tests/test_ticket_land.py::TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace,
tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root).
These span registry-reconciliation exhaustiveness self-checks
(patterns/compliance/secrets/supply_chain/weaknesses/system_design all
report real violations against this worktree's live tickets.md/registry
state), ticket-land/evidence-enforcement system tests, and a handful of
CLI system tests. Because pytest exits non-zero, `make coverage`'s
Makefile recipe halts before its own `coverage combine`/`coverage xml`/
`frob check --stamp-coverage` lines run, so a fresh `make coverage`
currently requires a manual combine/xml/stamp workaround to get any
numbers at all -- and the failing subprocess-heavy system tests never
contribute their coverage, capping how far `join_fraction` can rise
(0.49 observed vs T-0997's target of "well above 0.34"; a green suite
would likely push it meaningfully higher). Needs triage: some of these
may be genuine registry drift in this worktree's ticket state (dozens of
concurrent worktree agents landing tickets) rather than a real product
bug; others (the gitless-target severity assertion, the render-lint
stderr-vs-logging-capture mismatch) look like real, fixable test/gate
bugs. Scope was deliberately not widened to fix these under T-0997.

2026-07-28 coordinator addendum (refiled from a w18-strata3 draft that
died to ledger-restore cycles): three more members of this failure set,
each verified pre-existing on main and unrelated to the wave-17/18
changes: tests/system/test_export_golden.py TestExportGolden
test_seccomp; tests/unit/strata/test_effects.py
TestDeployServeMutateNodeSplitConformance
test_serve_declares_zero_may_and_exercises_zero_effects;
tests/test_registry_cross_corpus_totality.py
TestCrossCorpusLinkageIntegrity
test_every_cross_ref_is_mutually_navigable. Fold them into this
ticket's triage denominator.