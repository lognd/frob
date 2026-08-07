## Done report

Changed:
- src/frob/tickets/_store.py::archive_path
- src/frob/tickets/_store.py::load_archive
- src/frob/tickets/_store.py::write_archive
- src/frob/tickets/_store.py::_render_ledger (header parameter)
- src/frob/tickets/__init__.py::archive
- src/frob/tickets/__init__.py::load_active (renamed from the old
  active-only load_queue body)
- src/frob/tickets/__init__.py::load_queue (redefined: now merges active +
  archive via the new `_load_merged` helper)
- src/frob/tickets/__init__.py::transition (blocker resolution now reads
  `_load_merged`, so an archived blocker still resolves as closed)
- src/frob/app/ticket_runner.py::_archive, `_list` switched to `load_active`
- src/frob/app/config.py, src/frob/__main__.py (archive subparser)
- docs/modules/tickets.md (Storage, Public API, Storage internals)

`tickets-archive.md` is the same ledger section format as `tickets.md`,
just a different header. `load_queue` merges both files (DuplicateId on an
id collision between them) because blocked_by/parent references and gate
joins must keep resolving after a ticket is archived -- a done ticket that
becomes a blocker's target must still read as closed, not unknown/open
(covered by test_blocked_by_archived_ticket_resolves_closed). `frob ticket
list`/`doable` deliberately read the active file only (`load_active`), so
the archive never bloats them back up -- the whole point of archiving.
`archive()` is idempotent: a second run with nothing newly done/dropped
returns Ok(0) and touches neither file.

Evidence: see structured `evidence:` list above (9 pytest node ids across
tests/test_tickets.py::TestArchive and
tests/unit/test_ticket_store.py::TestArchiveLedger, recorded via `frob
ticket evidence`).
Filed: none.
Gates: `frob check --ticket T-0096 --only gates` clean (exit 0; remaining
118 warn-level violations are pre-existing repo-wide debt outside this
ticket's scope). Widened scope mid-ticket (via `frob ticket sweep`) to
include `src/frob/__main__.py`, `docs/modules/tickets.md`, `tickets.md`,
and `tickets-archive.md` -- the CLI wiring, docs, and both ledger files this
feature necessarily touches, not anticipated by the ticket's original scope.
