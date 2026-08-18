## Done report

Advisory concurrency reporting for frob check (T-2473), the coordinator's
chosen direction over an enforced global limit: an enforced cap risks
turning a busy fleet into a queue of stalled agents if the cap is chosen
badly, and this repo consistently prefers surfacing over commanding.

Two pieces:

- src/frob/process/_reap.py: new count_running_checks(proc, self_pid) --
  a /proc scan matching a live frob check process by its frob/check argv
  token pair as SEPARATE tokens (never a substring, so frob ticket
  check-repro or a path containing "check" never false-positives).
  Excludes self_pid so a single check on an idle machine reads 0 others.
  Returns None (never a fabricated zero) on an unreadable /proc, mirroring
  orphaned_forkserver_count's own contract exactly.
- src/frob/__main__.py: new _report_concurrent_check_advisory_best_effort,
  called at the same startup seam as T-2443's forkserver reap, right
  before a check subcommand dispatches. Logs at INFO when others ARE
  running (visible in a normal log-level run without -v), WARNING at 4 or
  more (this host's own measured degradation point), and logs nothing at
  0 -- an idle machine's check gets no extra log noise. Best-effort and
  NEVER fatal: any exception is caught, logged at DEBUG, swallowed --
  same posture as the forkserver reaper immediately above it.
- scripts/fleet_status.py: new concurrent_check_count (duplicated /proc
  matcher in plain form, this script's own "no frob import" contract,
  same posture orphaned_forkserver_count already takes for T-2443), wired
  into _land_status_lines/_print_land_status as a new
  "CONCURRENT CHECKS: N (T-2473, advisory)" line alongside the existing
  swap/orphaned-forkserver lines -- acceptance [3], the cheap one, done
  regardless of which direction was chosen.

ACCEPTANCE:
[0] concurrent-check count is accurately reported (advisory variant,
    not bounded) -- count_running_checks/concurrent_check_count both
    verified against synthetic /proc fixtures matching real cmdline/
    frob-check shape.
[1] a single check on an idle machine gains no latency, no new failure
    mode -- the advisory call is read-only (/proc scan, no lock, no
    subprocess), wrapped in try/except that swallows any failure
    (test_never_raises_on_a_broken_count proves this directly), and logs
    NOTHING when the count is 0, so an idle machine's check output is
    byte-identical to before this change.
[2] a queued/refused check must be visibly deferred, not silently
    skipped -- vacuously satisfied: the advisory variant never queues or
    refuses a check, so there is no deferral case to hide. Recorded
    explicitly in docs/modules/process.md's new section so a future
    enforced-limit direction knows it still owes this.
[3] fleet_status.py reports concurrent check count alongside swap/
    orphaned-forkserver -- done (see above), verified via
    TestConcurrentCheckCount and a direct read of _land_status_lines'
    new CONCURRENT CHECKS line.

Docs: docs/modules/process.md gained a new "Concurrent check advisory
(T-2473)" section (explicitly distinguishing this from T-2443's leak
fix); docs/guides/coordinator-scripts.md gained a concurrent_check_count
section plus updated _land_status_lines/_print_land_status prose.

Verified: full affected suites re-run clean --
tests/unit/test_process_reap.py + tests/unit/test_coordinator_scripts.py
+ tests/unit/test_main_entry.py = 186 passed, 0 failed. frob check --only
ruff clean on every touched file after frob fmt (0 files needed
reformatting on the second pass).

Filed: none.

### Changed
```
 docs/guides/coordinator-scripts.md     |  31 ++++++++-
 docs/modules/process.md                |  52 +++++++++++++++
 scripts/fleet_status.py                |  69 +++++++++++++++++++-
 src/frob/__main__.py                   |  49 +++++++++++++-
 src/frob/process/_reap.py              |  82 ++++++++++++++++++++++-
 tests/unit/test_coordinator_scripts.py |  31 +++++++++
 tests/unit/test_main_entry.py          |  51 +++++++++++++++
 tests/unit/test_process_reap.py        |  41 ++++++++++++
 tickets/T-2473/ticket.md               | 115 +++++++++++++++++++++++++++++++--
 9 files changed, 509 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/test_process_reap.py::TestCountRunningChecks::test_counts_other_check_processes` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestCountRunningChecks::test_excludes_self` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestCountRunningChecks::test_ignores_non_check_processes` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestCountRunningChecks::test_missing_proc_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestConcurrentCheckCount::test_counts_check_processes` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestConcurrentCheckCount::test_ignores_non_check_processes` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestConcurrentCheckCount::test_missing_proc_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_no_other_checks_logs_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_other_checks_logs_info_below_four` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_four_or_more_checks_logs_warning` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_never_raises_on_a_broken_count` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/process/_reap.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@docs/modules/process.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC002@src/frob/process/_reap.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2473/src/frob/app/ticket_runner/_waive_audit.py, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2473, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
