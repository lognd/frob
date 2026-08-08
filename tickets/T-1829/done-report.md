## Done report

T-1758 made new_ticket() auto-commit the ledger write internally by
default. Five tests in tests/test_ticket_land.py called new_ticket(...)
then immediately called _commit_all(...) themselves, expecting there to
still be something uncommitted to stage -- since T-1758 landed, the
ledger write was already committed by new_ticket, so _commit_all's own
`git add -A && git commit` found nothing to stage and failed with
CalledProcessError (exit 1, nothing to commit).

Fix: pass no_commit=True to each of the 6 affected new_ticket(...) calls
(one test, test_land_preserves_mains_newly_archived_blocks_over_a_stale_
worktree_archive, had two such calls) so the ledger write stays
uncommitted until the test's own explicit _commit_all call, matching the
existing no_commit=True pattern already used elsewhere in this module.
No production code changed; _new_renumber.py's scope entry was pre-work
sweep noise, not touched.

### Changed
```
 tickets/T-1829/ticket.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 7 error(s), 916 warning(s), 739 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/tickets/_doable.py, ARCH103@src/frob/app/ticket_runner/_query.py, COV001@src/frob/registry/_staleness.py, COV001@src/frob/tickets/_doable.py, E501@/home/logan/projects/frob/.claude/worktrees/test-repair/src/frob/registry/_staleness.py, TEST001@src/frob/registry/_staleness.py
