## Done report

Added TICK003: a ledger-hygiene gate that WARNs (escalating to ERROR
past a hard cap) when the active tickets.md ledger holds more than a
configurable threshold of closed (done/dropped) tickets un-archived --
systematizing the repeated "we got away with not archiving" gap named in
the ticket (61 closed vs 99 open at filing time). Thresholds
(stale_archive_warn=20, stale_archive_error=60 by default) come from
frob.toml's [tickets] table, degrading to defaults on a missing/
malformed frob.toml. New public frob.tickets.closed_ticket_ids(queue) is
the shared "which tickets are closed" predicate the gate counts over --
kept in frob.tickets (not computed inline in frob.gates) per the
dispatch's steer to keep the gates/__init__.py touch additive; the only
edits there are the new _tick003_* functions plus one added line each in
tickets_gate's return expression and _KNOWN_GATE_RULES.

Resurrection-safety: the gate only COUNTS and recommends `frob ticket
archive`; it never writes tickets-archive.md itself, so it structurally
cannot interact with the land/splice path's archive-resurrection guards
(_drop_resurrected_ids, splice_ledger) -- those guard a write this gate
never performs. Verified with a dedicated
test_never_writes_or_archives_anything test.

Fixed two regressions surfaced while wiring this in: (1) a docblock-
ordering bug where closed_ticket_ids's insertion point stole doable's
frob:doc/frob:tests/frob:waive directive block, leaving doable with
COV001; (2) TestTick002GateUnwaivable.test_no_violation_off_default_branch
called tickets_gate(Path("."), ...) against this repo's own real
tickets.md, which now legitimately has a TICK003 WARN (44 un-archived
closed tickets) -- isolated with tmp_path since the test is only about
TICK002's branch guard.

### Changed
```
 .frob-release.json                            |   6 +-
 CHANGELOG.md                                  |  61 ++++++++
 docs/modules/tickets.md                       |  53 ++++++-
 pyproject.toml                                |   2 +-
 src/frob/app/ticket_runner.py                 | 209 +++++++++++++++++++++++++-
 src/frob/gates/__init__.py                    |  89 ++++++++++-
 src/frob/tickets/__init__.py                  | 125 +++++++++++++++
 src/frob/tickets/_land.py                     | 132 +++++++++++++++-
 src/frob/tickets/_models.py                   |   9 ++
 tests/test_gates_tickets_hygiene.py           | 105 +++++++++++++
 tests/test_ticket_land.py                     | 167 ++++++++++++++++++++
 tests/test_tickets_collision.py               |   8 +-
 tests/unit/test_ticket_runner_land_release.py | 182 ++++++++++++++++++++++
 tests/unit/test_ticket_store.py               | 117 ++++++++++++++
 tickets.md                                    | 206 ++++++++++++++++++++++++-
 uv.lock                                       |   2 +-
 16 files changed, 1451 insertions(+), 22 deletions(-)
```

### Evidence
- `tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_below_warn_threshold_is_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_above_default_warn_threshold_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_above_default_error_threshold_errors` (pytest node id, verified passing when recorded)
- `tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_open_tickets_never_count_toward_threshold` (pytest node id, verified passing when recorded)
- `tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_configurable_thresholds_from_frob_toml` (pytest node id, verified passing when recorded)
- `tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_malformed_frob_toml_degrades_to_defaults` (pytest node id, verified passing when recorded)
- `tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_never_writes_or_archives_anything` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestClosedTicketIds::test_returns_done_and_dropped_only` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestClosedTicketIds::test_orders_oldest_first` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestClosedTicketIds::test_empty_queue_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestTick002GateUnwaivable::test_no_violation_off_default_branch` (pytest node id, verified passing when recorded)
