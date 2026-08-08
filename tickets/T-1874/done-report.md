## Done report

Added `_skip_close_for_anchor_no_close_requested` in `_land_finalize.py`, the
third skip-close shape alongside the T-1701 (drop) and T-1818 (fail)
precedents: an `anchor=True` ticket in a non-terminal, not-actively-mid-work
state (QUEUED or BLOCKED -- explicitly excluding IN_PROGRESS and the
terminal states DONE/DROPPED) now publishes its ledger record to main as-is
instead of `_close_finalized_ticket` forcing an illegal `-> done` transition.
Folded into `_skip_close_for_terminal_shortcut`'s existing composition chain.

Verified the lease half explicitly, not just the ledger-record half: this
skip path never calls `transition()` itself, so it never has a lease-release
opportunity to miss -- the lease is released earlier, by the deliberate
`frob ticket requeue`/`block` step (via `transition()`'s own
`_sync_cross_worktree_lease`) that must run before an anchor ticket can ever
reach a non-IN_PROGRESS state in the first place. Added an end-to-end
regression (`TestLandAnchorTicketReleasesLease`) that drives a ticket through
IN_PROGRESS (confirms a lease IS held), set_anchor + requeue (confirms the
lease is released BEFORE land runs), then lands it and confirms the lease
stays released afterward -- the exact T-1820 failure mode (a lease surviving
a land that could never close its anchor ticket's record) this ticket exists
to prevent.

### Changed
```
 tickets/T-1874/ticket.md | 18 +++++++++++++++++-
 1 file changed, 17 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_land_finalize_anchor.py::TestSkipCloseForAnchorNoCloseRequested::test_non_anchor_ticket_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finalize_anchor.py::TestSkipCloseForAnchorNoCloseRequested::test_in_progress_anchor_falls_through` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finalize_anchor.py::TestSkipCloseForAnchorNoCloseRequested::test_done_anchor_falls_through` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finalize_anchor.py::TestSkipCloseForAnchorNoCloseRequested::test_dropped_anchor_falls_through` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finalize_anchor.py::TestSkipCloseForAnchorNoCloseRequested::test_queued_anchor_skips_close` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finalize_anchor.py::TestSkipCloseForAnchorNoCloseRequested::test_blocked_anchor_skips_close` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finalize_anchor.py::TestSkipCloseForAnchorNoCloseRequested::test_queued_anchor_reaches_the_composed_entry_point` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finalize_anchor.py::TestLandAnchorTicketReleasesLease::test_requeued_anchor_ticket_lands_and_releases_its_lease` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 2 error(s), 696 warning(s), 742 waived
- error-findings: PRE001@tickets/T-1874, SELFAUDIT001@design
