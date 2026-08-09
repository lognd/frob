## Done report

Changed:
- src/frob/tickets/_leases.py::same_worktree_lease -- new shared conflict
  predicate (extracted from `_scope.py`'s `_same_worktree_lease`), the ONE
  home both `_scope.py`'s `--add` collision check and `_doable.py`'s
  `leased_by` now call.
- src/frob/tickets/_scope.py::_same_worktree_lease -- now a thin delegate
  to `frob.tickets._leases.same_worktree_lease`; call sites unchanged.
- src/frob/tickets/_doable.py::leased_by / _leased_by_one_holder (new,
  ARCH001 split) -- `leased_by` now skips any holder that
  `same_worktree_lease` matches BEFORE computing a scope collision, so a
  same-worktree lease can never appear as a `doable`/`doable --show-blocked`
  blocker.
- docs/modules/tickets.md -- documented the fix and the shared predicate.
- tests/test_ticket_leases_cross_worktree.py -- 4 new regression tests
  (TestSameWorktreeLease x2, TestDoableExcludesSameWorktreeLeases x2) using
  real `git worktree add` checkouts, matching this file's existing
  precedent.

Root cause: `_doable.py`'s `leased_by` (which both `doable`'s default
collision filter and `doable --show-blocked`'s explanation use) compared
every candidate against every in-progress ticket's lease with NO
same-worktree exemption. `_scope.py`'s `--add` check already had this
exemption (T-1356's `_same_worktree_lease`) but `_doable.py` had an
independent, un-exempted query -- two homes answering "does this lease
conflict?" differently for the same shape. A worktree cannot conflict with
itself: exactly one working copy, one agent. This made the recommended
grouped-dispatch workflow (several related tickets, one worktree,
legitimately sharing a doc in scope) read as fully self-blocked in
`doable --show-blocked`.

Fix: extracted the T-1356 predicate to
`frob.tickets._leases.same_worktree_lease(root, requesting_id, holder_id)`
-- the ONE shared home. `_scope.py`'s `_same_worktree_lease` now delegates
to it (call sites unchanged). `_doable.py`'s `leased_by` calls it directly
and skips any holder it matches before running the scope-overlap check, so
same-worktree leases can never surface as a blocker in either call site
again without both changing together. Comparison uses glob-expanded lease
scopes via `scope_overlap_globs` (unchanged from before -- this predicate
only decides SKIP/DON'T-SKIP, not the collision test itself), matching
T-1868's own semantic-overlap behaviour.

Measurement (delta proving this fixes real throughput, requirement 5): on
this worktree's live queue (46 doable candidates at measurement time), the
pre-fix `leased_by` logic (no same-worktree exclusion, reproduced inline
against the exact same lease/ticket state) reports 34 candidates blocked
(12 dispatchable); the post-fix logic reports 33 blocked (13
dispatchable) -- one real same-worktree false-positive removed from this
worktree's own current lease set. The originally-filed T-1832/T-1865/
T-1878 3-ticket self-block from t1552-ledger-v2 is no longer live on main
(those tickets have since landed/closed), so it could not be re-measured
directly; the new regression tests (`TestDoableExcludesSameWorktreeLeases`)
reproduce that exact shape synthetically (two same-worktree in-progress
tickets sharing a scope glob) and prove neither blocks the other, while a
cross-worktree collision on the identical scope still blocks, unchanged.

Gates: `uv run frob check --only archgate --ticket T-1883` -- ARCH001 on
`_doable.py::leased_by` (introduced by the fix growing the function past
60 lines) fixed via the `_leased_by_one_holder` split; re-run confirms
clean for this module (only pre-existing `_verify.py::verify_import_
resolution` ARCH001 debt remains, unrelated to this ticket's scope).
`uv run frob check --only scope --ticket T-1883` -- clean (0 errors, 470
warnings, all pre-existing scope-closure suggestions into sibling
tickets-family files this ticket does not touch). REG002/REG008 findings
seen in an earlier unscoped run are pre-existing registry debt (dangling
SYS104/other disposition references) unrelated to any file this ticket
touches.

Filed: none -- no out-of-scope work discovered.

### Changed
```
 tickets/T-1883/ticket.md | 50 +++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 49 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_leases_cross_worktree.py::TestSameWorktreeLease::test_both_leased_to_same_worktree_matches` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestSameWorktreeLease::test_different_worktrees_do_not_match` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestDoableExcludesSameWorktreeLeases::test_same_worktree_colliding_leases_do_not_block_each_other` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestDoableExcludesSameWorktreeLeases::test_cross_worktree_colliding_lease_still_blocks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 1249 warning(s), 692 waived
- error-findings: ARCH001@src/frob/refactor/_verify.py, PRE001@tickets/T-1883, REG002@docs/design/registry/check-coverage.yaml
