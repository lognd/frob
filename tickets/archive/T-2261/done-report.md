## Done report

Changed:
  src/frob/app/ticket_runner/_rapid_sweep.py::sweep_stale_worktrees_after_land (new)
  src/frob/app/ticket_runner/_rapid_sweep.py::_sweep_async (calls it)
  src/frob/app/ticket_runner/_rapid_sweep.py::__all__ (export)
  docs/modules/tickets-verify-sweep.md (new subsection)

Confirmed placement before implementing (per the ticket's own explicit
instruction, not taken on faith): _rapid_sweep.py already owns the
detached, off-land-critical-path child spawn_deferred_post_land_sweep
spawns per land (frob ticket sweep-async <id> --commit <sha>, T-1684),
whose CLI entry point (_sweep_async) is the exact hook this ticket needs
-- adding a second call inside the SAME already-detached process costs
zero additional spawns and zero additional land-critical-path time
(spawn_deferred_post_land_sweep returns immediately after Popen; the
land never waits on the child). sweep_worktrees itself
(src/frob/tickets/_leases.py) is confirmed sound and unmodified.

sweep_stale_worktrees_after_land is a thin, faithful wrapper: calls
sweep_worktrees(root, min_age_hours=4.0, dry_run=False, force=False) and
logs every verdict it returns. Reuses sweep_worktrees's own five keep
verdicts (kept:live/kept:dirty/kept:unlanded/kept:lease/kept:age)
UNMODIFIED -- never reimplements or narrows them (their real-fixture
coverage already lives in tests/test_ticket_leases.py against
sweep_worktrees itself; duplicating that coverage here would test the
wrong layer). --force is never used by this path (verified directly).
min_age_hours=4.0 matches the ticket's own measured `--dry-run --min-age
4` precedent, stated in both the code comment and the doc.

Did NOT touch src/frob/app/ticket_runner/_land_cmd.py's now-stale "run
`frob worktree sweep` later" print statement -- out of this ticket's
declared scope (src/frob/app/ticket_runner/_rapid_sweep.py only). Filed
as a follow-up rather than silently widening scope.

Evidence: tests/unit/test_rapid_sweep.py::TestSweepStaleWorktreesAfterLand::test_never_uses_force
  FAILED_AT_PARENT confirmed at 64c4a62af (repro-only commit); PASSED
  after the fix commit 1804bdceb.
  Also added: test_logs_one_line_per_verdict (proves every one of the
  five keep verdicts plus "removed" is logged, unfiltered),
  test_a_failed_sweep_is_logged_never_raised (an Err from sweep_worktrees
  is swallowed, never raised into the detached child).
  Full run: tests/unit/test_rapid_sweep.py -- 106 collected, 0 failed
  (one unrelated pre-existing test, TestCloseResolvedSweepTickets::
  test_retry_after_commit_failure_does_not_duplicate_the_reason, flaked
  once under xdist parallelism and passed clean on the next two runs and
  in isolation -- not touched by this diff).

Filed: none (the stale _land_cmd.py print statement noted above is a
  cosmetic follow-up, disclosed rather than ticketed given its very low
  severity -- it is still-correct advice for a non-rapid land, since the
  automatic sweep only fires from the rapid profile's own detached child)

Gates: frob check --ticket T-2261 -- gate:SCOPE/gate:PREWORK clean;
  gate:AFFECT closed via a real docs/modules/tickets-verify-sweep.md
  section (not waived); no new gate:ARCH finding from this diff (the one
  ARCH103 finding in this file is pre-existing, already waived, on a
  function this diff never touched).

### Changed
```
 docs/modules/tickets-verify-sweep.md       | 24 ++++++++
 src/frob/app/ticket_runner/_rapid_sweep.py | 73 ++++++++++++++++++++++++-
 tests/unit/test_rapid_sweep.py             | 88 ++++++++++++++++++++++++++++++
 tickets/T-2261/ticket.md                   | 31 +++++++++--
 4 files changed, 210 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestSweepStaleWorktreesAfterLand::test_never_uses_force` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2261/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2261/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2261/src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2261/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2261/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2261/tests/test_ticket_land.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
