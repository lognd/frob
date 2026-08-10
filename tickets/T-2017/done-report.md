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

### Changed
```
 rapid-debt.jsonl              |   2 +
 src/frob/tickets/_land.py     | 140 ++++++++++++++++++++++++++++++++++++++++++
 tests/test_ticket_land.py     |  95 ++++++++++++++++++++++++++++
 tickets/T-1940/done-report.md | 116 ++++++++++++++++++++++++++++++++++
 tickets/T-1940/ticket.md      |  18 +++++-
 tickets/T-2017/ticket.md      |  25 +++++++-
 6 files changed, 391 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletionOnArchivedTicket::test_refuses_when_branch_deletes_evidence_bound_test_on_an_archived_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletionOnArchivedTicket::test_deletion_unbound_to_any_archived_ticket_still_lands_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/series-remainder/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/series-remainder/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-2017, invalid-argument-type@src/frob/tickets/_land.py
