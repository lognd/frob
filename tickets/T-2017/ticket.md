---
id: T-2017
title: T-1946's orphaned-evidence guard did not fire on a test RENAME, so T-1963's
  land orphaned T-0907's evidence onto the floor
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_orphaned_evidence.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_orphaned_evidence.py
  reason: T-2017's fix (load_all -> load_queue in _check_orphaned_evidence_deletion)
    needs a regression test where the orphaned evidence's owning ticket is ARCHIVED,
    the actual root cause
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_ticket_land.py
  reason: coordinator flagged 3 COV002 findings on T-1940 tests needing a frob:ticket
    edge to an open ticket; T-2017 is their natural home since it is the live defect
    in that same registry
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletionOnArchivedTicket::test_refuses_when_branch_deletes_evidence_bound_test_on_an_archived_ticket
- tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletionOnArchivedTicket::test_deletion_unbound_to_any_archived_ticket_still_lands_cleanly
- tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test
designated_repro_test: tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletionOnArchivedTicket::test_refuses_when_branch_deletes_evidence_bound_test_on_an_archived_ticket
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-10. T-1946's `_check_orphaned_evidence_deletion`
(`src/frob/tickets/_land.py`) exists precisely to refuse a land whose own
diff "delete[s] or rename[s] a pytest test node bound as evidence on a
DIFFERENT, still-open-or-done ticket". It did not fire, and the orphan
reached main.

THE INSTANCE: T-1963's land (`11c3c824f`) renamed a test in
`tests/test_ticket_land.py`:

    -    def test_repair_refuses_loudly_when_current_tip_has_drifted_from_the_marker(
    +    def test_repair_recovers_even_when_current_tip_has_drifted_from_the_marker(

The rename is CORRECT and should not be reverted -- T-1963 deliberately
changed `_reconcile_one_land_repair_marker` from refusing-on-drift to
recovering-unconditionally, so a test named `..._refuses_loudly_...` had to
be renamed. The defect is that the land was allowed to orphan another
ticket's evidence silently.

The old node id was bound as evidence on T-0907 (`state: done`). Result on
main right now:

    [gate:COV] tickets/T-0907:0  COV003  COV003: T-0907 evidence
    'tests/test_ticket_land.py::TestLandRepairMarker::test_repair_refuses_
    loudly_when_current_tip_has_drifted_from_the_marker' does not resolve
    to a collected test

That COV003 is currently 1 of the repo's 3 floor errors. T-1963's own agent
reported its land floor-neutral in good faith; the finding surfaced only on
a later unscoped measurement.

WHY THIS MATTERS MORE THAN ONE ERROR: this class was previously measured at
4 of 4 of the entire error floor. A guard was built for it. The guard is
now the thing that needs verifying, and a guard that silently fails to fire
is worse than no guard, because it is trusted.

FIRST THING TO DETERMINE (do not assume; measure): why it did not fire. The
leading hypothesis, NOT yet confirmed, is that the guard resolves evidence
against a CACHED test collection -- COV003's own message notes "the
collection cache is keyed on test file content and refreshes automatically
on the next `frob test` / `frob check` run". If the guard consults a
collection snapshot taken before the rename, the OLD node id still resolves
and the guard sees no orphan. A second hypothesis: the guard detects
deletions but treats a rename as unrelated add+delete and misses the
binding. Confirm which (or neither) before designing the fix, and report
the measurement.

## Do not fix it this way
- Do NOT revert or rename-back T-1963's test. The new name is correct; the
  old name describes behavior that no longer exists.
- Do NOT fix this by only repointing T-0907's evidence. That clears today's
  COV003 and leaves the guard broken for the next rename. Repointing is
  necessary but is NOT this ticket's fix.
- Do NOT weaken the guard to a warning because it has false negatives. The
  failure here is under-firing, not over-firing.
- Do NOT add a blanket "refuse any land that renames a test". Renaming a
  test whose behavior changed is correct and routine; the guard must
  identify the EVIDENCE BINDING, not the rename.

## Acceptance criteria
1. A test that FAILS FIRST: construct a land whose diff renames a test node
   bound as evidence on a done ticket, and assert the CURRENT code lands it
   clean (the guard does not fire). Then assert it refuses.
2. The diagnosis is reported as measurement -- state which hypothesis held
   and cite the file:line that made the guard blind.
3. Re-scan main for OTHER evidence orphaned the same way and report the
   count with its denominator; if any exist, they are this ticket's residue
   and need accounting, not silent repointing.
4. A rename of a test bound to NO ticket's evidence must still land clean
   -- assert no over-refusal.