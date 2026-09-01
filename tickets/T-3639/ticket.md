---
id: T-3639
title: renumber_one races new_ticket allocator, same TOCTOU family as T-3638
state: queued
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_renumber_v2.py
- tests/test_tickets_ledger_concurrency.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3638 (archive-race allocator TOCTOU).

While stress-testing T-3638's fix (25x `pytest -n 4` runs of
tests/test_tickets_ledger_concurrency.py), the SIBLING test
tests/test_tickets_ledger_concurrency.py::TestRenumberOneRaceWithConcurrentNew::
test_concurrent_new_ticket_survives_a_racing_renumber_one failed once,
with the same failure shape (new_ticket's allocation returning
Err(DuplicateId) against a concurrent renumber_one).

T-3638's fix (a bounded, short-sleep retry around
_allocate_and_check_ticket_id's `_load_merged` call in
src/frob/tickets/_new_renumber.py) targets the archive_v2 TOCTOU window
specifically; renumber_one/renumber_one_v2 is a different id-mutating
code path that may have an analogous (or a differently-shaped) window
against the same allocator. Not reproduced densely enough in this
session to characterize with confidence (1 failure observed across
~65 stress runs of the whole file) -- needs its own dedicated repro
effort (single test, -n 4, many iterations) before diagnosing a fix,
same protocol T-3638 itself used.

Scope: likely src/frob/tickets/_new_renumber.py and/or
src/frob/tickets/_renumber_v2.py + tests/test_tickets_ledger_concurrency.py
(overlaps T-3638's own scope -- confirm no conflicting in-flight work
before starting).
