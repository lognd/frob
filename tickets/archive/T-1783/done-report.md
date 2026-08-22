## Done report

Implemented DOC012 (frob.gates._docblocks.doc012_gate): for every
top-level subcommand the live `[[docblocks.commands]]`-configured
registry (the same `_console_command_sources`/`_console_trees` walk
DOC004/DOC005 already use) exposes, requires at least one dedicated
`## `-level (or deeper) markdown heading somewhere under
docs/commands/ or docs/modules/ naming it -- a DOC005 command-table
row mention alone does not satisfy it. Shipped at WARN severity
(T-0688 new-gate-at-WARN precedent, same posture DOC006 used): this
repo carries real, disclosed DOC012 debt at ship time (measured 24
top-level subcommands with no dedicated section), so an immediate
ERROR would red every unrelated land fleet-wide over pre-existing
content, not new drift this ticket introduces.

Registered "DOC012" in frob.gates._waive._KNOWN_GATE_RULES, wired
doc012_gate into the "docblocks" gate group in frob.gates.__init__,
documented the rule in docs/modules/gates.md (rule table row plus a
full "DOC012 dedicated command-section drift-lock" section disclosing
the 24-command debt list), and added the frozenset entry to gates.md's
frob:enumerates directive so DOCENUM001 stays clean.

T-1682 (filed by T-1610) remains the CONTENT fix for frob coverage
specifically; this ticket is the MECHANISM only and writes no doc
section itself. The 24 other subcommands' own sections are burn-down
work, not this ticket's scope -- each is a candidate follow-up ticket
if/when someone wants to clear the WARN backlog; none is filed here
since T-1783's own acceptance was the rule's existence, not the
backlog's exhaustion, and filing 24 near-duplicate one-line follow-ups
would be more debt than the WARN backlog itself.

### Changed
```
 tickets/T-1783/ticket.md | 42 ++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 40 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDoc012CommandSectionGate::test_undocumented_subcommand_fails` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDoc012CommandSectionGate::test_documented_subcommand_passes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDoc012CommandSectionGate::test_table_row_alone_does_not_satisfy` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDoc012CommandSectionGate::test_no_config_means_no_checking` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, DUP001@tests/test_gates.py, E402@/home/logan/projects/frob/.claude/worktrees/t-1783/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1783/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1783/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-1783/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-1783/tests/test_ticket_land.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-1783, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md, WIRE001@tests/test_gates.py
