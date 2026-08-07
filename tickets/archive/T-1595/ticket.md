---
id: T-1595
title: 'Stale test assertions: coverage-fast Makefile dry-run + PERF001 fixture below
  TEST002 threshold'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/**
- src/frob/app/coverage_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_fast_incremental_branch_restores_and_verifies_natives
- tests/system/test_cli_perf.py::TestCheckOnlyPerf::test_perf001_fixture_warns_but_check_exits_zero
designated_repro_test: null
threat: null
component: null
---
tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_fast_incremental_branch_restores_and_verifies_natives
fails deterministically (confirmed in isolation, independent of xdist/
worker order) -- it dry-runs `make -n coverage-fast` and asserts a
"pytest --cov" substring appears after the "make core"/"frob doctor"
guard, but the real recipe's expansion no longer contains that literal
(observed: it now runs `uv run frob coverage .` instead). Found while
investigating T-1591 (shared-state pollution); this is NOT a pollution
bug, and the Makefile itself is outside T-1591's scope (tests/**,
src/frob/lang/**, src/frob/serve/**, src/frob/app/**) to fix -- the test's
assertion needs to be updated to match whatever the coverage-fast recipe
now actually invokes, or the recipe needs to keep a raw pytest --cov
invocation if that was a deliberate guarantee. Needs someone who owns
Makefile/coverage tooling to decide which side is correct.

Also found in the same investigation:
tests/system/test_cli_perf.py::TestCheckOnlyPerf::test_perf001_fixture_warns_but_check_exits_zero
also fails deterministically in isolation: its fixture repo's test file
has only 1 collected unit case for the function under test, and TEST002
now requires min_unit_cases=3 (was presumably a lower or absent threshold
when this fixture was written). Needs the fixture's test_pkg.py updated
to add 2 more unit cases, or confirmation TEST002's threshold change was
intentional and this is simply a stale fixture.