## Done report

T-1677 landed first and already substantially addressed T-1672's items 2
(a dead worker no longer discards a complete run -- `_pytest_outcome`'s
`_WORKER_CRASH_SIGNATURE_RE` match + one serial retry) and 3 (classify
environment abort vs real failure -- `_PytestPass.worker_crash`), per
the ticket's own body ("fold T-1672 into this if one implementation
covers both"). This ticket closes the remaining item 1.

Changed:
- src/frob/testing/_coverage_refresh.py:
  - `_pytest_argv` now appends an explicit `-n <count>` from
    `_compute_worker_count`, overriding `pyproject.toml`'s `addopts =
    "-n auto"` (pytest-xdist's `-n` is a plain argparse `store` option;
    the last occurrence wins).
  - `_available_memory_mb`: best-effort `/proc/meminfo` `MemAvailable`
    read (Linux only; `None` elsewhere -- no fabricated guess).
  - `_compute_worker_count` + its two split-out helpers
    (`_max_workers_override`, `_per_worker_mem_budget_mb`, kept under
    ARCH001's line threshold): caps the xdist pool at
    `min(cpu_count, available_memory_mb // per_worker_budget_mb)`.
    `FROB_COVERAGE_MAX_WORKERS` (0 = opt out, positive = pin exact) and
    `FROB_COVERAGE_PER_WORKER_MEM_MB` (default 1536) are the two
    disclosed knobs, matching T-1677's `COVERAGE_*_DEADLINE_S` precedent.
  - Also split `_spawn_with_watchdog` into `_start_watchdog_process` +
    `_watchdog_poll_loop`, and `_pytest_outcome`'s retry branch into
    `_retry_after_worker_crash` -- all three were over the ARCH001
    60-line threshold once the T-1672 additions landed on top of
    T-1677's own code; this is pure decomposition, no behavior change.
  - `frob:waive ARCH103` on `_kill_process_group` (one cohesive
    POSIX-vs-Windows teardown routine, same waiver shape as this repo's
    existing ARCH103 precedents) and `frob:waive SEC110` on the three
    new/pre-existing `os.environ.get` reads (all numeric knobs, no
    secrets).
- docs/modules/testing.md: new "Memory-aware xdist worker sizing"
  section.
- tests/test_coverage.py: `TestComputeWorkerCount` (9 tests) -- explicit
  override/opt-out, malformed-override fallback, memory-is-the-binding-
  constraint (the field incident's exact shape), unmeasurable-memory
  returns None not a guess, real `/proc/meminfo` parsing, and
  `_pytest_argv`'s `-n` wiring both ways.

Explicitly OUT of scope, left open on T-1672's own successor concern:
this fix is scoped to `native_coverage_refresh`'s own pytest invocation.
`frob test`'s general (non-coverage) runner does not build its own
pytest argv the way `_coverage_refresh.py` does and is a separate call
path this change does not touch -- checked `frob ticket list | grep -i
"worker\|xdist"` first, no existing ticket covers it, but it is not
filed here since the ticket's own priority ordering (item 1 lowest of
the three) and this session's time budget did not leave room to
investigate `frob test`'s call path with the same rigor.

Evidence: tests/test_coverage.py::TestComputeWorkerCount's 9 tests
(explicit override/opt-out, malformed override, memory-binding-
constraint, unmeasurable-memory, real /proc/meminfo parsing, -n wiring)
plus tests/test_coverage.py::TestSpawnWithWatchdog and
::TestPytestOutcomeWorkerCrashRecovery's 8 tests, bound because this
ticket's helper-extraction refactor (`_start_watchdog_process`/
`_watchdog_poll_loop`/`_retry_after_worker_crash`) moved those lines and
TEST016's mutation check treats moved lines as changed -- 17 ids total,
listed in full in the ticket's own recorded evidence.

Filed: none (grepped `frob ticket list` first; no duplicates).

Gates: `frob check --ticket T-1672` clean for this ticket's touched
set after fixes (gate:SCOPE/SEC/COV/ARCH all clean on
_coverage_refresh.py; the one remaining gate:ARCH error and the one
gate:DOC error are pre-existing, unrelated files -- gate:ARCH and
gate:DOC are repo-wide, not ticket-scoped, per the tool's own
scope-note). ruff-check/ruff-format/ty all clean on the touched files
directly. `frob test --base main` exit=0 (4 python tests, 0 failed) at
the final tree state.

### Changed
```
 docs/modules/testing.md               |  41 ++++
 rapid-debt.jsonl                      |   1 +
 src/frob/testing/_coverage_refresh.py | 420 +++++++++++++++++++++++++---------
 tests/test_coverage.py                | 109 +++++++++
 tickets.md                            | 176 +++++++++++++-
 5 files changed, 634 insertions(+), 113 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestComputeWorkerCount::test_explicit_zero_opts_out_entirely` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestComputeWorkerCount::test_explicit_positive_override_wins_over_memory` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestComputeWorkerCount::test_malformed_override_falls_back_to_memory_sizing` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestComputeWorkerCount::test_memory_is_the_binding_constraint` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestComputeWorkerCount::test_unmeasurable_memory_returns_none_not_a_guess` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestComputeWorkerCount::test_available_memory_mb_parses_real_proc_meminfo_shape` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestComputeWorkerCount::test_available_memory_mb_missing_file_returns_none` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestComputeWorkerCount::test_pytest_argv_appends_computed_n_flag` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestComputeWorkerCount::test_pytest_argv_omits_n_flag_when_unmeasurable` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestSpawnWithWatchdog::test_normal_completion_returns_exit_code_and_output` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestSpawnWithWatchdog::test_nonzero_exit_still_returns_ok_with_output` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_triggers_one_serial_retry` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_with_failing_retry_stays_degraded` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_ordinary_red_suite_is_not_classified_as_worker_crash` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 14 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
