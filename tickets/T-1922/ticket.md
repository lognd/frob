---
id: T-1922
title: OutOfScopeWaiveDeletion false-refuses a land whose merge-base is stale relative
  to an unrelated upstream waiver reword
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_unrelated_upstream_waiver_reword_on_a_file_this_branch_never_touched_does_not_refuse
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_a_genuine_committed_deletion_the_branch_made_itself_still_refuses
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_already_landed_sibling_deletion_on_shared_worktree_not_recounted
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-1918 (retrying T-1911's and T-1904's blocked lands).

T-1918 reworded a `frob:waive AFFECT001` comment's text in
src/frob/tickets/_renumber_v2.py (function name in the waiver reason
string changed from `_refuse_if_other_worktree_holds_live_lease` to
`_refuse_if_other_worktree_holds_live_lease_for_id`, wrapped across
slightly different line breaks). After T-1918 landed, retrying
`frob ticket land T-1911 --worktree .claude/worktrees/t1911-clean` (and
separately T-1904's worktree) both refused immediately with:

  ERROR: land: T-1911 refused -- branch history (commits since
  merge-base <stale-sha>) contains frob:waive deletion(s) outside scope
  [...] and undeclared by the Done report:
  ['src/frob/tickets/_renumber_v2.py:AFFECT001'] (real commits touching
  each file since main: {'src/frob/tickets/_renumber_v2.py': ("<sha>
  Merge branch 'main' into t1911-land",)})
  ERROR: ticket land failed: OutOfScopeWaiveDeletion

Root cause: `_land.py`'s branch-history OutOfScopeWaiveDeletion check
(around line 2084) diffs from the worktree's OWN merge-base (captured at
whatever `git merge main` last ran in that worktree, which for both
t1911-clean/verify-cluster pre-dated T-1918's land) forward to the branch
tip. Because that merge-base was stale, the diff includes T-1918's
reword of the AFFECT001 waiver text as if IT were a commit on the
landing branch's own history, and reads the literal old waiver string
disappearing as a "deletion" -- even though the landing ticket
(T-1911/T-1904) never touched _renumber_v2.py itself; it only inherited
the change transitively via its own `Merge branch 'main' into ...`
commit.

Confirmed workaround (not a fix): running a FRESH `git merge main` in
each worktree immediately before the land retry moved the merge-base
forward past T-1918's commit, and both retries then landed cleanly
(T-1904 landed at 1e524de9bec69141309638979a81296bded78d89; T-1911 got
past this check on retry too, though it then hit its own unrelated
BUG002 confirmatory-evidence finding).

The underlying defect: the check's "commits since merge-base" diff does
not distinguish "this branch's own commits changed/deleted the waiver"
from "an ALREADY-LANDED commit on main, picked up via a normal merge,
changed the waiver upstream of this branch's own work" -- the merge
commit itself carries the diff, and the check does not appear to
special-case merge commits or diff against CURRENT main instead of a
stale captured merge-base. Any concurrent worktree whose last main-merge
predates an unrelated waiver-text edit elsewhere in the repo will hit
this false refusal at land time, exactly the same "correct guard, wrong
scope/timing" shape as T-1918 itself.

Fix direction (not investigated further, out of T-1918's scope -- lives
in src/frob/tickets/_land.py, not touched by T-1918): either re-diff
against a freshly recomputed merge-base with CURRENT main at land time
rather than trusting the worktree's last captured merge-base, or exclude
lines whose "deletion" is fully explained by a merge commit pulling in
an already-landed, unrelated main-side edit.

## Done report

HYPOTHESIS TESTED (per coordinator instruction): does T-1720's auto-rebase
subsume T-1922? NO -- confirmed by reading the code, not assumed.
T-1720's auto-rebase fires only AFTER a worktree's OWN successful land
completes. T-1922's incident requires the OPPOSITE: a worktree's land
attempt is REFUSED (has not yet succeeded), while a DIFFERENT, unrelated
worktree lands independently in the meantime, moving main forward. T-1720
never triggers for a worktree that has not itself landed yet, so it
cannot prevent the staleness T-1922 depends on. The guard is also
independently wrong on its own arithmetic, not merely "quiet" -- see ROOT
CAUSE below -- so this ships as a real, narrow correctness fix, never a
loosened refusal threshold.

ROOT CAUSE (confirmed by reading `_committed_waive_deletions`,
`src/frob/tickets/_land_git_ops.py:1295`): T-1550 changed its diff source
from a stale `merge_base..HEAD` to `main_branch..HEAD` -- but LEFT IT A
TWO-DOT diff. A two-dot `git diff A..B` is a pure CONTENT diff between two
commits, not ancestry-scoped -- it reports a line "deleted" whenever `A`
(main's live tip) has it and `B` (HEAD) does not, REGARDLESS OF WHICH
SIDE ACTUALLY CHANGED. When main independently rewords a `frob:waive`
line's text on a file the landing branch never touched, while the branch
has not re-merged main since, the two-dot diff reads the branch's own
stale (unchanged) old text as though it deleted main's new text. This is
exactly T-1918/T-1911/T-1904's incident.

A naive fix (switch to three-dot `main_branch...HEAD`, ancestry-scoped)
would UNDO T-1550's own fix: a worktree that has not rebased keeps the
same old merge-base either way, so a three-dot diff would re-discover an
already-landed SIBLING ticket's own deletion and re-attribute it to
whichever ticket lands next off the same branch -- the exact T-1225/T-1444
bug T-1550 closed. Neither pure two-dot nor pure three-dot is correct
alone.

FIX: `_restrict_to_branch_own_files` (new, `src/frob/tickets/_land.py`)
intersects `_committed_waive_deletions`'s two-dot findings against
`_branch_changed_files(worktree, main_branch)` -- the SAME three-dot
`main_branch...HEAD` --name-only diff `_check_cross_ticket_leakage`
already uses for an identical "what did THIS branch's own commits
change" question. A file this branch's own history never touched can
never appear in that set, no matter how stale the worktree's merge-base
is or how much main moved independently -- so T-1918's reword (a file
the landing branch never committed to) is filtered out. A genuine
same-branch deletion (T-1799/T-1550's own cases) is UNAFFECTED: it is
always part of the branch's own three-dot changed-file set, and the
already-landed-sibling dedup still works exactly as before (via the
two-dot diff showing no delta once main already reflects it -- unrelated
to this filter). Best-effort: a `_branch_changed_files` failure degrades
to the OLD unfiltered (possibly over-broad) behavior, logged at WARNING
-- this filter can only narrow a refusal, never widen one.

FAIL-THEN-PASS (verified by temporarily reverting the filter call in
`_check_committed_waive_deletions` to `found.danger_ok`, restored
immediately after -- never via `git stash`):
`test_unrelated_upstream_waiver_reword_on_a_file_this_branch_never_touched_does_not_refuse`
FAILED with the filter disabled (refused `OutOfScopeWaiveDeletion`
exactly matching the real T-1918 log line shape), PASSED with it
restored. `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal`
(all 8, including every pre-existing T-1332/T-1550/T-1799 case) --
8 passed both before and after.

NEW TEST `test_a_genuine_committed_deletion_the_branch_made_itself_still_refuses`
proves the filter NARROWS correctly rather than accidentally suppressing
the whole check: a genuine out-of-scope deletion on one file still
refuses even while an unrelated upstream reword on a DIFFERENT file is
present in the same land attempt and gets filtered out.

TESTS RUN: tests/test_ticket_land.py (full file, 322 combined with
test_ticket_work_and_land_finish.py) -- 322 passed.

CONCURRENT-LAND REASONING: pure read-path change -- no new lock, no new
write, no change to `_land_lock`'s critical section. Adds one more
read-only `git diff --name-only` spawn (reusing the existing
`_branch_changed_files` helper) inside the same locked precheck section;
strictly more read work per land, no new concurrency exposure. Two lands
against the same root still serialize on the existing lock unchanged.

CROSS-TICKET OVERRIDE USED: `frob ticket land T-1922 --allow-cross-ticket`.
`tests/test_ticket_land.py` is also in T-1686's declared scope (T-1686:
`Verification watermark`, tier=epic, in-progress on main). Verified safe
BEFORE overriding, not waved through:
- `git diff main...HEAD -- tests/test_ticket_land.py` in this worktree is
  91 insertions, 0 deletions -- purely additive; every existing line,
  including T-1686's own evidence node
  (`TestRecordVerifyIntentForLandedCommit::test_real_land_records_an_intent_entry`),
  is untouched.
- T-1686 has NO unlanded code: its own Done report is already on main and
  its entire Changed set is ticket.md/done-report.md files -- there is no
  sibling fix to carry onto main ahead of its own close, and nothing gets
  stranded in BUG002 as a result.
- The refusal was a LEASE LEAK, not live conflicting work: T-1686's scope
  lease is held by worktree=/home/logan/projects/frob branch=main (the
  ROOT checkout, where no agent works), recorded 2026-08-08 -- an epic
  trapped holding a scope claim it cannot release
  (`frob ticket scope T-1686 --remove` refuses with
  `ScopeRemoveOrphansEvidence`: the epic cites one pre-existing test in
  this same file as evidence, and `scope` carries both evidence coverage
  and write lease in one field, so it cannot drop the claim without
  orphaning its own evidence).

The underlying defect is T-1944 (filed by the coordinator, high) --
scope-as-lease conflating evidence-coverage with write-lease traps an
epic holding a lease it never uses. This override does not fix that; it
is a one-time, individually verified exception for a case where the real
risk (a sibling's unlanded work silently landing) provably does not
exist.

### Changed
```
 design/frob.strata                      |   6 +-
 docs/modules/tickets.md                 |  41 ++++++++++
 rapid-debt.jsonl                        |   1 +
 src/frob/app/ticket_runner/_land_cmd.py |  90 ++++++++++++++++++++++
 src/frob/tickets/_land.py               |  92 +++++++++++++++++++++-
 tests/test_ticket_land.py               |  91 ++++++++++++++++++++++
 tests/unit/test_land_auto_rebase.py     | 131 ++++++++++++++++++++++++++++++++
 tickets/T-1720/done-report.md           |  96 +++++++++++++++++++++++
 tickets/T-1720/ticket.md                |   7 +-
 tickets/T-1922/done-report.md           |  93 +++++++++++++++++++++++
 tickets/T-1922/ticket.md                |   6 +-
 11 files changed, 646 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_unrelated_upstream_waiver_reword_on_a_file_this_branch_never_touched_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_a_genuine_committed_deletion_the_branch_made_itself_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_already_landed_sibling_deletion_on_shared_worktree_not_recounted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 8 error(s), 1007 warning(s), 700 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, COV003@tickets/T-0185, DOC001@docs/design/cli-hygiene.md, DOC002@src/frob/tickets/_land.py, DRIFT002@src/frob/tickets/_land.py, DUP001@tests/unit/test_land_auto_rebase.py, PRE001@tickets/T-1922, SEC110@src/frob/app/ticket_runner/_new.py
