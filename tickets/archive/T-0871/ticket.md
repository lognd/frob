---
id: T-0871
title: 'exports policy residue: drive all frob-exports missing-symbol lines to zero
  (9 packages, 57 symbols)'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/__init__.py
- src/frob/arch/__init__.py
- src/frob/lang/__init__.py
- src/frob/mutate/__init__.py
- src/frob/perf/__init__.py
- src/frob/scaffold/__init__.py
- src/frob/serve/__init__.py
- src/frob/testing/__init__.py
- src/frob/vet/__init__.py
- docs/guides/install.md
- docs/modules/arch.md
- docs/modules/lang.md
- docs/modules/mutate.md
- docs/modules/serve.md
- src/frob/arch/_cpp_mayraise.py
- src/frob/arch/_patterns.py
- src/frob/doctor.py
- src/frob/lang/_common.py
- src/frob/lang/_extract.py
- src/frob/lang/_nodes.py
- src/frob/lang/_walk_c.py
- src/frob/lang/_walk_kotlin.py
- src/frob/lang/_walk_python.py
- src/frob/lang/_walk_rust.py
- src/frob/lang/_walk_typescript.py
- src/frob/mutate/_journal.py
- src/frob/scaffold/_managed.py
- src/frob/serve/_daemon.py
- src/frob/serve/_tools.py
- src/frob/serve/_warm.py
- src/frob/serve/server.py
- src/frob/vet/_capability.py
- src/frob/vet/_capability_modes.py
- tests/test_serve.py
- tests/test_serve_daemon.py
- tests/unit/test_lang_primitives.py
- tests/unit/vet/test_capability_modes.py
- tests/unit/test_exports.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/guides/install.md
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/arch.md
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/lang.md
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/mutate.md
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/serve.md
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/arch/_cpp_mayraise.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/arch/_patterns.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/doctor.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/lang/_common.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/lang/_extract.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/lang/_nodes.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/lang/_walk_c.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/lang/_walk_kotlin.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/lang/_walk_python.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/lang/_walk_rust.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/lang/_walk_typescript.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/mutate/_journal.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/scaffold/_managed.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/serve/_daemon.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/serve/_tools.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/serve/_warm.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/serve/server.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/vet/_capability.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/vet/_capability_modes.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_serve.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_serve_daemon.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/test_lang_primitives.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/vet/test_capability_modes.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/test_exports.py
  reason: 'T-0871 re-sync: re-extend scope to referrer-fix files + the new acceptance-0
    evidence test (main advanced during landing, restoring reverted the prior extension)'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/vet/test_capability_modes.py::TestModeQualified::test_joins_family_and_mode
- tests/unit/vet/test_capability_modes.py::TestCanonicalAndNormalize::test_normalize_observed_kind_matches_canonical
- tests/test_serve.py::TestWarmState::test_second_call_is_cache_hit
- tests/test_serve.py::TestWarmState::test_file_change_forces_rebuild
- tests/test_serve_daemon.py::TestPollPostLand::test_head_unchanged_is_noop
- tests/test_serve_daemon.py::TestPollPostLand::test_head_moved_refreshes_verdict
- tests/test_serve_daemon.py::TestRunDaemonCycle::test_runs_both_jobs_and_returns_status
- tests/test_serve_daemon.py::TestFrobDaemonStatus::test_reads_current_status
- tests/test_serve_daemon.py::TestStartDaemon::test_background_loop_runs_a_cycle_then_stops
- tests/test_mutate_journal.py::test_write_journal_is_idempotent_for_same_content
- tests/test_mutate_journal.py::test_write_journal_refuses_on_content_collision
- tests/test_lang.py::TestParsePython::test_symbols_and_nesting
- tests/unit/test_lang_kotlin.py::TestParseKotlin::test_kt_fixture_parses_without_error
- tests/unit/test_lang_primitives.py::test_collapse_ws_flattens_whitespace
- tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_two_helpers_spawning_identical_subprocess_is_flagged
- tests/unit/perf/test_effect_summaries.py::TestUnknownIdentityEquality::test_two_unknowns_with_the_same_reason_text_are_not_equal
- tests/test_doctor.py::test_run_diagnosis_natives_present
- tests/test_gates.py::TestErrorsAsValuesAdvisory::test_public_raiser_with_no_handling_caller_recommends_result
- tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
designated_repro_test: null
acceptance:
- text: GIVEN the repo at this ticket's close WHEN frob check runs THEN every frob-exports
    package line reports zero public symbols missing from __init__.py, with each resolution
    being a deliberate export or demotion, not a waiver
  evidence:
  - tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
threat: null
component: exports
---
T-0204 child (exports family residue, continuing T-0600/T-0601). frob-exports still reports missing public symbols per package: src/frob 2, src/frob/arch 23, src/frob/lang 2, src/frob/mutate 3, src/frob/perf 5, src/frob/scaffold 1, src/frob/serve 11, src/frob/testing 2, src/frob/vet 8 (57 total at 2026-07-23 baseline; recount at start -- concurrent waves move it). Per-package policy decision as in T-0600/T-0601: export via __init__.py or demote to private (underscore) -- no blanket waiver. Deliverable: every frob-exports tool line reports 0 missing.