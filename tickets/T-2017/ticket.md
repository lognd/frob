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
land_commit: null
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

## Done report

MEASURED root cause -- NEITHER of the two hypotheses this ticket started from:

Not hypothesis 1 (stale collection cache): the collection cache refreshes on
content change and the guard's own `collect_python_tests(worktree)` call runs live
against the worktree at land time, not a stale snapshot.

Not hypothesis 2 (rename mis-parsed as add+delete): T-1963's rename was a function
rename INSIDE `tests/test_ticket_land.py` -- the FILE path itself never changed, so
`_branch_changed_files`'s three-dot diff correctly included it as a changed path
regardless of add/delete/rename diff semantics.

THE ACTUAL CAUSE: `src/frob/tickets/_land.py:3695` (pre-fix), inside
`_check_orphaned_evidence_deletion`, called `load_all(worktree)` -- which for a
v2-mode repo globs ONLY `tickets/T-####/ticket.md` (the ACTIVE tree,
`frob.tickets._store._v2_glob`), never `tickets/archive/T-####/ticket.md`. T-0907
(state: done) was archived at the v1->v2 ledger migration (`52e58d316`), long
before T-1963 ever ran. So T-0907 was never even a CANDIDATE in `_orphaned_
evidence_findings`'s `for other_id, other in queue.items()` loop
(`src/frob/tickets/_land.py:3729`) -- the guard was structurally blind to it from
the day it was written, independent of collection freshness or diff shape.
Confirmed directly: `frob.tickets._store.load_all(<repo root>)` returns 180
tickets and does NOT include `T-0907`; `frob check`'s own COV003
(`frob.gates._cov003`) caught the exact same orphan on its next unscoped run only
because its loader, `frob.tickets._archive.load_queue`, merges active+archive.

`frob verify explain "COV003:tickets/T-0907"` returned `UNATTRIBUTED (no batch
commit's touched symbols reach this finding)` -- the T-1690 attribution engine
could not map this finding to T-1963's causing commit. This particular finding
class (a ticket-ledger evidence binding going stale, not a code-symbol change) is
outside what the engine's touched-symbol reachability model covers; reporting this
per the coordinator's own method note, since it is worth tracking as a gap in
attribution coverage, not something I worked around by hand-reasoning -- the git
history confirmation above (T-0907 archived at 52e58d316, T-1963's rename diff,
direct `load_all` measurement) is independent of and does not rely on attribution.

Fix: `_check_orphaned_evidence_deletion` now calls `frob.tickets._archive.
load_queue(worktree)` (active+archive merged, `TicketQueue`) instead of `load_all`
-- the same authoritative source `frob check`'s COV003 already uses, so this guard
can no longer diverge from what the unscoped sweep catches.

Re-scan for OTHER evidence orphaned the SAME way (acceptance criterion 3): a real
`frob check --ticket T-2017` run's own COV003 output shows exactly ONE finding on
main right now -- T-0907, the known incident this ticket's OWN subject. Denominator:
10025 non-cmd evidence ids across the full active+archive queue (`load_queue`
measured directly). Count of OTHER instances found: 0. T-0907's own evidence is
NOT repointed here -- per the coordinator, that is owned by another agent; this
ticket only closes the guard defect.

Is the registry's own "stated reason" acceptance bar itself defective (per the
coordinator's sharper framing)? No -- `_check_orphaned_evidence_deletion` is NOT
one of T-1940's acknowledged-gap entries. It is registered in `_COMMITTED_DIFF_
GUARDS` with NO twin and NO exemption reason claiming it as closed; T-1940's Done
report explicitly named it as "identified as diff-content-reading... subject to
the same T-1932 hazard in principle" but that entry's own exemption_reason is
about the DIFFERENT T-1932 mutation-ordering hazard (a Tier-A auto-fix rewriting
content between preflight and wip-commit), not about this active-vs-archive
loader defect. So this is a genuinely SEPARATE bug from what T-1940's registry
was built to track -- not a stated reason that "turned out to be load-bearing".
Worth stating plainly: this defect existed since the check was first written
(T-1946), unrelated to and untouched by T-1940's own registry work.

## Do not fix it this way -- honored
- Did not revert or rename back T-1963's test.
- Did not repoint T-0907's evidence as this ticket's fix (residue, owned elsewhere).
- Did not weaken the guard to a warning.
- Did not add a blanket "refuse any rename".

Changed:
- src/frob/tickets/_land.py::_check_orphaned_evidence_deletion (load_all ->
  load_queue)

Evidence:
- tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletionOnArchivedTicket::test_refuses_when_branch_deletes_evidence_bound_test_on_an_archived_ticket
  -- acceptance criterion 1: constructs the exact T-1963 incident shape (other
  ticket DONE + ARCHIVED via `archive(wt, force=True)`, then a branch diff deletes
  the test its evidence cites). Manually verified FAILS on pre-fix code (git apply
  -R of the fix's source-only diff, rerun: lands clean, matching the real
  incident exactly) and PASSES post-fix.
- tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletionOnArchivedTicket::test_deletion_unbound_to_any_archived_ticket_still_lands_cleanly
  -- acceptance criterion 4: an archived ticket exists but its evidence is
  untouched; must not over-refuse.
- tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test
  -- pre-existing ACTIVE-ticket case, run (not edited) to confirm no regression.
`--designate-repro --designate-repro-force` on the first for the same mechanical
NO_VERDICT-at-parent-commit reason as every other ticket in this series (new test,
same commit as the fix) -- the real repro was verified directly via the saved-
patch revert above.

Also added `# frob:ticket T-2017` edges to the 3 test methods in
`tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness` the
coordinator flagged as carrying COV002 findings after T-1940 landed (changed with
no edge to an open ticket) -- T-2017 is their natural home, being the live defect
in exactly the registry those tests cover.

