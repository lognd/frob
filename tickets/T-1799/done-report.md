## Done report

T-1795's DirtyMain half of this ask (attribute the deferred-sweep's
rapid-debt.jsonl dirt to the real ticket instead of the static
T-1699/T-1755 pair) turned out to have never actually been landed to
_land_git_ops.py despite its Done report's claim -- T-1821 (this
session, same repo) implemented and landed that half for real
(_staged_rapid_debt_ticket, describe_root_dirt's real-ticket-or-
"unattributed" sweep_hint). That closes the DirtyMain half of this
ticket's scope.

This ticket adds the remaining half: OutOfScopeWaiveDeletion's
committed-history refusal (_check_committed_waive_deletions, _land.py)
used to tell an agent only "revert the offending commit" with no
commit actually named -- the exact "actual identity, not a guess"
gap the ticket describes, just for the waive-deletion refusal rather
than DirtyMain. New _commits_touching_path(worktree, base_ref, file)
(_land_git_ops.py) reads the REAL commit(s) that touched each
offending file off `git log --format='%h %s' base_ref..HEAD -- file`
-- a fact read from git history, never a guess -- and the refusal
message now includes a real {file: (commits...)} mapping alongside the
existing file:rule pairs.

The uncommitted-state refusal (_check_uncommitted_waive_deletions)
does not get the same treatment: by definition nothing is committed
yet there, so there is no commit to name -- `git status`/`git diff`
already show the actual dirty content directly, nothing to attribute.

2 new unit tests for _commits_touching_path (real commit named /
empty when the path was never touched); re-ran the existing
TestCommittedWaiveDeletionRefusal suite (10 tests) to confirm the
message change did not alter refusal behavior, only its text.
tests/test_ticket_land.py has 5 PRE-EXISTING unrelated failures
(TestLand::test_refuses_without_evidence_or_done_report and 4 others)
caused by new_ticket's own auto-commit (a later, unrelated ticket)
leaving `_commit_all(wt, "wip")` with nothing to commit -- confirmed
by diffing this file against main (cad43b691): my only change to it
is the new TestCommitsTouchingPath class, none of the 5 failing tests
are touched.

### Changed
```
 tickets/T-1799/ticket.md | 14 +++++++++++++-
 1 file changed, 13 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_land.py::TestCommitsTouchingPath::test_names_the_real_commit_that_touched_the_file` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommitsTouchingPath::test_empty_when_the_path_was_never_touched` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_out_of_scope_undeclared_waive_deletion_refuses_before_merge` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 7 error(s), 841 warning(s), 739 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/tickets/_doable.py, ARCH103@src/frob/app/ticket_runner/_query.py, COV001@src/frob/registry/_staleness.py, COV001@src/frob/tickets/_doable.py, E501@/home/logan/projects/frob/.claude/worktrees/refusal-attrib/src/frob/registry/_staleness.py, TEST001@src/frob/registry/_staleness.py
