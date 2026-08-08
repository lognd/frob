---
id: T-1572
title: 'frob coverage: add --base override, thread through make coverage-fast BASE='
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/coverage_runner.py
- src/frob/app/config.py
- src/frob/_cli_parsers/_misc.py
- tests/unit/test_app_runners*.py
- src/frob/testing/_coverage_wait.py
- tests/unit/test_coverage_wait*.py
- src/frob/app/_config_external.py
- tests/test_coverage.py
- tickets/T-1572/**
- tests/unit/test_coverage_runner.py
- docs/modules/cli.md
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/coverage_runner.py
  reason: 'identify actual implementation surface before failing: --base wiring needs
    both this runner/config AND _add_coverage_parser in src/frob/_cli_parsers/_misc.py,
    which is explicitly off-limits per dispatch'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/config.py
  reason: 'identify actual implementation surface before failing: --base wiring needs
    both this runner/config AND _add_coverage_parser in src/frob/_cli_parsers/_misc.py,
    which is explicitly off-limits per dispatch'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: add the CLI parser file needed to wire --base through (blocked in a prior
    attempt because another agent held it; that agent's series has since landed)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/coverage_runner.py
  reason: add the CLI parser file needed to wire --base through (blocked in a prior
    attempt because another agent held it; that agent's series has since landed)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/config.py
  reason: add the CLI parser file needed to wire --base through (blocked in a prior
    attempt because another agent held it; that agent's series has since landed)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_app_runners*.py
  reason: add the CLI parser file needed to wire --base through (blocked in a prior
    attempt because another agent held it; that agent's series has since landed)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/testing/_coverage_wait.py
  reason: run_coverage_wait (the default, non --full path frob coverage takes) never
    threads a base ref through to native_coverage_refresh at all -- --base is a no-op
    without this file; native_coverage_refresh's own base kwarg only affects touched-set
    selection, which --full bypasses entirely, so --base's only real effect is on
    this path
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_coverage_wait*.py
  reason: run_coverage_wait (the default, non --full path frob coverage takes) never
    threads a base ref through to native_coverage_refresh at all -- --base is a no-op
    without this file; native_coverage_refresh's own base kwarg only affects touched-set
    selection, which --full bypasses entirely, so --base's only real effect is on
    this path
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/_config_external.py
  reason: coverage_base needs wiring into _config_external.py's _STRING_FIELDS tuple
    like every other CLI dest
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_coverage.py
  reason: tests/test_coverage.py's _run_native_refresh callers need a base kwarg after
    threading --base through
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1572/**
  reason: add own ticket dir + the coverage_runner test file explicitly (mega-glob
    patterns didn't match them) + the two affects()-closure docs my diff touched
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_coverage_runner.py
  reason: add own ticket dir + the coverage_runner test file explicitly (mega-glob
    patterns didn't match them) + the two affects()-closure docs my diff touched
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/cli.md
  reason: add own ticket dir + the coverage_runner test file explicitly (mega-glob
    patterns didn't match them) + the two affects()-closure docs my diff touched
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/testing.md
  reason: add own ticket dir + the coverage_runner test file explicitly (mega-glob
    patterns didn't match them) + the two affects()-closure docs my diff touched
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_coverage_runner.py::TestCoverageRunner::test_default_delegates_to_run_coverage_wait
- tests/unit/test_coverage_runner.py::TestCoverageRunner::test_base_threads_through_to_run_coverage_wait
- tests/unit/test_coverage_runner.py::TestCoverageRunner::test_full_calls_native_refresh_directly
- tests/unit/test_coverage_runner.py::TestCoverageRunner::test_run_failure_exits_nonzero
designated_repro_test: null
threat: null
component: null
---
Refiled from worktree draft T-draft-a385ed9f (T-1526 follow-up; drafts cannot be cited by reports that must survive a land preview). make coverage-fast BASE=<ref> was honored by the old shell recipe but frob coverage currently hardcodes the touched-set base; add a --base flag and pass BASE through the Makefile wrapper.

## Failure log
- 2026-08-08 attempt 1: requires editing src/frob/_cli_parsers/_misc.py (_add_coverage_parser) to wire a --base CLI flag through to coverage_runner.run; that file is on the dispatch's explicit off-limits list held by another agent, so this cannot be implemented within my declared scope/constraints. Runner-side work (coverage_runner.py/config.py) is a small, mechanical addition once the flag exists; only the CLI parser edit is blocked.