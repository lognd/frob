## Done report

Lowered `_LAND_LOCK_TIMEOUT_S` from 600.0 to 500.0 seconds
(src/frob/tickets/_land.py) so it sits strictly BELOW the agent-playbook's
own mandated foreground shell-wrapper floor (`timeout 540`-580,
docs/guides/agent-playbook.md section 0 item 3 / section 3b).

Per the ticket's own explicit direction and T-1344's finding (agent-
playbook.md section 13), fixed by moving the LAND-side number down, not
by raising the shell-wrapper floor -- raising either number only makes a
genuinely stuck land take longer to surface. 500s still comfortably
covers the "two legitimate back-to-back land() calls" case this constant
exists for (T-1515), while guaranteeing `_land_lock`'s own
`LandLockTimeout` gets a real chance to fire and print a clean,
attributable refusal before an outer `timeout 540` wrapper would ever
need to SIGTERM the process -- closing the T-2032/T-2033 silent-land-
death mechanism this ticket describes.

Added a dedicated regression test,
`TestLandLockHolderMetadataAndTimeout::
test_lock_timeout_stays_below_the_playbook_shell_wrapper_floor`
(tests/test_ticket_land.py), asserting `_LAND_LOCK_TIMEOUT_S < 540.0`.
Confirmed via `frob ticket evidence --check-repro` that this test
genuinely fails against the pre-fix value (600.0, commit 385349e9c) and
passes after the fix.

Verification: `tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout`
(6 tests) all pass. No other code references `_LAND_LOCK_TIMEOUT_S`
(confirmed via `git grep`), so this is a self-contained, single-constant
change with no other callers to update.

### Changed
```
 src/frob/tickets/_land.py | 17 ++++++++++++++++-
 tests/test_ticket_land.py | 23 +++++++++++++++++++++++
 tickets/T-2065/ticket.md  | 13 +++++++++++--
 3 files changed, 50 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout::test_lock_timeout_stays_below_the_playbook_shell_wrapper_floor` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2065/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2065/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2065/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2065/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2065/tests/test_ticket_land.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2065, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
