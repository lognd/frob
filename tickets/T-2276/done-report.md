## Done report

Changed:
  scripts/fleet_status.py::scope_lease_collisions (added frob:waive PERF004)

Evidence: tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions::test_glob_scope_collides_with_a_literal_lease_file (bound to acceptance 0)
Filed: none
Gates: measured PERF004 finding on scripts/fleet_status.py:653 reproduced against current unscoped floor (`uv run frob check --only perf` before fix). After adding a reasoned frob:waive PERF004 (each collision's paths is a distinct per-collision overlap set, not a shared re-sort across iterations -- same posture as every other per-key-distinct-set PERF004 waiver already in this codebase), `uv run frob check --only perf --ticket T-2276` shows the scripts/fleet_status.py PERF004 identity is gone (gate:PERF errors dropped from 2 to 1, the remaining one being the unrelated _land_cmd.py PERF004 owned by T-2206). Targeted tests: tests/unit/test_coordinator_scripts.py -k ScopeLeaseCollisions, 7 passed.

### Changed
```
 tickets/T-2276/ticket.md | 7 ++++++-
 1 file changed, 6 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions::test_glob_scope_collides_with_a_literal_lease_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2276/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2276/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2276/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2276/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2276/tests/test_ticket_land.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2276, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
