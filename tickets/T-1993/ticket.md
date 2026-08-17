---
id: T-1993
title: 'Cross-worktree lease is last-writer-wins: a stale worktree''s scope change
  reverts a narrowed lease to its old superset'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_scope.py
- tests/test_ticket_leases_cross_worktree.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_leases_cross_worktree.py
  reason: add regression test alongside existing cross-worktree lease tests
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_leases_cross_worktree.py::TestLeaseDeltaReconciliation::test_stale_worktrees_add_does_not_revert_a_siblings_narrowing
- tests/test_ticket_leases_cross_worktree.py::TestLeaseDeltaReconciliation::test_a_legitimate_expansion_from_the_owning_worktree_still_takes_effect
designated_repro_test: tests/test_ticket_leases_cross_worktree.py::TestLeaseDeltaReconciliation::test_stale_worktrees_add_does_not_revert_a_siblings_narrowing
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The shared cross-worktree lease file (`.git/frob-leases/<id>.json`) is
re-recorded by `mutate_scope` from whichever worktree happens to run a
scope change, using THAT worktree's own view of the ticket's scope. When
two worktrees hold divergent copies of the same ticket's ledger entry,
the last writer wins -- and it can overwrite a correct narrow scope with
a stale broad one.

TWO INDEPENDENT OBSERVATIONS, 2026-08-10, both on T-1696:

1. Coordinator: ran `frob ticket scope T-1696 --remove src/frob/tickets/_land.py
   --remove src/frob/app/ticket_runner/_land_cmd.py` from the ROOT checkout.
   The ledger updated correctly (scope became 2 paths). The lease file
   still listed all 4 paths afterwards. Notably a probe
   (`scope T-1638 --add src/frob/tickets/_land.py`) SUCCEEDED at that
   moment despite the stale lease naming that path.
2. A different agent, later: the SAME stale lease BLOCKED its
   `scope --add src/frob/app/ticket_runner/_land_cmd.py`. It resolved it
   by calling `frob.tickets._leases.record_lease` directly from the
   `profile-collapse` worktree with that worktree's current scope --
   re-triggering the existing primitive, not hand-editing anything.

The contradictory symptoms (one blocked, one not) are the tell: the
lease file's contents depend on which worktree last touched the ticket,
so the same stale entry can appear to block or not depending on timing.

MECHANISM: `mutate_scope` re-records the lease only
`if updated.state is TicketState.IN_PROGRESS`, using `updated.scope` --
the scope as seen in the CALLING worktree. The `profile-collapse`
worktree had never merged the coordinator's narrowing commit (verified:
`git merge-base --is-ancestor <narrowing-sha> <worktree HEAD>` is false,
and that worktree's own `tickets/T-1696/ticket.md` still carried the
broad scope plus an independently-added path). So any scope-affecting
operation there rewrote the shared lease back to the old broad set.

WHY IT MATTERS: the lease is the cross-worktree exclusion mechanism under
parallel dispatch. A lease that can silently revert to a superset blocks
other agents from paths nobody is editing -- this cost one agent a
blocked `scope --add` and cost the coordinator a wrong diagnosis (I
initially concluded the narrowing had silently failed).

DO NOT FIX IT THIS WAY:
- Do NOT make the lease file authoritative over the ledger. The ledger is
  the source of truth; the lease is a derived side-channel.
- Do NOT drop the `IN_PROGRESS` guard so every scope change rewrites the
  lease -- that makes the last-writer-wins race MORE likely, not less.
- Do NOT have agents call `record_lease` by hand as the standing remedy.
  It worked as a one-off repair here, but a manual resync step is exactly
  the kind of knowledge-requiring workaround that does not survive.

FIX DIRECTION: derive the lease from the ledger at READ time rather than
caching it at write time, or make the recorded lease carry the ledger
commit it was derived from so a reader can detect that it is stale
relative to main. Either removes last-writer-wins entirely.

ACCEPTANCE: first test must FAIL before the fix -- two worktrees with
divergent copies of one in-progress ticket; narrow the scope in worktree
A, run any scope-affecting operation in worktree B, and assert the
effective lease does NOT revert to B's stale broader set. Then assert a
legitimate scope expansion from the owning worktree still takes effect.

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
