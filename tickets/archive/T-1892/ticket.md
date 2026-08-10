---
id: T-1892
title: '--evidence-cmd accepts any silently-succeeding command: empty-output digest
  makes ''true'' valid evidence'
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_evidence.py
- src/frob/tickets/_models.py
- tests/test_tickets_cmd_evidence.py
- tickets/T-1899/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: 'T-1892: refuse silent --evidence-cmd (empty stdout+stderr), new TicketError
    variant, regression tests'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-1892: refuse silent --evidence-cmd (empty stdout+stderr), new TicketError
    variant, regression tests'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_tickets_cmd_evidence.py
  reason: 'T-1892: refuse silent --evidence-cmd (empty stdout+stderr), new TicketError
    variant, regression tests'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tickets/T-1899/ticket.md
  reason: 'T-1892: scope covers the follow-up draft ticket filed during this work
    (docs update blocked on T-1883''s lease)'
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_tickets_cmd_evidence.py::TestSilentCmdEvidenceRefused::test_silent_zero_exit_command_is_refused
- tests/test_tickets_cmd_evidence.py::TestSilentCmdEvidenceRefused::test_grep_q_silent_match_is_refused
- tests/test_tickets_cmd_evidence.py::TestSilentCmdEvidenceRefused::test_chatty_zero_exit_command_is_accepted
- tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_exit_zero
- tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_nonzero_exit
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-09, coordinator, closing T-1644 on main.

'frob ticket close T-1644 --evidence-cmd "grep -q ..."' recorded:

  cmd:grep -q 'src/frob/yaml_io.py' design/frob.strata exit=0 sha256=e3b0c44298fc

e3b0c44298fc is the SHA-256 of the EMPTY STRING. 'grep -q' is silent by design, so the recorded digest carries zero information about what was actually verified. The identical digest would be recorded for 'true', 'cd .', ': ', or any other silent zero-exit command. Re-running with 'grep -c' instead recorded a distinct digest (4355a46b19d3) -- i.e. the channel only has integrity when the command happens to be chatty.

WHY IT MATTERS. --evidence-cmd is the sanctioned evidence channel for docs-kind tickets (T-0215). As it stands, a docs ticket can be closed with evidence that provably demonstrates nothing, and the ledger will show a well-formed evidence entry that passes every downstream check. This is the 'catalogued is not enforced' failure mode reappearing inside the evidence system itself -- the record looks like proof and is not.

FIX OPTIONS (pick on merit, do not just warn):
1. REFUSE an --evidence-cmd whose captured stdout+stderr is empty, with a message telling the operator to use a command that emits its finding (e.g. 'grep -c' over 'grep -q').
2. Include the command string itself in the digest input so distinct commands cannot collide on the empty digest.
Option 2 alone is insufficient -- it makes entries distinguishable but still lets 'true' stand as proof. Prefer 1, or 1+2.

Add a regression test asserting that a silent zero-exit command is REFUSED as evidence, and that a chatty one is accepted.