## Done report

Added the missing `frob sync-skills` row to README.md's Enforcement
command table (next to `frob claude`, its closest sibling: both are
config-sync commands replacing an old Makefile recipe) and bumped the
"N total commands" prose claim from 44 to 45, matching the live
top-level subcommand count (verified: `_build_parser()` yields 45
choices, sync-skills among them). Regenerated docs/modules/cli.md's
generated cli-commands block via `frob docs --sync-commands`, which
picked up the same missing sync-skills row mechanically. `gate:DOC`
(DOC005/DOC006) now reports 0 errors under `--only docblocks --ticket
T-2278` (was 2 errors per T-2268's triage). No code changes; docs-only
ticket, existing CLI-dispatch integration test bound as evidence per
playbook section 5.

### Changed
```
 tickets/T-2278/ticket.md | 6 +++++-
 1 file changed, 5 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2278/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2278/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2278/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2278/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2278/tests/test_ticket_land.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2278, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
