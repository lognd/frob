---
id: T-1717
title: consider relocating _write_ticket_unchecked out of src/frob/tickets/_store.py
  into a test-only helper module
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
frob:ticket T-1679

`_write_ticket_unchecked` (`frob.tickets._store`) is a deliberately
test-fixture-only escape hatch for the T-1637/T-1679 content-loss guard --
by design it has no production caller and never should. WIRE002 requires
a real `follow_up` ticket for its WIRE001 waiver since it lives in `src/`
(the `permanent="true"` test-tree exemption only applies to symbols under
`tests/`). This ticket is that accountable follow-up: investigate whether
`_write_ticket_unchecked` can be relocated into a `tests/`-tree helper
module instead (it needs access to the private `_write_ticket_impl` split
point in `_store.py`, so this may require exporting a narrow test-only
seam, or may simply not be worth the churn -- either outcome is a
legitimate close for this ticket).