---
id: T-2216
title: 'frob ticket block appends a duplicate blocked_by edge instead of being idempotent,
  and there is no verb to remove one: T-2205 now reads blocked_by [T-2211, T-2211]'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_lifecycle.py
evidence_scope:
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/_setters.py
  reason: Coordinator scope error caught by T-2177's own plausibility warning, which
    fired on filing. The block verb is _block at src/frob/app/ticket_runner/_lifecycle.py:1128
    -- its own comment calls it 'the ONE CLI verb that appends to an EXISTING ticket's
    blocked_by post-creation'. src/frob/tickets/_setters.py does not implement it;
    I picked that file from its module name, which is the exact T-2157/T-2173/T-2189
    shape the warning names.
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: Coordinator scope error caught by T-2177's own plausibility warning, which
    fired on filing. The block verb is _block at src/frob/app/ticket_runner/_lifecycle.py:1128
    -- its own comment calls it 'the ONE CLI verb that appends to an EXISTING ticket's
    blocked_by post-creation'. src/frob/tickets/_setters.py does not implement it;
    I picked that file from its module name, which is the exact T-2157/T-2173/T-2189
    shape the warning names.
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_tickets.py::TestBlockCliValidatesBy::test_blocking_by_a_different_second_id_still_appends
- tests/test_tickets.py::TestBlockCliValidatesBy::test_cli_refuses_empty_string_by
- tests/test_tickets.py::TestBlockCliValidatesBy::test_cli_refuses_malformed_by
- tests/test_tickets.py::TestBlockCliValidatesBy::test_cli_accepts_valid_by
- tests/test_tickets.py::TestBlockCliValidatesBy::test_blocking_by_the_same_id_twice_does_not_duplicate_the_edge
designated_repro_test: tests/test_tickets.py::TestBlockCliValidatesBy::test_blocking_by_the_same_id_twice_does_not_duplicate_the_edge
threat: null
component: null
anchor: false
anchor_reason: null
---
