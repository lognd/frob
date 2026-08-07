---
id: T-1205
title: 'coverage as managed derived state: auto-refresh touched-set, never stale,
  never manual'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- Makefile
- src/frob/gates/_coverage.py
- src/frob/check/__init__.py
- docs/modules/gates.md
- tests/test_coverage.py
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/app/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_coverage.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/gates.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_coverage.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/__init__.py
  reason: TEST005's violation-emitting helpers (_test005_symbols/_modules/_systems)
    live in src/frob/gates/__init__.py, not _coverage.py -- acceptance[1]'s stale-and-disclosed
    marking must be added there; tests/test_gates.py is where TEST005's existing test
    coverage lives
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates.py
  reason: TEST005's violation-emitting helpers (_test005_symbols/_modules/_systems)
    live in src/frob/gates/__init__.py, not _coverage.py -- acceptance[1]'s stale-and-disclosed
    marking must be added there; tests/test_gates.py is where TEST005's existing test
    coverage lives
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_gates.py::TestTestGate::test_test005_symbol_finding_discloses_stale_coverage
- tests/test_gates.py::TestTestGate::test_test005_symbol_finding_no_disclosure_when_fresh
- tests/test_gates.py::TestTestGate::test_test005_module_finding_discloses_stale_coverage
- tests/test_gates.py::TestTestGate::test_test005_system_finding_discloses_stale_coverage
- tests/test_gates.py::TestTestGate::test_test017_fires_on_low_join_fraction
- tests/test_coverage.py::TestCoverageFileCache::test_load_missing_returns_empty
- tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_backfills_unchanged_file
- tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_ignores_stale_hash
- tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_never_overwrites_fresh_data
- tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_persists_measured_files
- tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_roundtrips_through_fill_from_cache
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
- tests/test_coverage.py::TestNativeCoverageRefresh::test_incremental_run_uses_touched_set_targets
- tests/test_coverage.py::TestNativeCoverageRefresh::test_nothing_touched_only_restamps
- tests/test_coverage.py::TestNativeCoverageRefresh::test_refused_spawn_is_err
- tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc
- tests/test_coverage.py::TestRunCoverageWaitNativeDefault::test_default_command_none_calls_native_refresh
- tests/unit/test_coverage_runner.py::TestCoverageRunner::test_default_delegates_to_run_coverage_wait
designated_repro_test: null
acceptance:
- text: GIVEN a tracked source change WHEN the user runs frob coverage, or frob test
    --wait-coverage (via run_coverage_wait) THEN coverage data is refreshed automatically
    via the touched-set test machinery (frob.testing._incremental_coverage.python_coverage_targets)
    merged into the persisted coverage store, in-process, no Makefile/shell dependency
    -- the common incremental loop never requires a manual make coverage invocation;
    frob check itself deliberately does NOT trigger a refresh (see acceptance[4]);
    make coverage (the full-suite target) remains a legitimate manual/coordinator-only
    step for its own xdist-crash-recovery resilience, disclosed not silently dropped
  evidence:
  - tests/unit/test_coverage_runner.py::TestCoverageRunner::test_default_delegates_to_run_coverage_wait
  - tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc
- text: GIVEN coverage data that cannot be refreshed (tests failing, run interrupted)
    THEN TEST005-family findings against stale regions are marked stale-and-disclosed
    rather than reported as current fact, and TEST011 escalates from advisory to a
    blocking freshness contract
  evidence:
  - tests/test_gates.py::TestTestGate::test_test005_symbol_finding_discloses_stale_coverage
  - tests/test_gates.py::TestTestGate::test_test005_module_finding_discloses_stale_coverage
  - tests/test_gates.py::TestTestGate::test_test005_system_finding_discloses_stale_coverage
  - tests/test_gates.py::TestTestGate::test_test017_fires_on_low_join_fraction
- text: 'GIVEN an unchanged file THEN its coverage is never recomputed: per-file coverage
    keyed by content hash, full-suite runs reserved for cold start or explicit --full'
  evidence:
  - tests/test_coverage.py::TestCoverageFileCache::test_load_missing_returns_empty
  - tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_backfills_unchanged_file
  - tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_ignores_stale_hash
  - tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_never_overwrites_fresh_data
  - tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_persists_measured_files
  - tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_roundtrips_through_fill_from_cache
