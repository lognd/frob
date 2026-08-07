---
id: T-0740
title: 'tickets: investigate missing-marker ledger corruption class (T-0367 found
  absorbed into T-0363''s body)'
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: regression test locking the _splice_only_ticket integrity guard fix
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_ticket_land.py::TestSpliceOnlyTicket::test_render_that_would_drop_an_id_is_refused
designated_repro_test: null
threat: null
component: null
---
found while working T-0726 (TICK006 phantom-filing gate): T-0367 existed in tickets-archive.md as a fully-formed yaml frontmatter block + body (title/state/scope/created all present) but with NO <!-- ticket:T-0367 --> marker line before it, so _parse_ledger's marker-based chunking silently absorbed its entire block as prose inside the PRECEDING ticket's (T-0363) body instead of parsing it as its own ticket -- load_archive/load_all never saw T-0367 at all (frob ticket show T-0367 would have 404'd). Fixed the one instance directly in tickets-archive.md (added the missing marker, restoring T-0367 as its own resolvable block) since it directly corrupted TICK006's phantom-filing measurement, but did not audit the rest of the ~500-ticket ledger for the same missing-marker shape, nor find the write path that produced it (a hand-edit? a merge-splice bug? frob ticket new failing mid-write?). Investigate: (1) whether any other ledger block is missing its marker the same way (a scripted marker-vs-yaml-id cross-check over both ledger files), (2) the root cause / write path that can produce a markerless block, (3) whether frob.tickets._store or the land/splice path needs a structural guard against ever writing yaml frontmatter without its marker.