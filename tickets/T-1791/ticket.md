---
id: T-1791
title: Wire frob.verify._quarantine.raise_quarantine into the batch-verification driver
state: done
kind: feature
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets.md
- tests/unit/test_rapid_sweep.py
- tickets/T-1791/ticket.md
- tickets/T-1791/done-report.md
- tickets/T-1821/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: quarantine wiring needs kill-point/behavior tests in the module's own test
    file, and the ticket's own directory files per the established SCOPE001 precedent
    (T-1768/T-1220/T-1694)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1791/ticket.md
  reason: quarantine wiring needs kill-point/behavior tests in the module's own test
    file, and the ticket's own directory files per the established SCOPE001 precedent
    (T-1768/T-1220/T-1694)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1791/done-report.md
  reason: quarantine wiring needs kill-point/behavior tests in the module's own test
    file, and the ticket's own directory files per the established SCOPE001 precedent
    (T-1768/T-1220/T-1694)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1821/ticket.md
  reason: 'SCOPE001: this ticket''s own worktree branch filed a disclosed follow-up
    draft (T-1740/describe_root_dirt breakage found while working T-1791); the draft''s
    ticket.md landed in this branch''s diff and must be in scope for the SCOPE gate
    to pass, per the T-1694 precedent'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_raises_with_attributed_and_unattributed_findings
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_empty_queue_logs_and_skips_the_raise
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_raised_even_when_every_pair_already_has_an_open_ticket
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_raise_failure_is_logged_not_raised
designated_repro_test: null
threat: null
component: null
---
T-1693 built the durable quarantine primitive (frob.verify._quarantine: raise_quarantine/is_quarantined/clear_quarantine) and wired the land-path enforcement half (_land_cmd.py's _quarantine_override_ceilings, forcing synchronous verification while raised). It does NOT call raise_quarantine anywhere -- the batch-verification driver (T-1690's own declared scope, src/frob/app/ticket_runner/_rapid_sweep.py) needs to call raise_quarantine(root, batch_commit_shas=..., findings=...) when a batch verification comes back red with attributed/unattributed findings from frob.verify.attribute_batch. Out of T-1693's own declared scope (_rapid_sweep.py was leased by a concurrent in-progress ticket for that ticket's whole duration).