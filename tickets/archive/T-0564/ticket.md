---
id: T-0564
title: 'gates: COV002 closed-ticket grace window misses marker-in-hunk when unified=0
  diff omits the marker line'
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov002_grace_matches_hunk_anywhere_in_ticket_block
designated_repro_test: null
threat: null
component: null
---
Discovered while working T-0550: _bound_to_open_ticket's T-0214/T-0320 grace window (closed ticket still covers its own closing diff) requires the ticket's <!-- ticket:ID --> marker LINE to fall inside one of working_diff's unified=0 hunks. A YAML ticket block's marker/id/title lines often sit just above the first line that actually differs (e.g. state: queued -> done, or an evidence: [] -> evidence: [...] insertion later in the block), so the marker line itself is never in any hunk even though the ticket's own state transition clearly is in the diff. Result: once a ticket closes and a LATER ticket becomes active on the same stacked, unmerged branch, a full/ticket-scoped frob check re-flags the closed ticket's already-covered symbols as COV002 violations again, purely due to this narrow hunk-membership check, not a real coverage gap. Fix direction: extend _ticket_marker_in_diff_hunk to also count a hunk anywhere within the ticket's whole YAML block span (marker to closing triple-backtick), not just the exact marker line.