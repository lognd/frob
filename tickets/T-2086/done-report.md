## Done report

Changed:
- src/frob/testing/_coverage_refresh.py::_strip_xdist_tokens (renamed/extended
  from T-2032's `_strip_worker_count_flag`; now also strips `--dist`/`--tx`)
- src/frob/testing/_coverage_refresh.py::_XDIST_DIST_FLAGS (new)
- src/frob/testing/_coverage_refresh.py::_neutralized_addopts (new)
- src/frob/testing/_coverage_refresh.py::_retry_after_worker_crash (extended:
  now also applies `-o addopts=<neutralized>` when pyproject.toml's addopts
  carries an xdist token)

Root cause confirmed by measurement (not by reasoning about it, per the
coordinator's directive): a plain `uv run pytest --collect-only -q -p
no:xdist ...` against this repo's real `pyproject.toml` (addopts = "-q -n
auto --dist=loadgroup --timeout=120 --timeout-method=thread") reproduced
the exact exit-4 usage error even with NO explicit `-n` in the CLI argv --
confirming addopts' own `-n auto --dist=loadgroup` was the second injection
source. The fix (`-o addopts="-q --timeout=120 --timeout-method=thread"`)
was verified the same way before being wired into the module: same
collect-only invocation, exit 0, 1 collected.

Evidence:
- tests/test_coverage.py::TestNeutralizedAddopts::test_neutralizes_xdist_tokens_from_a_real_pyproject_toml
- tests/test_coverage.py::TestNeutralizedAddopts::test_returns_none_when_addopts_has_no_xdist_tokens
- tests/test_coverage.py::TestNeutralizedAddopts::test_returns_none_when_pyproject_toml_is_missing
- tests/test_coverage.py::TestNeutralizedAddopts::test_retry_argv_carries_the_override_when_addopts_has_xdist_tokens
  (acceptance criterion 1; FAILED_AT_PARENT confirmed via `frob ticket
  evidence --check-repro --base-ref 69ebd566883902c319cb4b35aeae6ac170dfd32b`,
  the test-only commit; also watched fail directly under plain pytest before
  the fix: `assert '-o' in ['pytest', '-p', 'no:xdist']` -> AssertionError)
- tests/test_coverage.py::TestWorkerCrashRetryRealSubprocessRecoversFromAddopts::test_real_pytest_subprocess_recovers_and_produces_coverage_xml
  (designated repro; acceptance criterion 2, END-TO-END with a REAL
  unmocked pytest subprocess against a real scratch pyproject.toml carrying
  this repo's exact addopts shape, through the real `_retry_after_worker_crash`
  AND a real `coverage xml -i` call, asserting `coverage.xml` actually
  exists on disk afterward. FAILED_AT_PARENT confirmed the same way;
  observed pre-fix failure: `assert retry_code == 0` -> `assert 4 == 0`)

All 5 pass post-fix; the broader worker-crash/native-refresh test set (19
tests across `TestWorkerCrashRetryArgvStripsWorkerCount`,
`TestWorkerCrashRetryUnmeasurableExitReporting`,
`TestPytestOutcomeWorkerCrashRecovery`, `TestNativeCoverageRefresh`,
`TestNeutralizedAddopts`, and this ticket's new end-to-end class) all pass
together -- T-2032's original fix and this follow-up compose cleanly.

On why criterion 2 is real-subprocess rather than routed through
`native_coverage_refresh`'s own auto-detection: forcing a genuine worker
crash (`os._exit`, `SIGKILL`) inside a real pytest-xdist run on this
repo's pinned pytest-xdist version produces `worker 'gwN' crashed while
running '...'`, which does NOT match `_WORKER_CRASH_SIGNATURE_RE`
(measured directly; the regex expects `worker\s+gw\d+\s+crashed`, i.e. an
unquoted `gwN` immediately after "worker", but the real message quotes
it). That is a separate, real defect in the DETECTION regex, unrelated to
this ticket's argv/addopts recovery bug, and out of this ticket's scope --
filed as T-2087 rather than folded in or fixed silently. Given
that gap, the most faithful "real, unmocked pytest invocation" achievable
here calls `_retry_after_worker_crash` directly (the exact recovery code
path a working detector would invoke) against a real scratch project and
a real subprocess, and confirms `coverage.xml` is actually produced --
this satisfies "the real CLI command's recovery mechanism, exercised for
real, produces the artifact it's supposed to," which is the property that
matters; it does not additionally re-verify signature detection, which is
T-2087's job.

Filed:
- T-2087 -- `_WORKER_CRASH_SIGNATURE_RE` may not match this
  repo's pinned pytest-xdist's real crash message (measured, see above).
  NOT folded into this ticket; NOT fixed here.

Gates: `uv run frob check --ticket T-2086 --only lint` clean for
both scoped files (0 ruff-check errors, 0 ruff-format diffs in
src/frob/testing/_coverage_refresh.py / tests/test_coverage.py; the run's 2
repo-wide errors and 122 warnings are all in files outside this ticket's
scope, pre-existing, same two F401s already present before this ticket).
`frob ticket evidence --check-repro` confirmed FAILED_AT_PARENT for both
new-behavior tests before designating/landing, per playbook 7b's
test-only-commit technique.

Not run: full unscoped `frob check`/`make coverage`/the whole
tests/test_coverage.py file in one pytest invocation -- exceed the
foreground timeout budget (playbook 3b/3c); collection of the whole file
was verified clean instead (49 collected, 0 errors), and the relevant
classes were run directly and pass (19/19).

### Changed
```
 src/frob/testing/_coverage_refresh.py | 129 ++++++++++++++++++++++++++------
 tests/test_coverage.py                | 137 ++++++++++++++++++++++++++++++++++
 tickets/T-2087/ticket.md    |  86 +++++++++++++++++++++
 tickets/T-2086/ticket.md    | 133 +++++++++++++++++++++++++++++++++
 4 files changed, 463 insertions(+), 22 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestNeutralizedAddopts::test_neutralizes_xdist_tokens_from_a_real_pyproject_toml` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNeutralizedAddopts::test_returns_none_when_addopts_has_no_xdist_tokens` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNeutralizedAddopts::test_returns_none_when_pyproject_toml_is_missing` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNeutralizedAddopts::test_retry_argv_carries_the_override_when_addopts_has_xdist_tokens` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestWorkerCrashRetryRealSubprocessRecoversFromAddopts::test_real_pytest_subprocess_recovers_and_produces_coverage_xml` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, DOC005@README.md, DOC005@docs/modules/cli.md, DRIFT002@src/frob/app/ticket_runner/_rapid_sweep.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2032-addopts/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2032-addopts/tests/unit/test_tickets_evidence_only_scope.py, PII012@src/frob/testing/_coverage_refresh.py, PRE001@tickets/T-2086, SELFAUDIT001@design
