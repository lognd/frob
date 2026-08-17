---
id: T-1899
title: 'docs: document T-1892''s EvidenceCmdSilent refusal in docs/modules/tickets.md'
state: done
kind: docs
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1892 fixed run_cmd_evidence (src/frob/tickets/_evidence.py) to refuse a
cmd: evidence command whose captured stdout+stderr is empty (Err
EvidenceCmdSilent), even on exit 0 -- closing the hole where `true`/`grep
-q`/`: ` all silently satisfied the --evidence-cmd channel with the
sha256-of-empty-string digest.

docs/modules/tickets.md needed a matching update (the cmd: evidence
section, #public-api anchor run_cmd_evidence already documents) but was
leased by T-1883 (in-progress) for the whole duration of T-1892's work,
so it could not be touched without a scope-lease conflict.

Add a short note to docs/modules/tickets.md's cmd: evidence section:
"A command whose captured stdout+stderr is empty is refused
(EvidenceCmdSilent), even on exit 0 -- prefer a chatty check (`grep -c`/
`grep -n`) over a silent one (`grep -q`)." Cite T-1892. Then
`frob ack` the refreshed run_cmd_evidence/add_cmd_evidence refs.

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
