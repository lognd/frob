## Done report

### Changed

- src/frob/tickets/_leases.py::enforce_ticket_ownership: now treats an
  EXPIRED cross-worktree lease as "no live holder" (fetches the lease
  record directly and checks `is_lease_ttl_expired`, matching
  `_refuse_if_foreign_live_lease`'s already-existing contract) instead
  of refusing regardless of expiry.
- src/frob/app/ticket_runner/_lifecycle.py::_refuse_if_foreign_live_lease:
  now accepts a `scope` parameter and, on a genuine `--steal`, calls
  `record_lease(root, ticket_id, scope)` immediately (before returning)
  instead of relying solely on the later `transition(...,
  TicketState.IN_PROGRESS)` call to re-pin the lease.
- src/frob/app/ticket_runner/_lifecycle.py::_start: passes `ticket.scope`
  through to `_refuse_if_foreign_live_lease`.
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable._MUTATING_VERB_INVOCATIONS:
  classified the `anchor` verb (added by T-2079/T-1867) alongside
  `priority`/`kind` -- same forwarding-to-a-ticket-write shape.

### Root cause (measured, three separate mechanisms under one label)

Only 1 of the 4 failures was "an enumeration test correctly flagging an
unclassified verb" (`test_dispatch_table_verbs_are_all_accounted_for` --
`anchor` was genuinely missing from the test's own bucket, no other
defect). The other 3 were a real T-2079 regression, not fixture bugs, in
`enforce_ticket_ownership`'s interaction with two PRE-EXISTING, tested
behaviors:

1. **Expiry gap** (`test_expired_lease_in_another_worktree_does_not_block`):
   `enforce_ticket_ownership` (added by T-2079) called
   `lease_holder_worktree`, which returns a recorded holder regardless of
   whether that lease has aged out. Every OTHER lease reader in the same
   module (`_refuse_if_foreign_live_lease`) already applies
   `is_lease_ttl_expired` before treating a lease as live -- this is the
   T-0782/T-0476 dead-agent recovery path, predating T-2079 by a wide
   margin. The new guard disagreed with the older check and broke that
   path.

2. **Steal-ordering gap**
   (`test_steal_succeeds_and_invalidates_the_other_worktrees_lease`,
   `test_incident_shape_end_to_end`): `_refuse_if_foreign_live_lease`'s
   own docstring documented that a `--steal` does NOT rewrite the lease
   file itself -- it relies on the caller's later
   `transition(..., IN_PROGRESS)` call to re-pin it via
   `_sync_cross_worktree_lease`. That was true and harmless before
   T-2079. After T-2079, `_start`'s EARLIER `_auto_plan_if_queued` step
   (queued -> planned) also writes the ticket, and now every ticket
   write is gated by `enforce_ticket_ownership` -- so that intermediate
   write is refused against the STILL-FOREIGN lease before the steal's
   real re-pin ever executes. A genuine `--steal` invocation could never
   succeed after T-2079 landed.

Per the coordinator's brief: I did NOT weaken the guard to make these
pass. `enforce_ticket_ownership`'s refusal condition (foreign worktree
holds a LIVE, non-expired lease, and this call is not itself a
sanctioned steal) is unchanged; the fix is either agreeing with an
ALREADY-EXISTING carve-out (expiry) or making an already-documented,
already-intended override (`--steal`) actually take effect at the right
time. `TestMainWriteToLeasedTicketIsRefused` (the guard's own dedicated
test file, `tests/test_ticket_ownership_guard.py`, T-2079's own coverage
for "main writing into a ticket it doesn't hold, no expiry, no steal")
still passes unchanged -- the NORMAL-case refusal the coordinator
observed live today is untouched.

### Evidence

- tests/test_ticket_leases.py::TestRefusesForeignLiveLease.test_expired_lease_in_another_worktree_does_not_block
  -- designated repro (FAILED_AT_PARENT at da1535f12f2dce36749de1eff370094dd9ac4a39, current main)
- tests/test_ticket_leases.py::TestStealOverride.test_steal_succeeds_and_invalidates_the_other_worktrees_lease
  -- independently confirmed FAILED_AT_PARENT at the same base
- tests/test_ticket_leases.py::TestDoubleDispatchIncidentRegression.test_incident_shape_end_to_end
  -- independently confirmed FAILED_AT_PARENT at the same base
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable.test_dispatch_table_verbs_are_all_accounted_for
  -- independently confirmed FAILED_AT_PARENT at the same base

Measured commands (full output read, never piped through tail/grep for
the pass/fail verdict itself):
  uv run pytest -o addopts="" tests/test_ticket_leases.py::TestRefusesForeignLiveLease tests/test_ticket_leases.py::TestStealOverride tests/test_ticket_leases.py::TestDoubleDispatchIncidentRegression -q
    -> 5 passed in 1.30s
  uv run pytest -o addopts="" tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable -q
    -> 13 passed in 3.38s (12 original + the new `anchor` parametrization)
  uv run pytest -o addopts="" tests/test_ticket_leases.py -q
    -> 131 passed in 22.61s (whole file, post-merge)
  uv run pytest -o addopts="" tests/test_ticket_ownership_guard.py -q
    -> 3 passed (T-2079's own dedicated guard coverage, unchanged)
  uv run pytest -o addopts="" tests/test_ticket_leases_cross_worktree.py tests/test_tickets_lease.py -q
    -> 52 passed (adjacent lease-machinery regression sweep)
  uv run frob check --only test --ticket T-2103 -> gate:TEST 0 errors,
    25 warnings (repo-wide, pre-existing), 4 waived
  uv run frob check --land-parity -> clean, 0 unscoped errors
    (re-measured after merging main mid-T-2092-land, confirmed tip
    stable ~60s before merging)
  git diff main --diff-filter=D --stat -> empty

### Filed

None -- no further out-of-scope defects found while fixing this.

### Gates

frob check --only test --ticket T-2103: clean (0 errors)
frob check --land-parity: clean (0 unscoped errors, re-measured after
merging main)

### Changed
```
 src/frob/app/ticket_runner/_lifecycle.py | 38 +++++++++++++++++++++++---------
 src/frob/tickets/_leases.py              | 18 ++++++++++++---
 tests/test_ticket_leases.py              |  9 ++++++++
 tickets/T-2103/ticket.md                 | 31 ++++++++++++++++++++++++--
 4 files changed, 80 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestRefusesForeignLiveLease::test_expired_lease_in_another_worktree_does_not_block` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestStealOverride::test_steal_succeeds_and_invalidates_the_other_worktrees_lease` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestDoubleDispatchIncidentRegression::test_incident_shape_end_to_end` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: PRE001@tickets/T-2103
