---
id: T-2111
title: CrossTicketLeakage refuses on the stale DECLARED scope instead of the live
  lease, so a narrowing that already freed a file still blocks every other ticket
  until land
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_cross_ticket_leakage.py
- src/frob/tickets/_land_git_ops.py
- tickets/T-2116/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_cross_ticket_leakage.py
  reason: repro/coverage test for the T-2111 live-lease-scope fix
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: same COV001/E501 fixup as T-2105's post-land floor
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tickets/T-2116/ticket.md
  reason: same COV001/E501 fixup as T-2105's post-land floor
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_a_narrowing_published_to_the_live_lease_releases_the_file_before_that_tickets_own_land
designated_repro_test: tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_a_narrowing_published_to_the_live_lease_releases_the_file_before_that_tickets_own_land
threat: null
component: null
anchor: false
anchor_reason: null
---
