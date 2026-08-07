## Done report

Added `--archived` reach to `frob ticket evidence <id> --replace OLD NEW`
(2026-08-05 incident: COV003 fired on archived T-1269/T-1495 after their
bound tests were renamed; evidence --replace answered NotFound because
the store only reads active tickets.md/v2 active dirs; the coordinator
worked around it with a raw string swap directly in
tickets-archive.md).

Root cause: `_load_one` (via `load_all`) and `write_ticket` both only
ever see ACTIVE storage. Added `write_archived_ticket` (src/frob/tickets/
_store.py) -- the archive-side analog of write_ticket: v2 mode writes
under tickets/archive/T-####/ticket.md via the per-ticket ticket_lock;
single mode splices into tickets-archive.md's raw text under the same
T-1536 post-splice integrity check write_ticket already holds for the
active ledger, so a repair can never itself corrupt a sibling archived
ticket.

Wired `archived: bool = False` through replace_evidence/
_prepare_replace_evidence (src/frob/tickets/_evidence.py): archived=True
loads via load_archive instead of _load_one, and writes back via
write_archived_ticket instead of write_ticket -- so a repair lands in
the archive, never resurrecting the ticket into active storage as a
side effect. Added the --archived CLI flag (parser + AppConfig field +
_config_external.py whitelist + _verify.py dispatch wiring).

Evidence: 3 direct write_archived_ticket unit tests (v2 mode, single
mode, sibling-preservation in single mode) plus 2 CLI-level tests
(archived reach works and rebinds without resurrecting; the same
scenario WITHOUT --archived still fails NotFound, proving the flag is
load-bearing).

Out-of-scope discoveries (both T-1553 fallout found while running this
ticket's own targeted tests, unrelated to this ticket's own changes):
11 tests across tests/unit/test_ticket_store.py and
tests/test_tickets_evidence_cli.py asserted v1-mode behavior against a
bare (now v2-default) tmp_path. Fixed by the coordinator in this same
worktree before landing (module-level autouse v1 pin, the T-1553
fixture pattern; fresh-repo default test renamed to assert the v2
contract) -- no follow-up ticket remains open for this.

### Changed
```
 docs/design/ledger-v2.md                   |  21 +-
 docs/modules/cli.md                        |  12 +
 docs/modules/tickets.md                    |  54 +++-
 src/frob/_cli_parsers/_ticket/_closeout.py |  10 +
 src/frob/_cli_parsers/_ticket/_progress.py |   9 +
 src/frob/app/_config_external.py           |   4 +
 src/frob/app/config.py                     |  11 +
 src/frob/app/ticket_runner/__init__.py     |   2 +-
 src/frob/app/ticket_runner/_query.py       |  21 +-
 src/frob/app/ticket_runner/_verify.py      |  21 +-
 src/frob/tickets/_evidence.py              |  61 +++-
 src/frob/tickets/_new_renumber.py          |  11 +-
 src/frob/tickets/_reporting.py             |  13 +-
 src/frob/tickets/_store.py                 | 114 +++++--
 tests/test_ticket_land.py                  |  32 ++
 tests/test_tickets.py                      | 104 ++++++
 tests/test_tickets_collision.py            |  17 +
 tests/test_tickets_evidence_cli.py         | 104 ++++++
 tests/test_tickets_migration.py            |  63 +++-
 tests/test_tickets_velocity.py             |  20 +-
 tests/unit/test_ticket_store.py            | 114 ++++++-
 tickets.md                                 | 495 ++++++++++++++++++++++++++++-
 22 files changed, 1245 insertions(+), 68 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_v2_mode_writes_under_archive_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_single_mode_splices_into_archive_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_single_mode_preserves_sibling_archived_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_replace_archived_reaches_the_archive` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_replace_without_archived_flag_cannot_reach_an_archived_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 610 warning(s), 784 waived
- error-findings: none (measured, zero errors)
