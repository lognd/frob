---
id: T-0588
title: 'Resolve TEST014 name-collision cases: disambiguate or tighten TEST001 credit'
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/app/*.py
- src/frob/arch/_models.py
- src/frob/dup/_legacy.py
- src/frob/exports/__init__.py
- src/frob/gitlog/__init__.py
- src/frob/map/__init__.py
- src/frob/outline/__init__.py
- src/frob/process/parsers/common.py
- src/frob/xref/__init__.py
- src/frob/check/__init__.py
- src/frob/logging/formatter.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/*.py
  reason: 'T-0588 disambiguates TEST014 name-collision groups by adding explicit frob:tests
    edges directly on the colliding public symbols themselves (app/*_runner.py run(),
    Result classes as_json/as_text, logging formatters) -- these edits necessarily
    touch each collision symbol''s own source file, not just src/frob/gates/__init__.py.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/arch/_models.py
  reason: 'T-0588 disambiguates TEST014 name-collision groups by adding explicit frob:tests
    edges directly on the colliding public symbols themselves (app/*_runner.py run(),
    Result classes as_json/as_text, logging formatters) -- these edits necessarily
    touch each collision symbol''s own source file, not just src/frob/gates/__init__.py.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/dup/_legacy.py
  reason: 'T-0588 disambiguates TEST014 name-collision groups by adding explicit frob:tests
    edges directly on the colliding public symbols themselves (app/*_runner.py run(),
    Result classes as_json/as_text, logging formatters) -- these edits necessarily
    touch each collision symbol''s own source file, not just src/frob/gates/__init__.py.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/exports/__init__.py
  reason: 'T-0588 disambiguates TEST014 name-collision groups by adding explicit frob:tests
    edges directly on the colliding public symbols themselves (app/*_runner.py run(),
    Result classes as_json/as_text, logging formatters) -- these edits necessarily
    touch each collision symbol''s own source file, not just src/frob/gates/__init__.py.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/gitlog/__init__.py
  reason: 'T-0588 disambiguates TEST014 name-collision groups by adding explicit frob:tests
    edges directly on the colliding public symbols themselves (app/*_runner.py run(),
    Result classes as_json/as_text, logging formatters) -- these edits necessarily
    touch each collision symbol''s own source file, not just src/frob/gates/__init__.py.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/map/__init__.py
  reason: 'T-0588 disambiguates TEST014 name-collision groups by adding explicit frob:tests
    edges directly on the colliding public symbols themselves (app/*_runner.py run(),
    Result classes as_json/as_text, logging formatters) -- these edits necessarily
    touch each collision symbol''s own source file, not just src/frob/gates/__init__.py.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/outline/__init__.py
  reason: 'T-0588 disambiguates TEST014 name-collision groups by adding explicit frob:tests
    edges directly on the colliding public symbols themselves (app/*_runner.py run(),
    Result classes as_json/as_text, logging formatters) -- these edits necessarily
    touch each collision symbol''s own source file, not just src/frob/gates/__init__.py.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/process/parsers/common.py
  reason: 'T-0588 disambiguates TEST014 name-collision groups by adding explicit frob:tests
    edges directly on the colliding public symbols themselves (app/*_runner.py run(),
    Result classes as_json/as_text, logging formatters) -- these edits necessarily
    touch each collision symbol''s own source file, not just src/frob/gates/__init__.py.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/xref/__init__.py
  reason: 'T-0588 disambiguates TEST014 name-collision groups by adding explicit frob:tests
    edges directly on the colliding public symbols themselves (app/*_runner.py run(),
    Result classes as_json/as_text, logging formatters) -- these edits necessarily
    touch each collision symbol''s own source file, not just src/frob/gates/__init__.py.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'T-0588 disambiguates TEST014 name-collision groups by adding explicit frob:tests
    edges directly on the colliding public symbols themselves (app/*_runner.py run(),
    Result classes as_json/as_text, logging formatters) -- these edits necessarily
    touch each collision symbol''s own source file, not just src/frob/gates/__init__.py.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/logging/formatter.py
  reason: 'T-0588 disambiguates TEST014 name-collision groups by adding explicit frob:tests
    edges directly on the colliding public symbols themselves (app/*_runner.py run(),
    Result classes as_json/as_text, logging formatters) -- these edits necessarily
    touch each collision symbol''s own source file, not just src/frob/gates/__init__.py.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_app_runners.py::TestArchRunner::test_json_mode
- tests/unit/test_app_runners_batch5.py::TestBindRunner::test_mismatch_json_mode_no_exit
- tests/unit/test_app_runners_batch5.py::TestCycleRunner::test_cycle_found_with_suggest
- tests/test_debt_runner.py::TestDebtRunner::test_json_mode_lists_debt_entries
- tests/unit/test_app_runners_batch5.py::TestDocsRunner::test_search_json_mode
- tests/unit/test_app_runners_batch5.py::TestDupRunner::test_scan_text_mode_logs_result
- tests/unit/test_app_runners.py::TestExportsRunner::test_json_mode_logs_result
- tests/unit/test_app_runners.py::TestGitlogRunner::test_json_mode_prints_json
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_build_success_logs_stats
- tests/unit/test_app_runners.py::TestMutateRunner::test_success_no_survivors_text_mode
- tests/unit/test_app_runners.py::TestOutlineRunner::test_file_target_json_mode
- tests/test_pool_runner.py::TestPoolSnapshotCli::test_snapshot_baselines_keys
- tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_stamp_success_writes_manifest
- tests/unit/test_app_style.py::test_stats_plain_stdout_has_no_ansi
- tests/unit/test_app_runners_batch7.py::TestSysRunnerDispatch::test_unknown_command_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketRunnerDispatch::test_unknown_command_exits_1
- tests/unit/test_app_runners.py::TestXrefRunner::test_found_symbol_json_mode
- tests/unit/test_arch.py::TestArchResultFormat::test_as_text_clean_project
- tests/unit/test_arch.py::TestArchResultFormat::test_as_json_has_suggestions_key
- tests/unit/test_dup.py::TestDupResultFormat::test_as_text_clean_project
- tests/unit/test_dup.py::TestDupResultFormat::test_as_json_has_groups_key
- tests/unit/test_exports.py::TestExportsPackage::test_as_text_output
- tests/unit/test_gitlog_rendering.py::test_as_json_round_trips_groups
- tests/unit/test_gitlog_rendering.py::test_as_text_no_commits_short_circuit
- tests/unit/test_map.py::test_map_as_text
- tests/unit/test_map.py::test_map_as_json
- tests/unit/test_outline.py::test_py_outline_as_text
- tests/unit/test_outline.py::test_py_outline_as_json
- tests/unit/test_xref.py::test_as_text
- tests/unit/test_xref.py::test_as_json
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_json_mode_prints_json_and_errors_exit_1
- tests/unit/test_process.py::test_ruff_as_text
- tests/unit/test_process.py::test_pytest_as_text_shows_failures
- tests/unit/test_process.py::test_pytest_as_json
- tests/system/test_cli_check.py::TestCheckBadCode::test_unused_import_output_mentions_error
designated_repro_test: null
threat: null
component: null
---
T-0547 added TEST014 (WARN) to surface every case where _inferred_unit_cases's naming-convention fallback ambiguously credits two DIFFERENT files' same-leaf-name public symbols off the same collected test id(s) (docs/audits/gates-accounting.md B6). It deliberately does NOT withdraw TEST001 credit: a compat survey against this repo (T-0547's Done report) found a blanket path/module-correlation requirement breaks ~100% of convention-fallback matches here (96/81 depending on heuristic), since tests/ does not mirror src/frob/<pkg>/ layout. But the survey ALSO found 5 real leaf-name collision groups in this repo TODAY sharing convention-matched tests (main, format, as_text, as_json, run) -- TEST014 will fire WARN for each until resolved. This ticket is to actually resolve those 5 (add explicit frob:tests edges to disambiguate, or accept the WARN permanently via frob:waive with a reason), and to decide/design a general per-symbol tightening path now that real examples exist to test any proposed rule against (e.g. requiring the matched test's own module path to appear as a substring of the target's qualname, or promoting TEST014 to ERROR once explicit edges are added to eliminate ambiguity repo-wide).

TEST-pool triage (T-draft-edbf1e26, 2026-07-22) re-measured `frob check --only test` against current main+T-0583: 244 TEST014 warnings remain, all pairwise fan-out from only 4 (not 5 -- `main` no longer collides) distinct leaf-name groups: `run` (171 pairs, 20 app/*_runner.py `run(cfg)` entrypoints all convention-matched by the same frob-core test), `as_json`/`as_text` (36 pairs each), `format` (1 pair). None resolved this pass -- disambiguating 20 runner modules' TEST001 credit is exactly this ticket's own scope and outsized for a triage pass; left queued with this refreshed count so the next attempt does not need to re-derive it.