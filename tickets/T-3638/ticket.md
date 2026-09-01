---
id: T-3638
title: archive-race allocator aborts on transient active/archive TOCTOU overlap
state: queued
kind: bug
origin: human
created: '2026-09-01'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_new_renumber.py
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
Run 33480116817 ubuntu:
  tests/test_tickets_ledger_concurrency.py::TestArchiveRaceWithConcurrentNew::
  test_concurrent_new_ticket_survives_a_racing_archive (failed)

  assert new_result is not None and new_result.is_ok
  E  AssertionError: TicketError.DuplicateId
  E  assert (Err(TicketError.DuplicateId) is not None and False)

REPRODUCED locally: passes 5/5 single-threaded, fails intermittently
(~1 in 15-20) under `pytest -n 4` (xdist parallel host load). Captured
failure log:

  ERROR frob.tickets:_archive.py:81 tickets: id(s) {'T-0001'} present
  in both active and archive
  ERROR frob.tickets:_new_renumber.py:1038 tickets: id allocation
  aborted, archive unreadable

Root cause: a bare tmp_path (no existing ledger content) defaults to
v2 store mode (`_store_mode`'s final-else branch, T-1553). In v2 mode,
`archive()` dispatches to `archive_v2`, which moves each ticket's
directory via `git_mv_dir` (`git mv tickets/T-#### tickets/archive/
T-####`) under that ticket's own PER-TICKET `ticket_lock` only -- NOT
under `allocator_lock` or any whole-tree lock. Meanwhile `new_ticket`'s
id allocation (`_allocate_and_check_ticket_id` -> `_load_merged`) reads
active state via ONE glob (`load_all`) and archived state via a SEPARATE
glob (`load_archive`), with nothing serializing those two unlocked glob
reads against a concurrent `git_mv_dir` rename in between them. A
`git_mv_dir` call that lands its directory rename between those two
glob reads makes the allocator observe the SAME id in both globs (a
genuine TOCTOU window, not lock contention) -- `_load_merged` treats
that as `DuplicateId` and aborts allocation outright, discarding a
concurrent `new_ticket` call rather than retrying past a window that
resolves itself within microseconds.

Fix direction (per this ticket's own family, T-1382-era renumber
allocation bug): the allocator must re-validate under allocator_lock
after winning it (double-checked), returning a fresh id instead of
Err on collision -- narrowly, bound a short retry around
`_allocate_and_check_ticket_id`'s `_load_merged` call so a transient
active/archive overlap self-heals by re-reading, rather than aborting
the whole allocation call.
Scope: src/frob/tickets/_new_renumber.py + tests/test_tickets_ledger_concurrency.py.
