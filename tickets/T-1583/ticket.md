---
id: T-1583
title: 'write_archive is v1-only: frob ticket archive loses tickets in a v2 repo'
state: in-progress
kind: bug
origin: human
created: '2026-08-05'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- tests/unit/test_ticket_store.py
- tests/test_gates.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_v2_write_archive_round_trips_many_tickets_count_and_content
designated_repro_test: null
threat: null
component: null
---
load_archive is store-mode aware (T-1256: v2 globs tickets/archive/T-####/ticket.md), but write_archive still unconditionally replaces the tickets-archive.md monofile. In a v2 repo the two disagree: archive() writes every archived ticket into a file load_archive will NEVER read, then write_all drops those same tickets from the active store -- the tickets disappear from every read path. Same asymmetry in _new_renumber.py's write_archive call.

Surfaced by tests/test_gates.py::TestTick006PhantomFiling::test_filed_as_real_archived_id_is_silent: write_archive put T-0137 in tickets-archive.md, load_archive globbed the v2 archive tree, found nothing, and TICK006 called a genuinely archived id a phantom.

Fix: give write_archive a v2 branch that writes each ticket through write_archived_ticket (T-1561's per-ticket archive writer) and prunes tickets/archive/T-####/ dirs absent from the map, preserving the wholesale-replace contract the v1 branch has. Every prune logged. Tests: a v2-mode archive round trip (write_archive then load_archive returns the same map) and a prune case.