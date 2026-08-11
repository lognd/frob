---
id: T-2106
title: 'frob ticket doable has no bounded mode: the only way to read the queue is
  a multi-minute full computation, and its argparse error names a --limit flag it
  does not have'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
- src/frob/tickets/_doable.py
- src/frob/app/ticket_runner/_query.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
evidence_scope:
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/ticket_runner/
  reason: narrow from a whole-directory glob (614 scope-closure warnings, locks the
    ticket_runner package away from the fleet) to the two files that actually implement
    doable
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: narrow from a whole-directory glob (614 scope-closure warnings, locks the
    ticket_runner package away from the fleet) to the two files that actually implement
    doable
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: narrow from a whole-directory glob (614 scope-closure warnings, locks the
    ticket_runner package away from the fleet) to the two files that actually implement
    doable
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: the T-2006 sweep re-verification (301s of doable's 736s) lives here; a genuine
    bound means not re-verifying unrelated candidates, which can only be done in this
    module
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: the repro test lives here alongside revalidate_dispatchable_sweep_tickets's
    own existing test suite
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_uncached_recheck_uses_the_doable_budget_not_the_sweep_budget
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
