## Done report

Implemented the ledger v2 file-per-ticket store backend as a THIRD
`_store_mode` branch alongside the existing single/dir backends, per
docs/design/ledger-v2.md section 1. v1 (single-file `tickets.md`) is
untouched and stays the default -- `_render_ledger`/`splice_ledger` were
not modified at all.

v2 layout: `tickets/T-####/ticket.md` (frontmatter+body, reusing
`_serialize_ticket`/`_parse_ticket_file` unchanged) plus a NEW
`tickets/T-####/done-report.md` split out of the body, plus a
self-contained `tickets/T-####/attachments/`. `_store_mode` detects v2
FIRST (`tickets/T-*/ticket.md` glob) so a v2 tree takes priority over any
stray legacy `tickets.md`/`tickets/*.md` left behind mid-migration.

`load_all`/`write_ticket`/`write_all` all gained a v2 branch:
- `write_ticket`'s v2 branch takes the per-ticket `ticket_lock` (T-1253)
  instead of the whole-ledger `ledger_lock` -- two callers writing
  different ticket ids never contend.
- `write_all`'s three per-mode bodies were split into
  `_write_all_single`/`_write_all_v2`/`_write_all_dir` private helpers
  (also brought the function under the ARCH001 60-line threshold).
- New `write_done_report`/`read_done_report` (v2-only) write/read
  `done-report.md` directly, under `ticket_lock`.

`frob.tickets._reporting.set_done_report` now branches on `_store_mode`
via a new private `_store_done_report` helper (also an ARCH001 line-count
extraction): v1 still splices into `ticket.body` exactly as before; v2
calls `write_done_report` and leaves `ticket.body` untouched, verified
byte-for-byte round-trip.

`attach`'s `_next_attachment_path` routes through the new
`v2_attachments_dir` in v2 mode. `Attachment.path` is still stored
relative to `tickets_dir(root)` in BOTH modes (not the ticket's own
directory) -- this was a deliberate design choice, not an oversight:
`frob.gates`' COV004 sha-verification reconstructs the absolute path as
`Path("tickets") / attachment.path`, and v2's attachment dir already
nests under `tickets_dir`, so no change to gates/__init__.py (out of
scope) was needed to keep that convention intact.

`design/frob.strata`'s `tickets_ledger` store interface= list and
`testsuite` node gained the new public symbols/test classes (SELFAUDIT001
required this); `docs/modules/tickets.md` gained a "v2 backend" section
under Storage internals plus a note on `set_done_report` (AFFECT001
required touching this doc since `_store_mode`/`load_all`/`write_ticket`/
`write_all`/`set_done_report` all changed) -- scope was widened to include
`docs/modules/tickets.md` and `design/frob.strata` via `frob ticket
scope --add` with a stated reason for each.

Remaining `frob check --ticket T-1254` errors (3, all `OPAQUE001` in
`src/frob/app/__init__.py`/`src/frob/app/app.py`) are pre-existing,
outside this ticket's scope, and unrelated to ledger v2 -- verified
present identically on `main` before this ticket started. Every other
gate (`AFFECT`, `ARCH`, `COV`, `DOC`, `PERF`, `SCOPE`, `SELFAUDIT`,
`TEST`, `PRE`) is clean for this diff.

Not implemented (explicitly out of this ticket's scope, per acceptance
[1] and the design doc's own scope note): archiving a v2 ticket
(`git mv tickets/T-0001 tickets/archive/T-0001`), the v1->v2 migration
path, and flipping the repo default away from v1 -- those belong to the
separate migration child ticket the design doc names.

### Changed
```
 design/frob.strata              |   5 ++
 docs/design/ledger-v2.md        |  13 +++
 src/frob/tickets/_store.py      | 145 +++++++++++++++++++++++++++++++
 tests/unit/test_process_lock.py | 159 ++++++++++++++++++++++++++++++++++
 tickets.md                      | 185 +++++++++++++++++++++++++++++++++++++---
 5 files changed, 494 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestV2StoreMode::test_v2_tree_present_is_v2` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_then_load_v2_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_prunes_removed_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestSetDoneReport::test_v2_mode_writes_done_report_md_not_body` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestV2DoneReport::test_write_then_read_back_byte_for_byte` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestV2Attachments::test_attachment_written_under_ticket_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestLoadAllAndWriteTicket::test_write_then_load_single_mode` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 2 error(s), 695 warning(s), 680 waived
- error-findings: OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py
