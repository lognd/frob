---
id: T-1397
title: 'coverage-fast Makefile target points COVERAGE_PROCESS_START at pyproject.toml
  (relative source/data_file), same Loss-A shape T-1235 fixed for coverage:'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: 'The Makefile fix needs a regression test locking the recipe text and

    proving coverage-fast no longer points COVERAGE_PROCESS_START at

    pyproject.toml directly. tests/unit/test_makefile_coverage.py is the

    existing home for every other Makefile coverage-recipe regression test

    (parses the same _MAKEFILE text) -- a new test file would duplicate its

    fixtures.

    '
  actor: logan
  at: '2026-08-02'
evidence:
- tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_never_points_at_pyproject_toml
- tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc
- tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_rc_file_target_is_shared_not_duplicated
designated_repro_test: null
threat: null
component: null
---
Found while investigating T-1395 (coverage attribution for daemon/CLI processes).

Makefile's `coverage-fast` target (line ~305) points COVERAGE_PROCESS_START at
`$(CURDIR)/pyproject.toml` directly:

    COVERAGE_PROCESS_START=$(CURDIR)/pyproject.toml xargs uv run pytest --cov=src/frob ...

pyproject.toml's [tool.coverage.run] has `source = ["src/frob"]` (relative) and
no explicit `data_file` (defaults to a relative `.coverage`). This is exactly
the "Loss A" shape T-1235 fixed for the `coverage:` target by generating a
dedicated `.frob/coverage-subprocess.rc` with ABSOLUTE `source`/`data_file` --
`coverage-fast` was never given the same treatment, so any subprocess spawned
during a `coverage-fast` run (this is `run_coverage_wait`'s own default
command, `src/frob/testing/_coverage_wait.py::run_coverage_wait`) risks
silently losing/stranding subprocess coverage data exactly the way `coverage:`
used to before T-1235, whenever a child process's cwd differs from $(CURDIR).

Verified by reading the Makefile directly (T-1395 investigation, 2026-08-01);
not independently reproduced end-to-end since `coverage-fast` recurses into
`make coverage` on a cold `.coverage` (the common case in a fresh checkout)
masking the bug until a warm/incremental run actually takes the `xargs`
branch.

Fix: generate the same kind of absolute-path subprocess rc `coverage:`
already does (or reuse `.frob/coverage-subprocess.rc` if `coverage:` has
already run once) instead of pointing COVERAGE_PROCESS_START at
pyproject.toml directly.