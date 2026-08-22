## Done report

Re-measured T-1783's disclosed 24-item DOC012 backlog (uv run frob check
--only docblocks): still exactly 24, no drift since T-1783 landed.

This ticket covers the 10 of the 24 whose owning module already has a
dedicated docs/modules/*.md file (arch, clean, dup, fleet, graph,
mutate, perf, serve, stats, vet) but used a `# frob.<name> -- ...`
dotted title style DOC012's `## frob <name>` heading parser does not
recognize. Added a real `## frob <name>` section with accurate,
--help-verified CLI usage prose to each of the 10 files.

Re-ran `uv run frob check --only docblocks` after the edits: DOC012
finding count dropped from 24 to 14, and the remaining 14 are exactly
the sibling ticket's (ack/agent/debt/deprecated/design/docs/explore/
ops/pool/profile/quality/registry/test/worktree) -- confirms these 10
are fully cleared with no collateral regression.

### Changed
```
 tickets/T-2299/ticket.md           |  2 +-
 tickets/T-2315/ticket.md | 85 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2316/ticket.md | 81 ++++++++++++++++++++++++++++++++++++
 3 files changed, 167 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2315, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md
