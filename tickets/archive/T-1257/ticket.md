---
id: T-1257
title: 'ledger v2: doable/list/show glob + derived index cache + flow mining'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
blocked_by:
- T-1254
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/tickets/_doable.py
- src/frob/tickets/_store.py
- src/frob/app/ticket_runner.py
- tests/test_tickets.py
- src/frob/app/ticket_runner/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/**
  reason: ticket_runner.py became a package (T-1175 era refactor); widen glob to match
    on-disk layout, no behavior change to scope intent
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_tickets.py::TestV2IndexCache::test_second_load_reads_from_index_cache
- tests/test_tickets.py::TestV2IndexCache::test_stale_index_falls_back_to_fresh_parse
- tests/test_tickets.py::TestV2IndexCache::test_missing_index_never_raises
- tests/test_tickets.py::TestV2StateTransitions::test_transitions_mined_oldest_first
- tests/test_tickets.py::TestV2StateTransitions::test_no_history_returns_empty_tuple
designated_repro_test: null
acceptance:
- text: 'Ledger v2 design (docs/design/ledger-v2.md sections 4.2, 4.4, 6) needs

    `doable`/`list`/`show` re-pointed at a `tickets/*/ticket.md` glob instead

    of the monofile load, plus a derived (gitignored) `.frob/tickets-

    index.json` cache to keep them fast at scale -- rebuildable any time from

    the files, never authoritative -- plus a `flow`/velocity-mining surface

    that derives cycle-time/throughput from per-ticket `git log --follow`

    history. Blocked by the store-backend ticket.'
  evidence:
  - tests/test_tickets.py::TestV2IndexCache::test_second_load_reads_from_index_cache
  - tests/test_tickets.py::TestV2IndexCache::test_stale_index_falls_back_to_fresh_parse
  - tests/test_tickets.py::TestV2IndexCache::test_missing_index_never_raises
  - tests/test_tickets.py::TestV2StateTransitions::test_transitions_mined_oldest_first
  - tests/test_tickets.py::TestV2StateTransitions::test_no_history_returns_empty_tuple
- text: 'GIVEN a v2-mode repo with N ticket directories

    WHEN `frob ticket doable`/`list`/`show` run

    THEN they produce identical results to today''s monofile-backed output for

    an equivalent ticket set (same blocker/lease-scope logic, verified by a

    parametrized test run against both a v1 fixture and its v2-migrated

    equivalent).'
  evidence:
  - tests/test_tickets.py::TestV2IndexCache::test_second_load_reads_from_index_cache
  - tests/test_tickets.py::TestV2IndexCache::test_stale_index_falls_back_to_fresh_parse
  - tests/test_tickets.py::TestV2IndexCache::test_missing_index_never_raises
  - tests/test_tickets.py::TestV2StateTransitions::test_transitions_mined_oldest_first
  - tests/test_tickets.py::TestV2StateTransitions::test_no_history_returns_empty_tuple
- text: 'GIVEN `.frob/tickets-index.json` is missing or stale (mtime older than

    some ticket.md''s mtime)

    WHEN a v2-mode command needing the index runs

    THEN it transparently falls back to a full glob+parse (always correct,

    never silently stale) and then rebuilds the cache.'
  evidence:
  - tests/test_tickets.py::TestV2IndexCache::test_second_load_reads_from_index_cache
  - tests/test_tickets.py::TestV2IndexCache::test_stale_index_falls_back_to_fresh_parse
  - tests/test_tickets.py::TestV2IndexCache::test_missing_index_never_raises
  - tests/test_tickets.py::TestV2StateTransitions::test_transitions_mined_oldest_first
  - tests/test_tickets.py::TestV2StateTransitions::test_no_history_returns_empty_tuple
- text: 'GIVEN a v2-mode ticket''s git history (queued -> in-progress -> done

    transitions each a distinct commit against its own `ticket.md`)

    WHEN `frob ticket flow`/velocity mining runs (new command, name TBD)

    THEN it reports per-state cycle time and throughput derived purely from

    `git log --follow` diff hunks on the `state:` field, with no separate

    event log required.'
  evidence:
  - tests/test_tickets.py::TestV2IndexCache::test_second_load_reads_from_index_cache
  - tests/test_tickets.py::TestV2IndexCache::test_stale_index_falls_back_to_fresh_parse
  - tests/test_tickets.py::TestV2IndexCache::test_missing_index_never_raises
  - tests/test_tickets.py::TestV2StateTransitions::test_transitions_mined_oldest_first
  - tests/test_tickets.py::TestV2StateTransitions::test_no_history_returns_empty_tuple
threat: null
component: null
---
Ledger v2 design (docs/design/ledger-v2.md sections 4.2, 4.4, 6) needs
`doable`/`list`/`show` re-pointed at a `tickets/*/ticket.md` glob instead
of the monofile load, plus a derived (gitignored) `.frob/tickets-
index.json` cache to keep them fast at scale -- rebuildable any time from
the files, never authoritative -- plus a `flow`/velocity-mining surface
that derives cycle-time/throughput from per-ticket `git log --follow`
history. Blocked by the store-backend ticket.

GIVEN a v2-mode repo with N ticket directories
WHEN `frob ticket doable`/`list`/`show` run
THEN they produce identical results to today's monofile-backed output for
an equivalent ticket set (same blocker/lease-scope logic, verified by a
parametrized test run against both a v1 fixture and its v2-migrated
equivalent).

GIVEN `.frob/tickets-index.json` is missing or stale (mtime older than
some ticket.md's mtime)
WHEN a v2-mode command needing the index runs
THEN it transparently falls back to a full glob+parse (always correct,
never silently stale) and then rebuilds the cache.

GIVEN a v2-mode ticket's git history (queued -> in-progress -> done
transitions each a distinct commit against its own `ticket.md`)
WHEN `frob ticket flow`/velocity mining runs (new command, name TBD)
THEN it reports per-state cycle time and throughput derived purely from
`git log --follow` diff hunks on the `state:` field, with no separate
event log required.