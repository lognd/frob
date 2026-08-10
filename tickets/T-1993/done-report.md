## Done report

Mechanism confirmed matches the ticket's own diagnosis: mutate_scope (and
demote_to_evidence_only) re-record the cross-worktree lease from
`updated.scope` -- this worktree's OWN just-written ticket.md snapshot --
which can be stale relative to what a sibling worktree already narrowed
the SHARED lease to, because tickets/<id>/ticket.md is a per-worktree git
checkout that only syncs on merge. A worktree that never merged a
sibling's narrowing commit still computes its own "updated.scope" as a
superset, and writing that superset into the shared lease file reverts
the sibling's narrowing purely because it wrote last.

Fix (confined entirely to src/frob/tickets/_scope.py, both lease-write
call sites -- mutate_scope and demote_to_evidence_only): a new
_lease_scope_to_record(root, ticket_id, updated_scope, add_globs,
remove_globs) helper. When a lease is ALREADY recorded for ticket_id
(read via the existing frob.tickets._leases.read_all_leases), the scope
written back is the add/remove DELTA this call actually validated and
wrote to the ledger, applied ON TOP of the lease's own current recorded
scope -- not a wholesale overwrite from this worktree's local ledger
snapshot. A fully up-to-date worktree computes the identical result
either way (local scope and recorded lease scope already agree), so nothing
changes for the common case. A stale worktree's legitimate delta (e.g.
adding a brand-new path nobody has touched) now lands on top of the
lease's true current state instead of reverting it. Falls back to
updated_scope when no lease is recorded yet (first IN_PROGRESS entry --
nothing to reconcile against) or if the lease read itself fails
(best-effort side channel, matching record_lease's own posture).

This does NOT make the lease authoritative over the ledger -- the ledger
write already happened via _write_scope_mutation/_demote_to_evidence_only_
locked, unaffected by this change; only the DERIVED lease mirror written
AFTER that ledger write is reconciled against its own prior state.
Does NOT touch the IN_PROGRESS guard (still: lease is only (re)written
while the ticket is IN_PROGRESS). Does NOT introduce a standing manual
`record_lease` workaround -- the fix is in the library call path itself,
every caller of mutate_scope/demote_to_evidence_only gets it for free.

Verified fail-before-fix per the acceptance criterion: reverted
src/frob/tickets/_scope.py to its pre-fix content (saved my own diff as
a patch first, git checkout -- <file> to restore my OWN uncommitted
edit within the same worktree/branch -- not the forbidden cross-branch
move), ran the new test
TestLeaseDeltaReconciliation::test_stale_worktrees_add_does_not_revert_a_siblings_narrowing,
confirmed it failed (AssertionError: "src/other.py" reappeared in the
recorded lease after the stale worktree's add). Re-applied the fix patch,
same test passes. Second test
(test_a_legitimate_expansion_from_the_owning_worktree_still_takes_effect)
asserts a genuine scope expansion from the OWNING (up-to-date) worktree
still takes full effect -- guards against the delta-merge fix
accidentally under-recording a real expansion.

Both new tests use real `git worktree add` checkouts sharing one git
common dir (matching this file's own existing fixture pattern), since
the bug is specifically about two DIFFERENT on-disk copies of the same
ticket file -- a single tmp_path fixture cannot exercise it.

Full test_ticket_leases_cross_worktree.py + test_tickets_scope_mutation.py
suite (56 tests) passes with the fix. Two pre-existing, unrelated
failures in test_ticket_leases.py (TestLedgerAutoCommitEnumeratedOverDispatchTable
-- an "anchor" verb not accounted for in a dispatch-table enumeration
test; a flaky land-lock process-scan test) reproduce identically with the
fix reverted, confirming they are not caused by this change.

Doc drift note: docs/modules/tickets.md's "Cross-worktree lease
side-channel (T-0473)" section states "mutate_scope re-writes it when an
in-progress ticket's scope changes, so it never drifts from the ledger's
own state:/scope: fields" -- this sentence is now only true for an
up-to-date worktree; the file is currently held by another in-progress
ticket's live lease (T-1696) and could not be added to this ticket's
scope. Filing residue to update that section once the lease frees.

### Changed
```
 tickets/T-1993/ticket.md | 14 ++++++++++++--
 1 file changed, 12 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_leases_cross_worktree.py::TestLeaseDeltaReconciliation::test_stale_worktrees_add_does_not_revert_a_siblings_narrowing` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestLeaseDeltaReconciliation::test_a_legitimate_expansion_from_the_owning_worktree_still_takes_effect` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/tickets/_scope.py, DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/ticket-bookkeeping/tests/unit/test_tickets_evidence_only_scope.py
