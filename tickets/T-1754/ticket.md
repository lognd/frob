---
id: T-1754
title: 'post-land sweep regression from T-1753: 2 new error(s) (REL001, invalid-argument-type)'
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- pyproject.toml
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: AFFECT001 requires touching the affects()-closure doc for _attribute_new_findings,
    fixed by this ticket's Sequence widening
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_attributed_and_unattributed_round_trip
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_all_attributed_to_open_tickets_files_nothing
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1753 at commit 8a2f473e454c085890de379dcefd098a2978b4ce found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- REL001  pyproject.toml
- invalid-argument-type  src/frob/app/ticket_runner/_rapid_sweep.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.