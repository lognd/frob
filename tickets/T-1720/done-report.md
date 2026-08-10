## Done report

SUBSUMPTION CHECK: does this ticket subsume T-1922, or the reverse?
Neither -- both ship independently (see T-1922's own Done report for the
full hypothesis test). This ticket's auto-rebase only fires after THIS
worktree's OWN successful land; T-1922's incident requires the OPPOSITE
timing (a land attempt still refused, while a DIFFERENT worktree lands
meanwhile). They address different staleness windows and do not overlap
in mechanism.

WHAT SHIPPED: `_auto_rebase_worktree_onto_main`
(`src/frob/app/ticket_runner/_land_cmd.py`), called from
`_finish_land_after_success` right after `_print_land_proof` has
confirmed `verified=True`, and only when `--finish`/`--retire-on-proof`
was NOT passed (a worktree about to be deleted gains nothing from being
rebased first). `git rebase <main>` in the worktree; on success, logs the
new state; on a REAL conflict, `git rebase --abort` immediately and logs
a WARNING for manual resolution -- never fails the overall `frob ticket
land` call (the land itself already succeeded and is durable by the time
this runs) and never leaves the worktree mid-rebase.

ORDERING (T-1932's own finding applied here, per the coordinator's
explicit instruction): rebase is a MUTATION of the worktree's own branch
history. It must not run in a position where an already-run guard's
decision could be invalidated by it. `_print_land_proof`'s ancestry/
state check reads `root`'s own `main` ref and the just-landed commit sha
-- NEITHER of which this rebase touches (it only rewrites `worktree`'s
own branch). Calling it strictly AFTER that check (which is where it now
lives) means it cannot retroactively invalidate a verdict already
reached. Nothing later in this same `frob ticket land` invocation
re-reads the worktree's rewritten history, so the mutation introduces no
NEW guard for a LATER step in this call to defeat either -- it is the
final action on the successful, non-`--finish` path.

OPEN QUESTIONS FROM THE TICKET, ANSWERED:
- Unconditional vs. opt-in flag: unconditional (no flag), but SKIPPED
  when `--finish`/`--retire-on-proof` is set -- the worktree is being
  torn down anyway, so rebasing it first is pure waste plus risk.
- Real conflict handling: abort and warn, never fail the land (the land
  already succeeded and published; a rebase conflict is a worktree
  housekeeping problem, not a land-correctness problem) and never leave
  the branch mid-rebase (a half-mutated worktree is exactly the kind of
  state a LATER guard -- e.g. this same series' T-1922 committed-waive-
  deletion scan for the NEXT ticket, or the next ticket's own pre-work
  sweep -- could misread).
- Preemptively dropping known housekeeping commits (`wip: pre-land
  snapshot for T-XXXX`, ledger auto-commits) rather than relying on
  git's generic "patch already upstream" detection: NOT done here --
  git's own detection already handles this correctly (verified by the
  test: the worktree's own real work survives the rebase, replayed onto
  the new base, exactly matching what the manual recipe this ticket
  replaces already produced) and doing it explicitly would duplicate
  logic git already gets right for free. Left as residue only if a
  future measurement shows git's detection missing a real case -- none
  observed.

FAIL-THEN-PASS (verified by temporarily short-circuiting
`_auto_rebase_worktree_onto_main` to a bare `return`, restored
immediately after -- never via `git stash`):
`test_rebases_the_worktree_onto_the_new_main_tip` FAILED with the
function disabled (`_is_ancestor(wt, "main", "HEAD")` was False -- the
worktree never moved), PASSED with it restored.
`tests/unit/test_land_auto_rebase.py` -- 2 passed both before (the
conflict test, unaffected by the short-circuit) and after restoring.

TESTS RUN: tests/unit/test_land_auto_rebase.py (2 passed);
tests/test_ticket_work_and_land_finish.py + tests/test_ticket_land.py
(322 passed combined, no regression from wiring this into
`_finish_land_after_success`).

CONCURRENT-LAND REASONING: the rebase touches ONLY the calling worktree's
own branch -- it never writes to `root`/`main`, never touches another
worktree, and runs strictly AFTER this land's own commit is already
durable on main (post-`LAND-PROOF`). Two concurrent `frob ticket land`
calls against DIFFERENT worktrees are unaffected by each other's
auto-rebase (each rewrites only its own branch). A concurrent land
against the SAME worktree cannot happen (worktree-lease/single-agent
convention); this is a new git operation on the worktree, not a new lock
or shared-state write, so it adds no new contention surface.

CROSS-TICKET OVERRIDE: none needed for T-1720's own diff (this ticket's
scope files are not in T-1686's declared scope) -- noted here only
because T-1922, landed immediately before this in the same series, used
`--allow-cross-ticket` against T-1686's leaked lease on
`tests/test_ticket_land.py`. See T-1922's own Done report for the full
verification (purely additive diff, T-1686 has no unlanded code, root
cause is the lease leak tracked as T-1944). If this land also hits the
same T-1686 collision (e.g. because it now carries T-1922's own already-
landed diff forward through the shared worktree branch until this
worktree rebases), the same override and the same justification apply --
recorded here in advance so the choice is not made silently if it
recurs.

### Changed
```
 design/frob.strata                      |   6 +-
 docs/modules/tickets.md                 |  41 ++++++++++
 rapid-debt.jsonl                        |   1 +
 src/frob/app/ticket_runner/_land_cmd.py |  90 ++++++++++++++++++++++
 src/frob/tickets/_land.py               |  92 +++++++++++++++++++++-
 tests/test_ticket_land.py               |  91 ++++++++++++++++++++++
 tests/unit/test_land_auto_rebase.py     | 131 +++++++++++++++++++++++++++++++
 tickets/T-1720/done-report.md           |  96 +++++++++++++++++++++++
 tickets/T-1720/ticket.md                |   7 +-
 tickets/T-1922/done-report.md           | 132 ++++++++++++++++++++++++++++++++
 tickets/T-1922/ticket.md                |   6 +-
 11 files changed, 685 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/test_land_auto_rebase.py::TestAutoRebaseWorktreeOntoMain::test_rebases_the_worktree_onto_the_new_main_tip` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_auto_rebase.py::TestAutoRebaseWorktreeOntoMain::test_a_real_conflict_aborts_cleanly_and_does_not_fail_the_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 8 error(s), 1416 warning(s), 700 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, COV003@tickets/T-0185, DOC001@docs/design/cli-hygiene.md, DOC002@src/frob/tickets/_land.py, DRIFT002@src/frob/tickets/_land.py, DUP001@tests/unit/test_land_auto_rebase.py, PRE001@tickets/T-1720, SEC110@src/frob/app/ticket_runner/_new.py
