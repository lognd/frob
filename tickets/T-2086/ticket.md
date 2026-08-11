---
id: T-2086
title: 'frob coverage''s xdist worker-crash retry still cannot recover: pytest''s
  own config addopts re-injects -n/--dist after T-2032''s argv strip'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/testing/_coverage_refresh.py
- tests/test_coverage.py
- tickets/T-2087/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-2087/ticket.md
  reason: residue ticket filed by this ticket's own investigation, needed for the
    land's touched-set
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_coverage.py::TestNeutralizedAddopts::test_neutralizes_xdist_tokens_from_a_real_pyproject_toml
- tests/test_coverage.py::TestNeutralizedAddopts::test_returns_none_when_addopts_has_no_xdist_tokens
- tests/test_coverage.py::TestNeutralizedAddopts::test_returns_none_when_pyproject_toml_is_missing
- tests/test_coverage.py::TestNeutralizedAddopts::test_retry_argv_carries_the_override_when_addopts_has_xdist_tokens
- tests/test_coverage.py::TestWorkerCrashRetryRealSubprocessRecoversFromAddopts::test_real_pytest_subprocess_recovers_and_produces_coverage_xml
designated_repro_test: tests/test_coverage.py::TestWorkerCrashRetryRealSubprocessRecoversFromAddopts::test_real_pytest_subprocess_recovers_and_produces_coverage_xml
threat: null
component: null
anchor: false
anchor_reason: null
---
## Problem

T-2032 fixed the explicit `-n <N>` flag in `_retry_after_worker_crash`'s
retry argv (stripped before appending `-p no:xdist`), and that half works:
verified on landed main (`eea3ffcc81c0`), the retry now spawns
`['pytest', '--cov=src/frob', '--cov-report=', '-p', 'no:xdist']` with no
explicit `-n`.

`frob coverage --full` still cannot recover from a worker-crash retry.
The recovery path still exits 4 and never runs a test.

## Root cause: pytest merges config `addopts` into every invocation

`pyproject.toml:171`:

    addopts = "-q -n auto --dist=loadgroup --timeout=120 --timeout-method=thread"

pytest appends this to EVERY invocation's argv, including the retry's.
Stripping `-n`/its value from the explicit argv T-2032 built is not enough:
`-n auto --dist=loadgroup` still arrives via `addopts`, and with `-p
no:xdist` disabling the plugin, pytest no longer recognises them --
usage error, exit 4, no test ever runs. Same failure shape as before,
different source for the offending flags.

## Measured evidence (2026-08-10, worktree checkout of landed main)

Direct repro, `pyproject.toml:171`'s addopts in effect:

    $ uv run pytest --collect-only -q -p no:xdist tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
    ERROR: usage: pytest [options] [file_or_dir] [file_or_dir] [...]
    pytest: error: unrecognized arguments: -n --dist=loadgroup tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
      inifile: /home/logan/projects/frob/.claude/worktrees/t-2032-addopts/pyproject.toml
      rootdir: /home/logan/projects/frob/.claude/worktrees/t-2032-addopts

Coordinator's `frob coverage --full` run on landed main showed the same
shape at the orchestration level -- retry argv correctly stripped of the
explicit `-n`, message correctly reports the T-1664 unmeasurable-exit
shape, and it STILL exits 4 because `-n auto --dist=loadgroup` re-enters
via `addopts`, invisible to any code that only inspects the argv list it
built itself.

## Blast radius

Same as T-2032: `frob coverage --full` is unusable on any machine where
the parallel run OOMs, which directly blocks T-1953 (the TEST005
coverage-floor ratchet) -- it needs a coordinator-run full-coverage
measurement and still cannot get one.

## T-2032's own criterion-3 test passed while the real command still failed

T-2032's acceptance criterion 3 test
(`tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery`)
exercises `native_coverage_refresh` with `_spawn` MOCKED -- it asserts the
retry argv has no `-n` and that the mocked call returns 0, then asserts
`coverage.xml`'s production path is reached. That is a real, correct unit
test of the ARGV-BUILDING code, but it can never see `addopts` at all: no
real pytest process is ever invoked, so pytest's own CLI-plus-config
merging step (which is where the remaining `-n auto --dist=loadgroup`
actually enters) is entirely outside what the mock can exercise. The test
passed and the real, unmocked `frob coverage --full` command still failed
end to end -- worth stating plainly: a unit-level "recovery" test at
`native_coverage_refresh` is NOT sufficient evidence that the real CLI
command recovers, because it structurally cannot see anything pytest
itself contributes to the final argv (config-file addopts chief among
them). This ticket's acceptance criterion 3 must be a real end-to-end
`frob coverage --full` invocation with the first parallel attempt forced
to fail, checking that `coverage.xml` is actually produced by the real
subprocess -- not a mocked one.

## Likely shape (establish this by running the command, not by reasoning about it)

The retry likely needs to neutralise `addopts` explicitly rather than
merely omit an explicit `-n` -- e.g. `-o
addopts="-q --timeout=120 --timeout-method=thread"` re-specifying only the
xdist-independent options from `pyproject.toml:171`'s current value, so
the retry's effective argv carries no worker-count/dist flags from EITHER
source (explicit argv or config `addopts`). Confirm the exact working
shape empirically against a real `frob coverage --full` run with a forced
worker-crash signature, not by inspecting argv alone.

## Do NOT fix it this way

- Do NOT edit `pyproject.toml`'s `addopts` to remove `-n auto
  --dist=loadgroup` globally -- that would slow every healthy (non-crash)
  run by disabling parallelism for everyone, the same "makes the crash
  rarer without making recovery work" trap T-2032 already ruled out for
  the worker-count default.
- Do NOT special-case exit 4 further into a silent pass -- T-2032's
  message fix (report it honestly as unmeasurable) must stay intact; this
  ticket is about making the retry actually run tests, not about
  softening how its failure is reported.

## Acceptance criteria

1. A test (unit or integration) demonstrating the retry argv/config no
   longer carries ANY xdist worker-count/dist flag (from explicit argv OR
   `addopts`) once `-p no:xdist` is added. Must fail before the fix.
2. An END-TO-END check: a real, unmocked `frob coverage --full` invocation
   with the first parallel pytest attempt forced/observed to fail with the
   worker-crash signature must actually produce `coverage.xml`. Mocking
   `_spawn`/`native_coverage_refresh` alone does not satisfy this
   criterion -- see this ticket's own "T-2032's own criterion-3 test
   passed while the real command still failed" section for why.