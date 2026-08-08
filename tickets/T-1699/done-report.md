## Done report

Both confirmed-live halves fixed.

1. rapid-debt commit races DirtyMain outside the land lock: fixed via
`_commit_rapid_debt_only_drift` (src/frob/tickets/_land_git_ops.py),
following T-0793's uv.lock precedent -- auto-commits rapid-debt.jsonl
when it is the SOLE dirty path (unlike the uv.lock precedent, which
discards, this commits: the content is real and land-owned), then
`_refuse_if_main_dirty` re-evaluates before refusing.

2. DirtyMain misreads coordinator-owned dirt as a crashed land: fixed
via `_dirt_owned_by_no_open_ticket` (src/frob/tickets/_land.py) --
checks whether any dirty path falls inside any currently open
(queued/planned/in-progress/blocked) ticket's declared scope. When none
does, `_log_dirty_main_refusal` names the real cause explicitly instead
of the generic "has uncommitted changes" message that three agents this
session misread as a crashed land. Fail-closed on an unreadable ledger.

Split _log_dirty_main_refusal out of _refuse_if_main_dirty for
ARCH001. Land lock NOT widened, per the ticket's own explicit
instruction.

Scope correction: test file moved from tests/unit/test_rapid_sweep.py
(different module) to tests/test_ticket_land.py (where DirtyMain tests,
including the T-0793 precedent, already live).

No root-cause fix needed under DEAD001/WIRE001/OPAQUE001/REF002.

### Changed
```
 tickets/T-1699/ticket.md | 24 ++++++++++++++++++++++--
 1 file changed, 22 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit::test_sole_rapid_debt_dirt_is_committed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit::test_a_second_dirty_file_blocks_the_auto_commit` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit::test_no_dirt_at_all_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDirtOwnedByNoOpenTicket::test_path_inside_an_open_tickets_scope_is_not_orphaned` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDirtOwnedByNoOpenTicket::test_path_outside_every_open_tickets_scope_is_orphaned` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDirtOwnedByNoOpenTicket::test_a_done_tickets_scope_does_not_count` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 2 error(s), 1094 warning(s), 731 waived
- error-findings: AFFECT001@src/frob/tickets/_land_git_ops.py, PRE001@tickets/T-1699
