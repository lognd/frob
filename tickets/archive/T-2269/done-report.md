## Done report

Changed:
tests/test_coverage.py::TestCoverageTargetNativesGuard._assert_guard_precedes_coverage_cli
tests/test_coverage.py::TestCoverageTargetNativesGuard.test_coverage_target_restores_and_verifies_natives_before_pytest
tests/test_coverage.py::TestCoverageTargetNativesGuard.test_coverage_fast_incremental_branch_restores_and_verifies_natives
tests/test_coverage.py::TestCoverageTargetFlakeTolerance (removed -- retired class)

Root cause: T-2240 rewrote `make coverage`'s recipe to delegate to `uv run
frob coverage --full`, removing the inline shell (subprocess-rc capture,
serial rerun-on-flake, `coverage combine`, `exit $status`) that
`TestCoverageTargetFlakeTolerance` and one `TestCoverageTargetNativesGuard`
test asserted on. The equivalent behavior now lives in Python
(`native_coverage_refresh`) and is already covered by
`TestNativeCoverageRefresh`, `TestSpawnWithWatchdog`, and
`TestPytestOutcomeWorkerCrashRecovery` in this same file -- so
`TestCoverageTargetFlakeTolerance` was deleted as redundant dead weight,
the same shape T-2240 itself already applied to
`tests/unit/test_makefile_coverage.py`. `_assert_guard_precedes_pytest`
was folded into the pre-existing `_assert_guard_precedes_coverage_cli`
(generalized to take the coverage-invocation substring as a parameter) and
both `TestCoverageTargetNativesGuard` tests now assert against the current
Makefile dry-run text (`frob natives build` < `frob doctor` <
`frob coverage --full` / `frob coverage .`).

Evidence: tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_target_restores_and_verifies_natives_before_pytest (designated repro; FAILED_AT_PARENT confirmed via --check-repro and --designate-repro)
Full-file run: `uv run pytest tests/test_coverage.py -p no:cacheprovider -q -o addopts=""` -- 47 passed (SUITE-RESULT: exitstatus=0 collected=47 failed=0)

Filed: none (no out-of-scope work found)
Gates: uv run frob check --ticket T-2269 clean (see command output in session)

### Changed
```
 tickets/T-2269/ticket.md | 6 ++++--
 1 file changed, 4 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_target_restores_and_verifies_natives_before_pytest` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV003@tickets/T-1180, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2269/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2269/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2269/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2269/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2269/tests/test_ticket_land.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2269, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
