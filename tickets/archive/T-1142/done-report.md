## Done report

Fixed ticket_flow's undercount of both landed AND filed for any ticket
already moved out of tickets.md into tickets-archive.md by `frob ticket
archive` (the 2026-07-28 real-run incident: landed=0 for two days the
zero-drive record shows ~50 lands each, both followed by an archive
sweep).

Root cause: ticket_flow(root, queue) derives BOTH the filed side
(queue.tickets.values()' created dates) and the landed-mining id set
(queue.tickets.keys(), fed to _mine_done_transitions) purely from
whatever queue the caller passed -- the CLI's own _flow handler passes
load_active's ACTIVE-ONLY view. Once a ticket is archived, its id simply
vanishes from that view, so _mine_done_transitions is never even asked
to look for its done-transition commit -- which is still perfectly
readable in tickets.md's own FULL git history, from before the archive-
sweep commit removed the ticket. No separate tickets-archive.md mining
turned out to be needed for the landed side; the whole bug was scope
(which ids get asked about), not a missing data source.

Fix: ticket_flow now unconditionally merges tickets-archive.md's own
tickets (frob.tickets._store.load_archive, best-effort -- a load failure
degrades to an empty archive view with a logged warning rather than
blocking the whole report) into BOTH the filed-by-day source and the
landed-mining id set, regardless of what view of the active queue the
caller passed in. This means the CLI's load_active call site needed NO
change at all -- the fix lives entirely inside ticket_flow itself, so
every caller benefits uniformly. open_count still only ever counts the
caller's own queue -- an archived ticket is always done/dropped, never a
member of _OPEN_STATES, so merging the archive in cannot change that
count either way; verified by reading _OPEN_STATES' definition, not just
asserted.

Updated docs/modules/tickets.md's "frob ticket flow (T-1100)" section
with a "T-1142 fix" paragraph explaining the undercount and the fix.

Out of scope, not touched: the pre-existing SCOPE002 scope-closure debt
(already tracked as T-1145) and INV006 finding surfaced by `frob check
--ticket T-1142` are unrelated to this diff, confirmed by symbol/file.

### Changed
```
 docs/modules/tickets.md        | 21 ++++++++++++
 src/frob/tickets/__init__.py   | 42 ++++++++++++++++++++++--
 tests/test_tickets_velocity.py | 74 +++++++++++++++++++++++++++++++++++++++++-
 tickets.md                     | 11 +++++--
 4 files changed, 143 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_landed` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_filed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 19 error(s), 1222 warning(s), 428 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, ARCH001@src/frob/doctor.py, ARCH001@src/frob/tickets/__init__.py, COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:295, INV006@src/frob/app/stats_runner.py, PII012@tests/system/test_cli_doctor.py, SELFAUDIT001@design
