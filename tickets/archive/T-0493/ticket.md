---
id: T-0493
title: frob ticket done-report leaves a stray empty '## Done report' heading before
  the rendered one
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/unit/test_ticket_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: T-0493 regression test for stray-heading self-heal mirrors src/frob/tickets/_models.py
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_ticket_store.py::TestReplaceDoneReportSection::test_stray_empty_heading_before_real_one_collapses_to_one
designated_repro_test: null
threat: null
component: null
---
Observed twice while working T-0348/T-0349 in this worktree: each ticket's pre-existing empty '## Done report' placeholder heading (present in the queued-ticket template) is not reused/filled by 'frob ticket done-report' -- it appends a SECOND '## Done report' heading right after the empty one, and 'frob ticket close' then fails with MissingEvidence (reads the first, empty, heading) until the stray empty heading is manually deleted. Reproduce: frob ticket start T-XXXX; frob ticket evidence T-XXXX <node-id>; frob ticket done-report T-XXXX --why-file <file>; frob ticket close T-XXXX -- fails first time, succeeds after manually removing the leading blank '## Done report' line.