Full `tests/test_ticket_land.py`: 275/275 pass (247.18s). Full `tests/unit/
test_land_orphaned_evidence.py`: 5/5 pass.

Filed: none new.

Gates: `frob check --ticket T-2017` -- no SCOPE001/COV001/COV002/COV006/TEST001
finding against any new symbol (`_ticket_done`, the new test class, or the
`load_queue` swap) after waiving one WIRE001 (private test-tree helper,
`permanent="true"`, the established exemption class). The 3 SCOPE001 findings
present in this run (rapid-debt.jsonl, tickets/T-1940/*) are this series
worktree's own prior, already-landed T-1940 ticket-ledger commits sitting in
branch history -- not touched by this ticket's diff, same pattern as T-1963's own
residual SCOPE001 findings earlier in this series.

## BUG002 repro-at-parent, measured at a pre-passenger ref

T-1940's land (`ddd2acfecfe6ba9e783b00240eef4ff45d97e125`) carried T-2017's own
fix as a disclosed `--allow-cross-ticket` passenger (both tickets fully evidenced/
Done-reported, genuinely intentional joint landing in one series worktree) --
this put the FIX on main ahead of T-2017's own close, so BUG002's repro-at-parent
check (parent = main, which now already contains the fix) finds T-2017's
designated repro test PASSING at the parent -- not because the evidence is
confirmatory-only, but because of land ORDER (the known passenger-land-order
trap).

MEASURED the real repro at a genuinely pre-passenger ref instead of asserting it:
`git worktree add <tmp> 8cea2c287` (T-1940's own parent commit, the last commit
before ddd2acfe -- verified `git log -1 ddd2acfe^`), copied ONLY the test file
(`tests/unit/test_land_orphaned_evidence.py` as of ddd2acfe) into that checkout
with the FIX itself absent (confirmed: `_check_orphaned_evidence_deletion` at
8cea2c287 still calls `load_all`, not `load_queue`), then ran the exact
designated node:

    cd <tmp-worktree-at-8cea2c287>
    pytest "tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletionOnArchivedTicket::test_refuses_when_branch_deletes_evidence_bound_test_on_an_archived_ticket"

Observed: FAILED --
`assert result.is_err` -> `AssertionError: assert False +  where False =
Ok(None).is_err` -- the guard did not fire at this pre-fix, pre-passenger
commit, exactly the T-2017 defect. This is the proof BUG002 wants: the defect
reproduced at a real ref, the gate is unsatisfiable only because of land order,
not because the evidence never reached the wiring.

frob:waive BUG002 reason="T-1940 landed T-2017's fix as a disclosed --allow-cross-ticket passenger (ddd2acfecfe6ba9e783b00240eef4ff45d97e125), so BUG002's repro-at-parent check (parent=main) now finds the designated test PASSING at the parent -- the fix is already there, not because the evidence is confirmatory. Measured the real repro at 8cea2c287 (T-1940's own parent commit, the last ref before the fix existed anywhere): built a temp worktree there, copied in tests/unit/test_land_orphaned_evidence.py from ddd2acfe with the _land.py fix absent (confirmed _check_orphaned_evidence_deletion still called load_all, not load_queue, at that ref), and ran tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletionOnArchivedTicket::test_refuses_when_branch_deletes_evidence_bound_test_on_an_archived_ticket directly -- it FAILED there (assert result.is_err -> AssertionError: Ok(None).is_err is False), the exact defect, confirming the repro is real and this is a land-order artifact, not confirmatory-only evidence."

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletionOnArchivedTicket::test_refuses_when_branch_deletes_evidence_bound_test_on_an_archived_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletionOnArchivedTicket::test_deletion_unbound_to_any_archived_ticket_still_lands_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, F401@/home/logan/projects/frob/.claude/worktrees/series-remainder/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/series-remainder/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-2017
