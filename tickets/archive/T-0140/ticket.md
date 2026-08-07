---
id: T-0140
title: ticket id allocator ignores tickets-archive.md -- new ids collide with archived
  tickets
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- tests/test_tickets.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets.py::TestArchive::test_new_ticket_id_continues_past_archived_max
- tests/test_tickets.py::TestArchive::test_new_ticket_fresh_repo_no_archive_file
- tests/test_tickets.py::TestArchive::test_new_ticket_corrupt_archive_fails_loudly
designated_repro_test: null
threat: null
component: null
---
Found immediately after the first post-archive frob ticket new: allocation scans only the active tickets.md for the max id, so a freshly archived queue restarts at T-0001, colliding with archived ids and making the merged active+archive queue unloadable (DuplicateId on every command). Fix: allocate from the max across BOTH ledgers (load_queue already merges them; reuse that path), plus a regression test: archive a ledger, file a new ticket, assert the id continues the sequence and the merged queue loads.