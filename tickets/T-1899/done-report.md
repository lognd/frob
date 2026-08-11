## Done report

Added the T-1892 EvidenceCmdSilent note to docs/modules/tickets.md's
cmd: evidence section, right after the existing EvidenceCmdFailed
sentence: a command whose captured stdout+stderr is empty is refused
even on exit 0, with the recommendation to prefer a chatty check
(grep -c/grep -n) over a silent one (grep -q). Cites T-1892.

Ran `frob ack src/frob/tickets/_evidence.py::run_cmd_evidence
src/frob/tickets/_evidence.py::add_cmd_evidence` to refresh both
symbols' digests against the updated doc.

docs/modules/tickets.md was NOT under any live lease at the start of
this ticket (T-1883, named in the ticket body as the original blocker,
had already released it).

### Changed
```
 tickets/T-1899/ticket.md |  6 +++++-
 tickets/T-1952/ticket.md | 14 +++++++++++++-
 tickets/T-1973/ticket.md |  6 +++++-
 tickets/T-1996/ticket.md |  6 +++++-
 4 files changed, 28 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/t-1899/src/frob/gates/_root_asset_dirs.py, PRE001@tickets/T-1899, TICK004@tickets.md
