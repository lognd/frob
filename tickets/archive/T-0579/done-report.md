## Done report

Added `frob ticket drop <id> --reason TEXT [--absorbed-by T-####]` as a
first-class CLI transition to DROPPED, replacing the hand-edit workflow
(`state: dropped` typed directly into tickets.md) that left worktree leases
dangling and recorded no reason. New public `frob.tickets.drop_ticket`
appends a dated line under a `## Drop reason` body heading -- same
append-a-section shape as `record_failure`'s `## Failure log` -- then runs
the ordinary DROPPED transition through `frob.tickets.transition`, so a
held lease releases exactly the way any other terminal transition releases
one. New `TicketError.DropReasonMissing` rejects a blank `--reason`.
`--absorbed-by` is an unvalidated cross-reference note appended
parenthetically to the line. Wired into `__main__.py`'s ticket subparser
and `ticket_runner.py`'s dispatch table/usage strings; docs/modules/
tickets.md's state-machine section and public-API/CLI-integration lists
updated. Public API grew (new function + new error variant) so REL001
required a version bump to 0.73.0 plus a CHANGELOG.md entry, both done.

### Changed
```
 CHANGELOG.md                  | 12 ++++++
 docs/modules/tickets.md       | 27 +++++++++++-
 pyproject.toml                |  2 +-
 src/frob/__main__.py          | 23 +++++++++-
 src/frob/app/config.py        |  4 ++
 src/frob/app/ticket_runner.py | 31 ++++++++++++--
 src/frob/tickets/__init__.py  | 53 +++++++++++++++++++++++
 src/frob/tickets/_models.py   |  4 ++
 tests/test_tickets.py         | 98 +++++++++++++++++++++++++++++++++++++++++++
 tickets.md                    | 44 ++++++++++++++++++-
 10 files changed, 288 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestDropTicket::test_drops_queued_ticket_with_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDropTicket::test_records_absorbed_by_reference` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDropTicket::test_blank_reason_is_err` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDropTicket::test_in_progress_ticket_drops_and_releases_lease` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDropTicket::test_unknown_ticket_not_found` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDropTicket::test_appends_preserving_existing_drop_reason_section` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDropCli::test_cli_drops_with_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDropCli::test_cli_requires_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDropCli::test_cli_requires_id` (pytest node id, verified passing when recorded)
