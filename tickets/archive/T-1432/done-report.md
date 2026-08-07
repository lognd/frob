## Done report

_add_and_commit_tickets_md (src/frob/tickets/_leases.py) ran `git add
tickets.md` followed by a bare `git commit -m message`, which commits the
ENTIRE index, not just what this helper staged. The T-1403 c2fd45da
incident: a conflicted git stash pop auto-stages every file that merged
cleanly, and anything left staged that way rode along into the next
ledger commit under an unrelated chore(tickets) message, poisoning git
blame/bisect archaeology for whatever it swept in.

Fix: pathspec-limit the commit (git commit -m message -- tickets.md,
git's documented way to commit only a named path regardless of what else
is staged) so the ledger commit can never contain anything but
tickets.md. This is a one-line change to the single helper both
commit_start_transition and commit_ticket_ledger_change funnel through
(per the ticket's own note), so it covers every caller: frob ticket
start/new/drop/fail.

Added a regression test
(test_pre_staged_unrelated_file_never_rides_along_into_the_commit) that
stages a sentinel file, runs commit_ticket_ledger_change, and asserts the
sentinel stays staged (git status shows "A  sentinel.py" both before and
after) and is absent from the resulting commit's file list (git log -1
--name-only shows only tickets.md).

### Changed
```
 docs/modules/tickets.md                      |  82 ++++++++++-
 src/frob/app/ticket_runner/_close_cmd.py     |  51 ++++---
 src/frob/app/ticket_runner/_land_cmd.py      |  82 ++++++++++-
 src/frob/tickets/_archive.py                 |  65 +++++++--
 src/frob/tickets/_leases.py                  |  32 ++++-
 tests/test_ticket_leases.py                  |  53 +++++++
 tests/test_ticket_merge_driver.py            | 185 ++++++++++++++++++++++++-
 tests/test_tickets.py                        |  44 ++++++
 tests/unit/test_ticket_close_bug002_t1438.py | 140 +++++++++++++++++++
 tickets.md                                   | 199 ++++++++++++++++++++++++++-
 10 files changed, 886 insertions(+), 47 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_pre_staged_unrelated_file_never_rides_along_into_the_commit` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 5 error(s), 380 warning(s), 693 waived
- error-findings: DUP001@tests/test_ticket_merge_driver.py, OPAQUE001@tests/unit/test_ticket_close_bug002_t1438.py, PRE001@tickets/T-1432, SELFAUDIT001@design, WIRE001@tests/unit/test_ticket_close_bug002_t1438.py
