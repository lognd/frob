## Done report

Added `src/frob/tickets/_leases.py`: a cross-worktree scope-lease side
channel under the git COMMON directory (`git rev-parse --git-common-dir`),
which every linked worktree of the same repository resolves to the same
absolute path -- unlike `.git/` itself, which is a per-worktree pointer
file for a linked worktree. `.git/frob-leases/<ticket-id>.json` records
one `LeaseRecord` (scope, worktree path, branch, timestamp) per currently
IN_PROGRESS ticket, written/removed alongside the ledger transition that
creates/ends the hold, so it is a live overlay, not a separate source of
truth: `tickets.md`'s `state:` field in each worktree stays exactly as-is.

Wiring:
- `frob.tickets.transition` calls a new `_sync_cross_worktree_lease` after
  every successful state write: records a lease on entering IN_PROGRESS,
  releases it on leaving. This covers `start`, `close`, `fail`, `requeue`,
  and any other transition path uniformly, with no per-command call site
  to remember.
- `frob.tickets.mutate_scope` (`frob ticket scope --add/--remove`)
  re-records the lease with the ticket's new scope when the ticket is
  IN_PROGRESS, so widening/narrowing scope mid-flight can't leave the
  cross-worktree side-channel showing a stale scope.
- `leased_by` (T-0453's collision check, used by both `doable`'s default
  filter and `--show-blocked`) now consults `_all_leases`, which unions the
  LOCAL ledger's own IN_PROGRESS rows with every lease `read_all_leases`
  finds from OTHER worktrees, local ledger winning on an id collision (it
  is authoritative for anything it already knows about). `root=None`
  keeps the exact old local-only behavior for callers with no repo root.

Liveness guard (per the coordinator's design reminder, folded into this
ticket rather than deferred whole to T-0476): `read_all_leases` skips any
lease file whose recorded worktree path no longer exists on disk -- a
crashed/abandoned worktree's unreleased lease cannot wedge `doable` for
every other worktree forever. This is a structural, cheap check (path
existence), not a full reconcile -- T-0476 is still the ticket for the
fuller two-way liveness reconciliation (dead in-progress ticket ->
requeue; live worktree with no in-progress ticket -> flag/clean).

Real-worktree test coverage (no mocks -- `git worktree add` fixtures,
matching `tests/test_ticket_land.py`'s existing style) in the new
`tests/test_ticket_leases_cross_worktree.py`:
- shared git-common-dir resolution across two linked worktrees
- a lease written by `transition` in worktree A is visible via
  `read_all_leases` from worktree B
- `doable`/`leased_by` in worktree B correctly excludes/flags a ticket
  colliding with a lease worktree A holds, that worktree B's own
  `tickets.md` never recorded locally
- releasing the lease on transitioning back out of IN_PROGRESS
- lease scope refresh on `mutate_scope`
- a lease referencing a now-removed worktree path is treated as stale and
  skipped

All 6 new tests plus the full pre-existing `tests/test_tickets_lease.py`
(24) and `tests/test_ticket_land.py` (41) suites pass together (71 total)
after this change -- `leased_by`'s new `root`-driven cross-worktree lookup
does not perturb any existing local-only behavior.

### Changed
```
 src/frob/tickets/_land.py | 219 ++++++++++++++++++++++++++++++++++++++++------
 tests/test_ticket_land.py |  91 +++++++++++++++++++
 tickets.md                |  98 +++++++++++++++++++--
 3 files changed, 375 insertions(+), 33 deletions(-)
```

### Evidence
- `tests/test_ticket_leases_cross_worktree.py::TestGitCommonDir::test_shared_across_linked_worktrees` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_lease_written_in_one_worktree_seen_in_another` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_doable_in_second_worktree_hides_colliding_ticket` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_release_on_close_removes_the_lease` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_stale_lease_for_a_removed_worktree_is_skipped` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_scope_mutation_refreshes_the_lease` (pytest node id, verified passing when recorded)
