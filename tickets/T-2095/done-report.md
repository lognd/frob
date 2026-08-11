## Done report

### Changed
- src/frob/tickets/_scope.py::_scope_add_conflicts -- before trusting a
  stale queue-based conflict, checks the holder's live cross-worktree
  lease (if any) and drops the conflict when that lease no longer
  overlaps the requested glob.
- src/frob/tickets/_scope.py::_live_lease_still_conflicts (new) -- the
  narrow, monotone-safe predicate: True unless the holder's live lease
  exists and demonstrably no longer covers the glob.
- tests/test_ticket_leases_cross_worktree.py::TestScopeLeaseConflictPrefersLiveNarrowingOverStaleQueue
  (new) -- real three-worktree repro (main + holder's own worktree +
  a third, never-merged worktree), confirmed FAILED_AT_PARENT before the
  fix, passes after.

### Evidence
- tests/test_ticket_leases_cross_worktree.py::TestScopeLeaseConflictPrefersLiveNarrowingOverStaleQueue::test_narrowed_away_path_is_not_blocked_by_a_stale_local_queue
  -- bound to acceptance[0] and acceptance[1]; designated repro
  (--check-repro at 3bae8bd2f: FAILED_AT_PARENT).
- tests/test_ticket_leases_cross_worktree.py::TestScopeAddRefusesLiveCrossWorktreeLease::test_scope_add_refused_by_unmerged_sibling_worktrees_live_lease
  -- pre-existing test, bound to acceptance[2] (widening still refused;
  the fix never touches that path, only supersedes a stale NARROWING
  false-positive).
- Full file re-run after fix: `tests/test_ticket_leases_cross_worktree.py`
  24 passed, `tests/test_tickets_scope_mutation.py` 35 passed.

### Filed
- T-2104: "A stale blocked_by does not self-heal when its
  blocker narrows scope" -- the ticket's own explicitly-flagged, genuinely
  separate gap (needs the blocked_by mutation/reconciliation surface in
  _doable.py or a lifecycle command, outside this ticket's declared
  scope of src/frob/tickets/_scope.py).

### Gates
- `frob check --ticket T-2095 --budget 90` (both invocations, all 43
  gate groups covered across the two calls): 0 errors.
- `frob check --land-parity`: clean -- 0 unscoped errors, matches what
  the land sweep would see.
- `ruff-check`/`ruff-format` on the two touched files: clean after
  `frob fmt tests/test_ticket_leases_cross_worktree.py` (scoped, not
  repo-wide).

### Changed
```
 src/frob/tickets/_scope.py                 |  50 ++++++++++++
 tests/test_ticket_leases_cross_worktree.py | 127 +++++++++++++++++++++++++++++
 tickets/T-2095/ticket.md                   |  18 ++--
 tickets/T-2104/ticket.md         |  46 +++++++++++
 4 files changed, 236 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_ticket_leases_cross_worktree.py::TestScopeLeaseConflictPrefersLiveNarrowingOverStaleQueue::test_narrowed_away_path_is_not_blocked_by_a_stale_local_queue` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestScopeAddRefusesLiveCrossWorktreeLease::test_scope_add_refused_by_unmerged_sibling_worktrees_live_lease` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: PRE001@tickets/T-2095
