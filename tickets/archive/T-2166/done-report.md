## Done report

Added "## --finish is pure cleanup when already landed (T-2108)" to
docs/modules/tickets-landing.md, right after the "Auto-sync after a
successful land" section (the module's own T-1780 split moved this
content out of docs/modules/tickets.md; tickets-landing.md is now the
correct home, matching the ticket's declared scope). The new section
frob:describes _ticket_terminal_state_on_main and
_finish_only_if_already_landed, and explains the distinction from
_check_already_landed/AlreadyLandedOnMain: that one refuses loudly on
an empty scope-diff for ANY land call; this one only fires for
--finish/--retire-on-proof, keys on terminal ledger STATE (not diff
emptiness), and succeeds quietly since --finish's whole point is
cleanup.

_finish_only_if_already_landed's body had drifted from its last
DRIFT001 ack independent of this ticket's own work; re-verified it
against the new doc section and ran `frob ack` on it since adding the
frob:describes edge made it newly relevant to this ticket's scope
closure.

### Changed
```
 tickets/T-2166/ticket.md | 7 ++++++-
 1 file changed, 6 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_terminal_on_main_skips_land_core_and_cleans_up` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_non_terminal_on_main_runs_the_normal_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2166/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2166/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2166/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2166/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2166/tests/test_ticket_land.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2166, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
