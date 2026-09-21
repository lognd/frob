## Done report

T-5120 measured 32 of 71 in-progress leases held against tickets the root
ledger still called "queued": `transition(..., IN_PROGRESS)` stamped the
worktree/branch onto the gitignored `.git/frob-leases/<id>.json` side
channel only, never the durable ticket record, and left the actual
`tickets.md`/`tickets/<id>` ledger write uncommitted for the fleet-dispatch
shape (`frob ticket work`, one agent worktree per ticket) where the
generic post-dispatch auto-commit sweep only ever commits the CALLING
worktree's own copy of the ledger, never `root`'s.

Fix: `Ticket`'s `extra="allow"` (T-0838) lets `transition()` stamp
`worktree`/`branch` fields directly onto the ticket on every IN_PROGRESS
entry with no schema change (`_start_transition_ledger_fields`,
`src/frob/tickets/_evidence.py`). `record_lease` (`src/frob/tickets/
_leases.py`) now commits that same write through
`commit_ticket_ledger_change` in the exact operation that records the
cross-worktree lease, but ONLY when dispatched agent worktrees are
actually registered (`_list_agent_worktrees`, the same fleet-detection
`_should_skip_root_lease`'s T-2007 guard already uses) -- the ordinary
single-checkout case (the shape most of this repo's own test suite
exercises, e.g. `tests/test_ticket_leases_cross_worktree.py`'s
`_commit_all(repo, "start ...")` pattern) is unchanged.

Verified: new fixture repo with a real `.claude/worktrees/` sibling
worktree shows `transition(..., IN_PROGRESS)` leaves the ledger committed
and the ticket carrying `worktree`/`branch` fields, without a worktree
mirror. Full existing lease/evidence/fleet-worktree suites (275 tests)
still pass unmodified.

### Changed
```
 src/frob/tickets/_evidence.py                      |  34 ++++-
 src/frob/tickets/_leases.py                        |  48 +++++++
 tests/unit/tickets/__init__.py                     |   3 +
 tests/unit/tickets/test_start_transition_ledger.py | 146 +++++++++++++++++++++
 tickets/T-5120/ticket.md                           |   7 +-
 5 files changed, 235 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/tickets/test_start_transition_ledger.py::TestStartTransitionCommitsLedgerInFleetContext::test_in_progress_transition_commits_the_ledger` (pytest node id, verified passing when recorded)
- `tests/unit/tickets/test_start_transition_ledger.py::TestStartTransitionCommitsLedgerInFleetContext::test_in_progress_transition_stamps_worktree_and_branch` (pytest node id, verified passing when recorded)
