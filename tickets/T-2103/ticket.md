---
id: T-2103
title: 'T-2079 residue: 4 tests in test_ticket_leases.py fail (anchor verb + ownership
  guard not accounted for)'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_ticket_leases.py
- src/frob/tickets/_leases.py
- src/frob/app/ticket_runner/_lifecycle.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: "Investigation found the real root cause of 3 of the 4 named failures is\
    \ a\ngenuine T-2079 ordering/expiry gap, not a fixture bug:\n\n1. enforce_ticket_ownership\
    \ (_leases.py) does not treat an EXPIRED\n   cross-worktree lease as \"no live\
    \ holder\" -- every other reader of\n   leases in this file (_refuse_if_foreign_live_lease)\
    \ already applies\n   is_lease_ttl_expired before treating a lease as live, but\
    \ the new\n   ownership guard does not, so it wrongly refuses the T-0782 dead-agent\n\
    \   recovery path (test_expired_lease_in_another_worktree_does_not_block).\n\n\
    2. _refuse_if_foreign_live_lease (_lifecycle.py)'s --steal path documents\n  \
    \ that the re-pin happens later, inside transition(..., IN_PROGRESS)'s\n   own\
    \ _sync_cross_worktree_lease call -- but _auto_plan_if_queued's\n   earlier transition(...,\
    \ PLANNED) call writes the ticket FIRST and\n   trips enforce_ticket_ownership\
    \ against the OLD (still correctly-live)\n   lease before the re-pin ever happens,\
    \ so a genuine --steal now always\n   fails (test_steal_succeeds_and_invalidates_the_other_worktrees_lease,\n\
    \   test_incident_shape_end_to_end). Fixing this without weakening the\n   guard\
    \ requires moving the re-pin earlier, in _lifecycle.py.\n\nBoth are in _lifecycle.py\
    \ + _leases.py, both already in scope or a\none-file widen of it.\n"
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_leases.py::TestRefusesForeignLiveLease::test_expired_lease_in_another_worktree_does_not_block
- tests/test_ticket_leases.py::TestStealOverride::test_steal_succeeds_and_invalidates_the_other_worktrees_lease
- tests/test_ticket_leases.py::TestDoubleDispatchIncidentRegression::test_incident_shape_end_to_end
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for
designated_repro_test: tests/test_ticket_leases.py::TestRefusesForeignLiveLease::test_expired_lease_in_another_worktree_does_not_block
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2093 (unrelated ticket): 4 tests in
tests/test_ticket_leases.py fail against current main, reproduced
identically at both HEAD and at T-2093's pre-fix parent commit
(confirming they predate T-2093 entirely):

  TestRefusesForeignLiveLease::test_expired_lease_in_another_worktree_does_not_block
  TestStealOverride::test_steal_succeeds_and_invalidates_the_other_worktrees_lease
  TestDoubleDispatchIncidentRegression::test_incident_shape_end_to_end
  TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for

The last one names the mechanism directly:

  AssertionError: verb(s) ['anchor'] exist in the real
  _ticket_dispatch_table() but are not accounted for by
  TestLedgerAutoCommitEnumeratedOverDispatchTable

The other three appear to fail via the new T-2079 ownership guard
(TicketOwnershipViolation) rejecting writes that used to be allowed --
e.g. test_incident_shape_end_to_end's captured log shows:

  ERROR ownership-guard: refusing to write T-0001 from .../wt -- it is
  currently leased to worktree .../main

Likely root cause: T-2079 added a new `anchor` verb/dispatch entry and a
write-ownership guard, and this test file's own coverage (the
enumerated-dispatch-table sentinel test, plus the lease/steal fixtures)
was not updated to match. Reproduce with:

  uv run pytest -o addopts="" tests/test_ticket_leases.py -q

Out of scope for T-2093 (declared scope is src/frob/tickets/_leases.py
plus tests/test_ticket_leases.py for T-2093's own fix only) -- filing
rather than fixing silently.

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
