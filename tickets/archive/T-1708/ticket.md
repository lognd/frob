---
id: T-1708
title: 'post-land sweep regression from T-1703: 7 new error(s) (ARCH001, DOC009, INV006,
  PII012)'
state: dropped
kind: bug
origin: agent
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- docs/audits/docs-completeness-2026-08-06.md
- src/frob/gates/_markdown_scan.py
- src/frob/tickets/_evidence.py
- tests/test_ticket_work_and_land_finish.py
- tests/unit/gates/test_markdown_scan.py
- tests/unit/test_ticket_runner_gate_findings.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1703 at commit 5242df9c1092f2746df4591c6450fb3957146b49 found 7 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs:

- ARCH001  src/frob/tickets/_evidence.py
- DOC009  docs/audits/docs-completeness-2026-08-06.md
- INV006  src/frob/gates/_markdown_scan.py
- PII012  tests/unit/gates/test_markdown_scan.py
- TICK006  tickets.md
- invalid-parameter-default  tests/unit/test_ticket_runner_gate_findings.py
- unresolved-attribute  tests/test_ticket_work_and_land_finish.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-07: all 7 findings verified gone on main: ARCH001+DOC009+unresolved-attribute fixed by T-1685, INV006+PII012 fixed by T-1709 (waivers), invalid-parameter-default and TICK006 were transient/already clean (T-1709 investigated, reconfirmed here via frob check)