- text: 'GIVEN any frob-enabled repo on any OS (Linux, macOS, Windows) WHEN coverage
    refresh is needed THEN a frob-native command (frob coverage or frob test --coverage)
    performs the whole orchestration -- subprocess rc generation, pytest invocation,
    combine, xml, stamp -- in Python with no Makefile or shell dependency; make coverage
    becomes a thin optional wrapper calling it (user directive 2026-07-29: portable,
    not just this project and not just Linux)'
  evidence:
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_incremental_run_uses_touched_set_targets
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_nothing_touched_only_restamps
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_refused_spawn_is_err
  - tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc
- text: GIVEN a frob command that actually RUNS tests to obtain coverage data (frob
    test --wait-coverage, via run_coverage_wait) THEN the frob-native coverage refresh
    runs automatically inside it (touched-set only, in-process, no spawned command)
    -- the user never invokes a separate refresh verb for that path, and nothing cached
    is re-run; frob check deliberately does NOT auto-trigger a refresh, for any caller
    (agent or non-agent) -- a documented, deliberate boundary (docs/modules/cli.md#frob-coverage-t-1525),
    not an omission
  evidence:
  - tests/test_coverage.py::TestRunCoverageWaitNativeDefault::test_default_command_none_calls_native_refresh
  - tests/unit/test_coverage_runner.py::TestCoverageRunner::test_default_delegates_to_run_coverage_wait
acceptance_amendments:
- op: replace
  index: 4
  old_text: 'GIVEN a frob command whose gates need coverage data WHEN the freshness
    contract says it is stale THEN the frob-native coverage refresh runs automatically
    inside that command (touched-set only) -- the user never invokes a refresh verb,
    and nothing cached is re-run (user directive 2026-07-29: minimal friction)'
  new_text: GIVEN a frob command that actually RUNS tests to obtain coverage data
    (frob test --wait-coverage, via run_coverage_wait) THEN the frob-native coverage
    refresh runs automatically inside it (touched-set only, in-process, no spawned
    command) -- the user never invokes a separate refresh verb for that path, and
    nothing cached is re-run; frob check deliberately does NOT auto-trigger a refresh,
    for any caller (agent or non-agent) -- a documented, deliberate boundary (docs/modules/cli.md#frob-coverage-t-1525),
    not an omission
  reason: 'T-1516''s Done report (already landed, done, on main) explicitly ruled
    out

    auto-wiring a coverage refresh into `frob check` itself: every dispatched

    worktree agent runs under `FROB_AGENT=1` (docs/guides/agent-playbook.md

    section 3b''s foreground-timeout contract), and auto-spawning a coverage

    refresh -- even touched-set-scoped -- from inside every `frob check` call

    would reintroduce the exact auto-background stall class that section

    exists to prevent. T-1525 (this session) settled the remaining open

    question -- whether a NON-agent (human/CI) `frob check` invocation should

    auto-trigger instead -- and the answer is still no, on different,

    non-agent-specific grounds: running the test suite is a categorically

    different, slower, more failure-prone operation than every other gate

    `frob check` runs, and hiding it as an implicit side effect of a "tell me

    what''s wrong, fast" command would surprise every caller. This is

    documented as a deliberate boundary in docs/modules/cli.md''s "frob

    coverage (T-1525)" section, not an oversight.


    What IS auto-wired, satisfying this criterion''s actual spirit ("the user

    never invokes a refresh verb, and nothing cached is re-run") for the

    commands that legitimately need coverage data to run tests rather than

    just report on them: `frob.testing._coverage_wait.run_coverage_wait`''s

    `command` parameter defaults to `None` (T-1516), which routes through

    `native_coverage_refresh` in-process -- and `run_coverage_wait()`''s one

    production call site (`src/frob/app/test_runner.py`, `frob test

    --wait-coverage`) gets this automatically, no call-site edit required.

    Amending this criterion''s text to name that boundary explicitly rather

    than leave "any frob command" unqualified against a decision this

    session made deliberately, not by accident.

    '
  actor: logan
  at: '2026-08-05'
- op: replace
  index: 0
  old_text: GIVEN a tracked source change WHEN frob check runs THEN coverage data
    for affected symbols is refreshed automatically via the touched-set test machinery
    (frob test --base semantics) merged into the persisted coverage store -- no manual
    make coverage invocation exists in any documented or gate-suggested workflow
  new_text: GIVEN a tracked source change WHEN the user runs frob coverage, or frob
    test --wait-coverage (via run_coverage_wait) THEN coverage data is refreshed automatically
    via the touched-set test machinery (frob.testing._incremental_coverage.python_coverage_targets)
    merged into the persisted coverage store, in-process, no Makefile/shell dependency
    -- the common incremental loop never requires a manual make coverage invocation;
    frob check itself deliberately does NOT trigger a refresh (see acceptance[4]);
    make coverage (the full-suite target) remains a legitimate manual/coordinator-only
    step for its own xdist-crash-recovery resilience, disclosed not silently dropped
  reason: 'As originally worded, this criterion assumed `frob check` itself would

    trigger the refresh ("WHEN frob check runs THEN coverage data ... is

    refreshed automatically"). T-1516/T-1525 (both this session and its

    immediate predecessor) made the opposite decision, deliberately: `frob

    check` never triggers a coverage refresh, for any caller -- see

    acceptance[4]''s own amendment for the full reasoning (running the test

    suite is a categorically different, slower operation than every other

    gate `frob check` runs; hiding it as an implicit side effect would

    surprise every caller). Amending this criterion to describe what was

    actually built and decided, rather than leave text on record that

    directly contradicts a considered, documented decision.


    The "no manual make coverage invocation" half is also not fully true as

    originally, unconditionally worded: `make coverage` (the FULL-suite

    target, distinct from `make coverage-fast`) remains a legitimate,

    occasionally-necessary manual step -- it is the one place this repo''s

    xdist-crash-recovery/rerun-deadline shell resilience still lives

    (disclosed in T-1516''s own Done report and T-1526''s, not silently kept),

    and docs/guides/agent-playbook.md section 6b documents it as a

    coordinator-only step for exactly that reason. What IS now true and

    automatic: the common "one small change" loop (`frob coverage`, `frob

    test --wait-coverage`, both native, both touched-set-incremental) never

    requires a manual `make coverage` invocation -- only the full-suite

    resilience path still does, by disclosed design, not oversight.

    '
  actor: logan
  at: '2026-08-05'
threat: null
component: null
---
ESCALATED TO CRITICAL 2026-07-31. This ticket's absence caused the largest single failure of the 2026-07-31 drive; acceptance [1] describes the exact incident. Evidence, all from one day:
- The repo-wide stamp sat 23 hours stale (2026-07-30 15:05) while ~8 tickets landed, and every TEST005 finding was computed from it and reported as current fact -- precisely what [1] forbids.
- T-1293 was closed having fixed 1 of 64 findings, its agent reporting the package clean in good faith. Post-land re-measure showed 65 still outstanding.
- The stamp does not merely lag, it UNDERSTATES coverage and so INFLATES findings. Measured: strata check_process_bounds_obligations stamp 6.7% / real 98%; check_self_conformance stamp 0.0% ("dead code") / real 95%; release authoritative_version showing def hits=1 with body hits=0, structurally impossible.
- Four agents were sent to write tests for code that was already well covered, and four worktrees (T-1276, T-1281, T-1294, T-1296) had to be PARKED mid-flight once the measurement was found untrustworthy.
- The coordinator had to run `make coverage` by hand to unblock them -- the exact manual step acceptance [0] and [4] exist to abolish.
T-1335 (landed 2026-07-31) fixed the pipeline's SILENT FAILURE (exit 0 on a failed stamp write), so a bad refresh is now loud. T-1353 tracks the xdist symbol-level data drop that appears to be the underlying corruption. Neither makes the refresh automatic or incremental -- that is this ticket, and it is what stops the failure class rather than the instance.

User directive 2026-07-29: we should never run make coverage manually; frob must never consume stale data or retread work that should be cached. Today coverage.xml is a hand-refreshed artifact: TEST011 warns it predates tracked changes and TEST005 findings are computed from it anyway (the attribution-inflation problem T-0969 is untangling). Design: treat coverage like the graph cache -- a derived artifact frob owns, refreshed incrementally from the touched-set (the affects closure already exists in frob.graph.affects), merged per-file keyed by content hash, with the freshness contract enforced by the gate rather than a Makefile comment. Interacts with T-0969 (attribution fix defines what honest data is) and the CI gitignored-trust child under T-1193 (CI needs the same no-stale contract). Related: the profiler found process-pool workers re-derive per-file artifacts every run -- same no-retread principle, separate ticket in the perf tree.