---
id: T-1756
title: 'post-land sweep regression from T-1692: 3 new error(s) (E501, invalid-argument-type)'
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- /home/logan/projects/frob/src/frob/app/ticket_runner/_land_cmd.py
- /home/logan/projects/frob/src/frob/verify/_backpressure.py
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/tickets.md
- src/frob/verify/_backpressure.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: AFFECT001 requires touching the affects()-closure doc for BackpressureError/current_status,
    both touched by this ticket's E501 wraps
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/verify/_backpressure.py
  reason: relative-path scope entry alongside the absolute-path one already filed
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/verify/test_backpressure.py::TestCurrentStatus::test_empty_queue_is_never_tripped
- tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_not_tripped_is_a_noop
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1692 at commit 1647eb98b3f9a373c9c47effef78ea141857c48f found 3 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- E501  /home/logan/projects/frob/src/frob/app/ticket_runner/_land_cmd.py
- E501  /home/logan/projects/frob/src/frob/verify/_backpressure.py
- invalid-argument-type  src/frob/app/ticket_runner/_land_cmd.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.