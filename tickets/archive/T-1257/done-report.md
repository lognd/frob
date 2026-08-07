## Done report

Implemented the two parts of T-1257 that fell inside its declared scope:

1. `doable`/`list`/`show` re-pointed at the `tickets/*/ticket.md` glob:
   already true going in (`load_all`'s v2 branch, T-1254/T-1256) -- no
   change needed there, verified by the existing TestV2* store suite
   still passing.
2. Derived, gitignored index cache (`.frob/tickets-index.json`, design
   section 6): `_index_path`/`_read_index_cache`/`_write_index_cache` in
   `src/frob/tickets/_store.py`, wired into `load_all`'s v2 branch. A hit
   requires the exact path SET and every recorded mtime-ns to match the
   live glob -- any add/remove/touch is a miss, never a stale hit. A
   miss transparently falls back to the full glob+parse (always correct)
   and rebuilds the cache. Never a second source of truth: deleting the
   file only costs the next load's speedup.
3. `v2_state_transitions(root, ticket_id)` (design section 4.4): mines
   every `state:` transition a v2-mode ticket's OWN `ticket.md` has ever
   recorded, oldest-first, as `(commit_sha, author-date-iso, new_state)`
   triples, purely from `git log --follow -p` diff hunks -- no separate
   event log. Empty tuple (never raises) with no history/not a git repo.

Cut (disclosed, not silently dropped): acceptance criterion 3 wants
`frob ticket flow` itself to use this in v2 mode. That command's
rendering lives in `src/frob/tickets/_setters.py`
(`_ledger_commit_history`/`_mine_done_transitions`, hardcoded to the v1
`tickets.md` blob), which is NOT in T-1257's declared scope
(src/frob/tickets/_doable.py, src/frob/tickets/_store.py,
src/frob/app/ticket_runner/**, tests/test_tickets.py). Filed as a draft
follow-up rather than silently widening scope -- see Filed below. The
mining PRIMITIVE this follow-up needs already exists and is tested.

Changed:
- src/frob/tickets/_store.py::_index_path
- src/frob/tickets/_store.py::_read_index_cache
- src/frob/tickets/_store.py::_write_index_cache
- src/frob/tickets/_store.py::load_all (v2 branch now cache-aware)
- src/frob/tickets/_store.py::v2_state_transitions
- tests/test_tickets.py::TestV2IndexCache
- tests/test_tickets.py::TestV2StateTransitions

Evidence:
- tests/test_tickets.py::TestV2IndexCache::test_second_load_reads_from_index_cache
- tests/test_tickets.py::TestV2IndexCache::test_stale_index_falls_back_to_fresh_parse
- tests/test_tickets.py::TestV2IndexCache::test_missing_index_never_raises
- tests/test_tickets.py::TestV2StateTransitions::test_transitions_mined_oldest_first
- tests/test_tickets.py::TestV2StateTransitions::test_no_history_returns_empty_tuple
Also re-ran tests/unit/test_ticket_store.py (74 tests) and the full
tests/test_tickets.py file (140 tests) -- all pass, no regression to the
existing v2 store/doable/show surface.

Filed: T-1330 (wire v2 git-history mining into `frob ticket
flow`/`sprint velocity`, scope src/frob/tickets/_setters.py +
tests/test_tickets_velocity.py)

Gates: scoped pytest runs above clean; ruff clean on
src/frob/tickets/_store.py and tests/test_tickets.py under both `ruff`
and `uv run ruff`. Full `frob check` not run per memory-budget
constraints (scoped verification only).

### Changed
```
 design/frob.strata                |  16 +
 docs/design/ledger-v2.md          |  13 +
 docs/modules/tickets.md           |  72 ++++-
 src/frob/tickets/_archive.py      |  85 +++++-
 src/frob/tickets/_new_renumber.py | 262 ++++++++++++++++-
 src/frob/tickets/_reporting.py    |  66 ++++-
 src/frob/tickets/_store.py        | 484 +++++++++++++++++++++++++++---
 tests/test_ticket_land.py         | 167 +++++++++++
 tests/test_tickets_collision.py   | 146 +++++++++
 tests/unit/test_process_lock.py   | 159 ++++++++++
 tests/unit/test_ticket_store.py   | 180 ++++++++++++
 tickets.md                        | 601 ++++++++++++++++++++++++++++++++++++--
 12 files changed, 2174 insertions(+), 77 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestV2IndexCache::test_second_load_reads_from_index_cache` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestV2IndexCache::test_stale_index_falls_back_to_fresh_parse` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestV2IndexCache::test_missing_index_never_raises` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestV2StateTransitions::test_transitions_mined_oldest_first` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestV2StateTransitions::test_no_history_returns_empty_tuple` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 6 error(s), 615 warning(s), 685 waived
- error-findings: ARCH001@src/frob/refactor/_scan.py, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, PRE001@tickets/T-1257, RENDER001@src/frob/refactor/_cli.py, SELFAUDIT001@design
