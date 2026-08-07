---
id: T-1573
title: test_tickets_evidence_cli.py TestDoneReportCli assumes v1 body-embedded Done
  report, broken by T-1553's v2 default flip
state: dropped
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_tickets_evidence_cli.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
found while working T-1561: tests/test_tickets_evidence_cli.py::TestDoneReportCli::test_cli_composes_and_writes
constructs a fresh ticket via a bare tmp_path (now v2-mode by T-1553's
default flip) and asserts "## Done report" appears in ticket.body after
`frob ticket done-report` -- but v2 mode splits the Done report out into
its own tickets/T-####/done-report.md file (migrate_v1_to_v2/set_done_report,
T-1259/T-1536), so ticket.body never contains it there. This is real,
reproducible breakage (confirmed failing on main at T-1553's tip,
unrelated to T-1541/T-1561's own changes) -- T-1553's own audit pass
missed this file. Either seed tickets.md explicitly (pin v1, matching
T-1553's own fix pattern elsewhere) or update the assertion to read the
v2-mode done-report.md path when in v2 mode.

## Drop reason
- 2026-08-05: moot: coordinator fixed the 11 v1-assuming tests in this worktree before landing