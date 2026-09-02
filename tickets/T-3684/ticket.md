---
id: T-3684
title: 'load_all races a concurrent per-ticket move/delete: unguarded FileNotFoundError
  crashes new_ticket/archive callers'
state: in-progress
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
- src/frob/tickets/_store.py
- src/frob/tickets/_models.py
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
## Description

CI run 33582058515 (ubuntu leg) failed
tests/test_tickets_ledger_concurrency.py::TestArchiveRaceWithConcurrentNew::test_concurrent_new_ticket_survives_a_racing_archive
intermittently under load (both legs were fully green in run 33545437868 --
this is a genuine flake, not a hard regression).

Reproduced locally (not in isolation -- required real background CPU/IO
contention, e.g. a concurrent `pytest -n 12` full-suite run alongside 5-6
parallel loop processes hammering this one test) as a real product race,
NOT a fixture/git-env problem:

```
FileNotFoundError: [Errno 2] No such file or directory:
'.../tickets/T-0001/ticket.md'
```

raised from `tests/test_tickets_ledger_concurrency.py:121 -> new_ticket ->
_allocate_and_write_new_ticket -> write_ticket (src/frob/tickets/_store.py:1891)
-> load_all -> _parse_ticket_file (src/frob/tickets/_store.py:684) ->
`path.read_text()`.

Root cause: `write_ticket`'s T-1637/T-1679 content-loss guard calls
`existing = load_all(root)` BEFORE any lock is held (`_store.py:1891`).
`load_all` in v2 mode globs `tickets/*/ticket.md` and then reads each file
in a separate step (`_store.py:1492`, `_parse_ticket_file` has no
exception handling at all around `path.read_text()`). `archive_v2` moves
a done/dropped ticket's directory (`git mv tickets/T-#### tickets/archive/
T-####`) under that ticket's OWN `ticket_lock` only (by design, T-1750:
v2 mode deliberately does NOT take a whole-tree `ledger_lock` for archive,
unlike v1's `archive`) -- so a concurrent `load_all` that already globbed
`tickets/T-0001/ticket.md` before the move, then tries to `read_text()`
it after the move completes, hits a bare `FileNotFoundError` that
`_parse_ticket_file` propagates as an unguarded exception instead of a
`Result`. In the failing test this crashed the `_run_new` thread
(`new_result` stays `None`, since a plain `threading.Thread`'s uncaught
exception is not propagated to the joining thread), matching the CI
symptom exactly ("left new_result=None, its body raised before
assigning").

This is a genuine TOCTOU in `load_all`'s glob-then-read loop, not a test
fixture issue -- the "gitio: git-common-dir lookup failed" log lines
CI's failure captured are a red herring (the tmp repo genuinely is not a
git worktree in this test, and that path already degrades gracefully via
`Result`, unrelated to the crash).

Likely also the mechanism behind T-3639 (renumber_one allocator race) if
that path shares the same unguarded `load_all`/`_parse_ticket_file` glob
loop -- NOT folded into this ticket; leaving T-3639 to be checked
separately against this fix once it lands, since this ticket's scope is
`_store.py`/`_models.py` only.

## Plan

`_parse_ticket_file` (src/frob/tickets/_store.py) currently does:

```python
def _parse_ticket_file(path: Path) -> Result[Ticket, TicketError]:
    text = path.read_text(encoding="utf-8")
    return _parse_ticket_text(text, str(path))
```

with zero exception handling. Fix:

1. Add a new `TicketError` variant (e.g. `TicketVanishedDuringScan`) in
   `src/frob/tickets/_models.py` naming this specific, expected-under-
   concurrency outcome distinctly from `MalformedFrontmatter` (a genuine
   parse failure, which must still abort the whole `load_all` loudly --
   never conflate the two).
2. `_parse_ticket_file` catches `FileNotFoundError` around
   `path.read_text()` and returns `Err(TicketError.TicketVanishedDuringScan)`
   instead of letting the exception propagate.
3. `load_all`'s two glob-then-parse loops (`_store.py` ~1492 v2/dir mode,
   ~1672 the other mode) treat `TicketVanishedDuringScan` specifically as
   "this ticket was concurrently moved/deleted out from under this
   snapshot -- skip it, keep scanning" (log at DEBUG, `continue`) rather
   than aborting the whole `load_all` call the way every other parse
   error still does. This is the correct backend-agnostic answer to a
   point-in-time-snapshot read racing ANY other operation, and matches
   the v2 archive path's own no-whole-tree-lock design (T-1750) -- a
   ticket that moved mid-scan is legitimately "gone from this snapshot,"
   not "load failed."
4. Do NOT touch `_archive.py`, `_land.py`, or `_store_migrate.py`'s own
   direct `_parse_ticket_file` call sites (out of this ticket's declared
   scope) -- they already treat any `Err` from `_parse_ticket_file` as an
   error/log-and-return path today, so returning the new distinct variant
   there instead of crashing is a strict improvement with no behavior
   change required at those call sites.
5. Harden `tests/test_tickets_ledger_concurrency.py` if needed once the
   product fix lands, to keep proving the race is now closed (no sleeps,
   no weakened assertions -- the existing Barrier-rendezvous shape stays).

Do NOT add a whole-tree lock around `load_all` -- that would reintroduce
the whole-tree contention T-1750's `archive_v2` design deliberately
avoided; the fix belongs at the read-tolerance layer, not the locking
layer.
