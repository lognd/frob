## Done report

Documented T-2071's fact-based root-contamination guard in
docs/commands/scaffold.md's install_worktree_lease_hook docstring
block, alongside the existing FROB_AGENT-keyed guard: it refuses a
commit made in the PRIMARY checkout while other worktrees exist and
staged files are not limited to tickets.md/tickets/**, unless
FROB_LAND_INTERNAL=1 covers it. No code changes; docs-only ticket,
existing test coverage for the described guard is bound as evidence
per playbook section 5.

### Changed
```
 tickets/T-2119/ticket.md | 6 +++++-
 1 file changed, 5 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_agent_context_root_write_refused_without_frob_agent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2119/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2119/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2119/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2119/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2119/tests/test_ticket_land.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
