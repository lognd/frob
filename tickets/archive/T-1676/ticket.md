---
id: T-1676
title: Coverage refresh must not discard a whole run because the suite was red
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tests/test_coverage.py
- docs/modules/testing.md
- frob-coverage.lock.json
- src/frob/testing/_coverage_refresh.py
- design/frob.strata
- tickets-archive.md
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/testing/**
  reason: the fix lives in src/frob/testing/_coverage_refresh.py with its tests in
    tests/test_coverage.py and its contract documented in docs/modules/testing.md;
    frob-coverage.lock.json is the derived lock the refresh rewrites
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_coverage.py
  reason: the fix lives in src/frob/testing/_coverage_refresh.py with its tests in
    tests/test_coverage.py and its contract documented in docs/modules/testing.md;
    frob-coverage.lock.json is the derived lock the refresh rewrites
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/testing.md
  reason: the fix lives in src/frob/testing/_coverage_refresh.py with its tests in
    tests/test_coverage.py and its contract documented in docs/modules/testing.md;
    frob-coverage.lock.json is the derived lock the refresh rewrites
  actor: logan
  at: '2026-08-06'
- op: add
  glob: frob-coverage.lock.json
  reason: the fix lives in src/frob/testing/_coverage_refresh.py with its tests in
    tests/test_coverage.py and its contract documented in docs/modules/testing.md;
    frob-coverage.lock.json is the derived lock the refresh rewrites
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: src/frob/testing/**
  reason: 'narrow to the one module actually touched: the package glob pulled in _stability.py''s
    own test-closure obligations, which this ticket does not touch'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/testing/_coverage_refresh.py
  reason: 'narrow to the one module actually touched: the package glob pulled in _stability.py''s
    own test-closure obligations, which this ticket does not touch'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/testing/_incremental_coverage.py
  reason: tests/test_coverage.py is a shared test file covering three modules; scope
    closure requires both frob:tests targets even though this ticket edits neither
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/testing/_coverage_wait.py
  reason: tests/test_coverage.py is a shared test file covering three modules; scope
    closure requires both frob:tests targets even though this ticket edits neither
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/gitio.py
  reason: scope closure cascade from two monolithic shared doc anchors (docs/modules/testing.md#public-api
    and docs/modules/gates.md#coverage-as-managed-derived-state) that describe symbols
    across several modules; none of these files are edited by this ticket
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_app.py
  reason: scope closure cascade from two monolithic shared doc anchors (docs/modules/testing.md#public-api
    and docs/modules/gates.md#coverage-as-managed-derived-state) that describe symbols
    across several modules; none of these files are edited by this ticket
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/gates.md
  reason: scope closure cascade from two monolithic shared doc anchors (docs/modules/testing.md#public-api
    and docs/modules/gates.md#coverage-as-managed-derived-state) that describe symbols
    across several modules; none of these files are edited by this ticket
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: docs/modules/gates.md
  reason: 'reverting: adding this monolithic doc file pulled the entire gates package
    into scope closure (358 SCOPE errors); the single edge into it is handled at the
    directive instead'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/testing/**
  reason: 'restore the package glob: docs/modules/testing.md#public-api is a shared
    anchor describing every module in the package, so editing it requires the whole
    package in closure; tests/unit/testing/test_stability.py closes the test edge
    that glob brings with it'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/testing/test_stability.py
  reason: 'restore the package glob: docs/modules/testing.md#public-api is a shared
    anchor describing every module in the package, so editing it requires the whole
    package in closure; tests/unit/testing/test_stability.py closes the test edge
    that glob brings with it'
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: src/frob/testing/**
  reason: SCOPE002 is warn-tier; the broad globs added 130 closure warnings without
    changing what this ticket edits. Narrow to the four files actually touched
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: tests/unit/testing/test_stability.py
  reason: SCOPE002 is warn-tier; the broad globs added 130 closure warnings without
    changing what this ticket edits. Narrow to the four files actually touched
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: src/frob/gitio.py
  reason: SCOPE002 is warn-tier; the broad globs added 130 closure warnings without
    changing what this ticket edits. Narrow to the four files actually touched
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: tests/test_app.py
  reason: SCOPE002 is warn-tier; the broad globs added 130 closure warnings without
    changing what this ticket edits. Narrow to the four files actually touched
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: src/frob/testing/_incremental_coverage.py
  reason: SCOPE002 is warn-tier; the broad globs added 130 closure warnings without
    changing what this ticket edits. Narrow to the four files actually touched
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: src/frob/testing/_coverage_wait.py
  reason: SCOPE002 is warn-tier; the broad globs added 130 closure warnings without
    changing what this ticket edits. Narrow to the four files actually touched
  actor: logan
  at: '2026-08-06'
- op: add
  glob: design/frob.strata
  reason: the new provenance write is a real fs.write capability at the core node
    and the tests read it back at the testsuite node; both must be declared in the
    self-model
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tickets-archive.md
  reason: rebinding T-1205/T-1516's evidence off the renamed test writes the archive
    ledger
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/gates.md
  reason: 'AFFECT001: native_coverage_refresh''s affects()-closure doc anchor lives
    here and must be updated in the same change'
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_coverage.py::TestNativeCoverageRefresh::test_red_suite_keeps_coverage_data
- tests/test_coverage.py::TestNativeCoverageRefresh::test_refused_spawn_is_err
- tests/test_coverage.py::TestNativeCoverageRefresh::test_green_suite_records_not_degraded
designated_repro_test: null
threat: null
component: null
---
_run in src/frob/testing/_coverage_refresh.py treats ANY non-zero pytest exit as 'this produced nothing', and _run_full_suite/_run_targeted turn that into CoverageRefreshError.PytestFailed, discarding the run. coverage.xml is never rewritten.

This conflates two independent results: the suite VERDICT (did every test pass) and the coverage ARTIFACT (which lines did the tests that ran execute). A failing test does not invalidate the coverage recorded for the 8622 that passed. Observed 2026-08-06: a full run took 7m32s, 8622 of 8654 tests passed, one xdist worker was OOM-killed, and the refresh produced no artifact at all -- the second such loss that day.

Requirement (user directive, 2026-08-06): remove the all-passing-tests requirement on the coverage artifact.

Work:
1. Write the coverage data regardless of exit status -- failed tests, dead workers, INTERNALERROR, all of it.
2. Stamp the run's provenance: degraded=True plus failure count and cause (test failures vs worker death vs exec-refused), so every consumer can see what it is reading. A silently-accepted degraded artifact would just relocate the derived-artifact trap.
3. Constrain what a degraded run may do: it may RAISE a locked floor and CLEAR a violation (both safe directions), but must never lower a locked floor or be the sole basis for a NEW TEST005 violation, because a test that failed early stops contributing coverage and deflates its symbols.
4. Keep reporting the suite failure loudly and separately. It stays visible; it just no longer vetoes the artifact.

Related: T-1672 (worker death aborts the run and should be retried/classified) is the other half of the same incident; T-1389 already tracks per-symbol false-0.0% deflation detection, which item 3 must not duplicate.