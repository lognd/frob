---
id: T-1753
title: 'post-land sweep regression from T-1690: 3 new error(s) (ARCH001, E501, invalid-argument-type)'
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- /home/logan/projects/frob/src/frob/verify/_attribution.py
- src/frob/verify/_attribution.py
- tests/unit/test_rapid_sweep.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: the ty invalid-argument-type finding traces to _attribute_new_findings's
    pairs parameter, whose call site and type both live in _rapid_sweep.py
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/tickets.md
  reason: AFFECT001 requires touching the affects()-closure doc for attribute_batch/_attribute_new_findings,
    both fixed by this ticket
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_caller_break_attributes_to_the_caller_commit
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_missing_line_falls_back_to_whole_file_candidates
- tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_attributed_and_unattributed_round_trip
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_attributed_to_open_ticket_is_not_refiled
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1690 at commit 5c17406570de3df7006b5737a6fc1cdc8fdf6b5c found 3 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- ARCH001  src/frob/verify/_attribution.py
- E501  /home/logan/projects/frob/src/frob/verify/_attribution.py
- invalid-argument-type  tests/unit/test_rapid_sweep.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.