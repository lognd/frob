---
id: T-1720
title: frob ticket land should auto-rebase the worktree onto main after a successful
  land
state: done
kind: feature
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/tickets.md
- docs/guides/agent-playbook.md
evidence_scope:
- tests/unit/test_land_auto_rebase.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_merges_the_worktree_onto_the_new_main_tip
- tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_a_real_conflict_aborts_cleanly_and_does_not_fail_the_land
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_land_auto_rebase.py::TestAutoRebaseWorktreeOntoMain::test_a_real_conflict_aborts_cleanly_and_does_not_fail_the_land
  new_node: tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_a_real_conflict_aborts_cleanly_and_does_not_fail_the_land
  reason: 'T-2173 renamed _auto_rebase_worktree_onto_main to

    _auto_sync_worktree_onto_main (rebase replaced by merge) and renamed its

    test class TestAutoRebaseWorktreeOntoMain to TestAutoSyncWorktreeOntoMain

    in the same diff -- T-1720''s bound evidence node ids no longer resolve.

    Re-pointing to the renamed equivalents; the underlying test content and

    assertions this evidence proves are otherwise unchanged.

    '
  actor: logan
  at: '2026-08-11'
- old_node: tests/unit/test_land_auto_rebase.py::TestAutoRebaseWorktreeOntoMain::test_rebases_the_worktree_onto_the_new_main_tip
  new_node: tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_merges_the_worktree_onto_the_new_main_tip
  reason: 'T-2173 renamed _auto_rebase_worktree_onto_main to

    _auto_sync_worktree_onto_main (rebase replaced by merge) and renamed its

    test class TestAutoRebaseWorktreeOntoMain to TestAutoSyncWorktreeOntoMain

    in the same diff -- T-1720''s bound evidence node ids no longer resolve.

    Re-pointing to the renamed equivalents; the underlying test content and

    assertions this evidence proves are otherwise unchanged.

    '
  actor: logan
  at: '2026-08-11'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

Every single land I performed across two ticket groups in this session
(T-1673/T-1630/T-1675/T-1670/T-1679, then T-1714/T-1706) hit the same
sequence: land a ticket successfully (`LAND-PROOF: ... verified=True`),
then the NEXT `frob check --ticket <next-id>` in the same worktree reports
spurious SCOPE001/COV002 findings on files the just-landed ticket touched
-- because the worktree's own commits for that already-landed work are
still present on its branch, and the branch has not moved to include
main's new (squashed) tip. `git diff main` for those files then shows
non-empty content even though the content is byte-identical, because the
branch and main reached the same state via two DIFFERENT commits (the
worktree's own step-by-step history vs. land's squash-apply), so `git
diff main --stat` inherently looks non-empty for anything the worktree
itself changed, whether or not it matches main.

Observed sequence, every time, this session:
1. `frob ticket land T-XXXX --worktree <path>` succeeds, `LAND-PROOF ...
   verified=True`.
2. Start the next ticket in the same worktree; `frob ticket sweep`/`frob
   check --ticket <next>` reports SCOPE001 (files outside declared scope)
   and/or COV002 (changed-with-no-frob:ticket-edge) findings that are
   NOT caused by the next ticket's own work -- they are the just-landed
   ticket's files, which the worktree's branch still carries as its own
   uncommitted-relative-to-main diff.
3. Resolved every time by `git rebase main` in the worktree (dropping the
   now-"patch already upstream" commits git detects automatically, and
   skipping any obsolete `wip: pre-land snapshot for T-XXXX` commits
   land's own machinery leaves behind) BEFORE doing any more gate
   verification for the next ticket.
4. Repeat from step 1 for the next ticket in the series.

This is pure repeated friction -- the exact same manual recipe, by hand,
after every single successful land in a multi-ticket worktree series.
Per the standing directive (systematize repeated friction rather than
re-doing it by hand every time), this should be mechanical.

## Proposal

`frob ticket land --worktree <path>` should, after a successful land
(`verified=True`), automatically `git rebase main` the worktree's own
branch onto the new main tip it just produced -- dropping the now-
redundant commits the same way a manual rebase does (git's own "patch
contents already upstream" detection), before returning control to the
caller. This closes the loop the same way a human currently does by hand,
every time, immediately after every land in this session.

Open questions for whoever picks this up:
- Should this be unconditional, or opt-in via a flag (e.g. `--rebase-
  after`) for a caller that does not want its worktree branch rewritten
  automously? A single-ticket worktree (not a series) may not care either
  way; a series worktree needs it every time.
- What happens if the auto-rebase hits a REAL conflict (not just
  redundant-patch drops) -- should land still report success (the land
  itself is done) and just warn that the auto-rebase needs manual
  attention, rather than let a rebase conflict retroactively fail an
  already-successful land?
- Should the two housekeeping commit classes land already knows about
  (`wip: pre-land snapshot for T-XXXX`, ledger auto-commits) be preemptively
  dropped/skipped rather than relying on git's generic empty-patch
  detection, since land KNOWS which of the worktree's own commits are its
  own now-obsolete staging artifacts?

## Evidence (the actual observed sequence this session)

Every occurrence below is `git rebase main` run in
`.claude/worktrees/agent-ac2dad95d0b2b8809` immediately after a
`LAND-PROOF ... verified=True` line, always resolving 1-3 conflicts (the
shared `rapid-debt.jsonl` append-only log, occasionally a `tickets.md`
splice-driver conflict) and dropping 1-6 "patch contents already
upstream" commits per rebase:

- After landing T-1673: rebased before starting T-1630 (SCOPE001 on
  `rapid-debt.jsonl` and other post-land-sweep-touched files).
- After landing T-1630: rebased before starting T-1675 (same shape).
- After landing T-1675: rebased before starting T-1670 (plus resolving a
  CHANGELOG.md/land-owned-file pre-commit-hook collision on the first
  attempt, which forced an abort-and-rebase-instead-of-merge decision).
- After landing T-1670: rebased before starting T-1679.
- After landing T-1679: rebased before starting T-1714 (2 real conflicts
  in `src/frob/tickets/_store.py`, both trivially resolved by keeping
  HEAD's already-landed content).
- After landing T-1714/merging T-1701 (already landed by another agent):
  rebased before starting T-1706.

Six for six. This ticket exists so the seventh time is automatic.

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
