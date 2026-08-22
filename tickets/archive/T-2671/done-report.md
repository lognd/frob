## Done report

Changed:
- src/frob/app/ticket_runner/_rapid_sweep.py::_persist_commit_step_failure (new)
- src/frob/app/ticket_runner/_rapid_sweep.py::_RAPID_DEBT_FAILURE_LOG_PREFIX (new)
- src/frob/app/ticket_runner/_rapid_sweep.py::_commit_rapid_debt (all three
  failure branches now call _persist_commit_step_failure)

Scope: this ticket's first task is observability, not a fix, per the
ticket's own instruction ("a concurrency fix built on an unconfirmed
hypothesis is how this repo got two mechanisms for one problem before").
T-2669's fix (_land_internal_git_env around the commit spawn) is
untouched.

## Reproduction attempts

**Real recurrence (546ddf39c, 16:36:59):** could NOT be further diagnosed
retroactively -- the land invocation's own stderr from that run was never
retained anywhere (frob.logging installs no file handler; a foreground
`frob ticket land` invocation's terminal output is gone once the terminal
closes), and the detached post-land sweep log is silent about this step
because it runs in a different, later process. This confirms the ticket's
own diagnosis: the blocker was evidence, not analysis.

**Deliberate reproduction of the leading hypothesis (concurrent-write
contention), via a scratch probe (not committed, /tmp only) running two
threads calling `_commit_rapid_debt` concurrently against the SAME seeded
repo:** reproduced cleanly and repeatably. Of 5 attempts, every one
produced a genuine git-level race between the two `add`/`commit` spawns
(interleaved `status`/`add`/`commit` calls from both threads racing on
the same `rapid-debt.jsonl`), and 1 of 5 left the root in the exact
DirtyMain-precursor state (`A  rapid-debt.jsonl` staged but uncommitted)
the ticket describes -- both losing threads in that attempt failed at
`add`/`commit` respectively. Every failure in all 5 attempts produced a
retained diagnostic log under `.frob/rapid-sweep/`. This is a reproduction
of the underlying git-race MECHANISM at the function level (two racing
callers of `_commit_rapid_debt` on one root), not a reproduction via two
full `frob ticket land` subprocess invocations against the real shared
fleet root -- deliberately not attempted, since orchestrating two real
concurrent lands against the live shared root risked interfering with
the other agents' work in flight during this session.

Conclusion: the concurrency hypothesis is CONFIRMED REACHABLE at the
mechanism level (concurrent writers to rapid-debt.jsonl can race past
each other's read-decide-write and leave one side's commit refused with
no atomic retry), even though the specific real-fleet recurrence at
16:36:59 cannot be retroactively attributed to it with certainty --
that attribution requires the NEXT occurrence's own retained diagnostic
log, which this ticket's instrumentation now provides.

## Instrumentation added

`_persist_commit_step_failure(root, ticket_id, step, outcome)`: on any of
`_commit_rapid_debt`'s three git steps (status/add/commit) failing,
writes a JSON diagnostic file to `.frob/rapid-sweep/rapid-debt-commit-
failure-<ticket_id>-<timestamp>.log` containing the full outcome --
argv/returncode/stdout/stderr for a spawned-but-failed process, or the
GitError name for a spawn that never ran at all. This is the same
directory a detached sweep's own stdout/stderr already survives in
(`_LOG_DIR_REL`), for the same reason: a foreground land invocation's own
terminal output is retained nowhere by default. Best-effort: a failure
writing the diagnostic itself is swallowed and logged separately, never
allowed to become a second failure layered on the one it explains.

## Positive controls, both directions

- A single uncontended rapid land still commits its own rapid-debt line
  with zero behavior change: `TestCommitRapidDebt::test_leaves_the_repo_
  clean` (pre-existing, still green) plus this ticket's own probe run
  (non-DirtyMain attempts 1-4 of 5 all landed one thread's commit
  cleanly).
- The DirtyMain guard still fires for genuinely unexpected root content:
  `TestCommitRapidDebt::test_guard_still_refuses_a_genuinely_foreign_file`
  (pre-existing, still green, unaffected by this change).
- After the fix, a commit-step failure now leaves a retained diagnostic:
  `TestCommitRapidDebt::test_commit_failure_persists_a_diagnostic_log`
  (new, designated repro, FAILED_AT_PARENT at 59a82c57d) -- reproduces
  the T-2669-shaped hook refusal directly and asserts a diagnostic file
  with the real stderr text now survives it.

Evidence:
- tests/unit/test_rapid_sweep.py::TestCommitRapidDebt::test_commit_failure_persists_a_diagnostic_log (designated repro, FAILED_AT_PARENT at 59a82c57d)
- tests/unit/test_rapid_sweep.py::TestPersistCommitStepFailure::test_writes_proc_result_diagnostics
- tests/unit/test_rapid_sweep.py::TestPersistCommitStepFailure::test_writes_spawn_error_diagnostics
- tests/unit/test_rapid_sweep.py::TestPersistCommitStepFailure::test_swallows_its_own_write_failure

Filed: none (no out-of-scope work found)

Gates: frob check --ticket T-2671 clean re gate:SCOPE (after adding
tests/unit/test_rapid_sweep.py to scope, --reason recorded via `frob
ticket scope --add`) and gate:PRE (re-swept after the scope widen). `ty`
clean (0 issues, after typing `_persist_commit_step_failure`'s outcome
parameter as `Result[Any, Any]`). All other FAIL lines in the ticket-
scoped unscoped-gate counts (DRIFT, PERF, COV, TICK, etc.) are
pre-existing repo-wide baseline findings unrelated to _rapid_sweep.py,
confirmed via gate:scope-note disclosure and by their file paths lying
entirely outside this ticket's scope.

### Changed
```
 rapid-debt.jsonl                           |   1 +
 src/frob/app/ticket_runner/_rapid_sweep.py | 111 +++++++++++++++++++++-
 tests/unit/test_rapid_sweep.py             | 143 +++++++++++++++++++++++++++++
 tickets/T-2671/done-report.md              | 117 +++++++++++++++++++++++
 4 files changed, 368 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestPersistCommitStepFailure::test_writes_proc_result_diagnostics` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestPersistCommitStepFailure::test_writes_spawn_error_diagnostics` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestPersistCommitStepFailure::test_swallows_its_own_write_failure` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCommitRapidDebt::test_commit_failure_persists_a_diagnostic_log` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 36 error(s), 806 warning(s), 697 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
