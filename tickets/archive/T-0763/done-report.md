## Done report

Added a pre-merge closeability preflight to `frob ticket land`: `_validate_closeable`
(called from `_land_precheck`, before `_land_merge_stage` ever runs `git merge`) now
also calls a new `_validate_acceptance_bound`, which uses the existing T-0572
`unbound_acceptance(ticket)` helper to find any acceptance criterion with no
resolving evidence id and refuse the land (`LandError.NotCloseable`), logging the
specific unbound criterion text, before any merge/finalize/squash commit is made.

Previously this same condition (`AcceptanceUnbound`) was only caught inside
`_close_finalized_ticket`'s `transition(..., DONE)` call, which runs AFTER the
merge-main-into-worktree commit and the finalize commit -- exactly the fail-after-
merge friction this ticket documents (15+ coordinator occurrences).

`EvidenceScopeUnbound` (the `covers_scope` D-05 check) is deliberately left as a
post-merge check: it needs the obligation graph built against the post-merge tree
(`frob.gates`'s job, which `frob.tickets` cannot import per docs/rework.md
cycle-avoidance), so it cannot be moved earlier without a larger architectural
change out of this ticket's scope.

Verification: with the fix reverted (via `git show HEAD:...` swapped in, not
`git stash`, per the worktree-isolation rule), the new test fails exactly as
described -- `land()` returns `Err(CloseFailed)` (not `NotCloseable`) after
having already committed a merge-main-into-worktree commit in the worktree.
With the fix restored, the same test passes: `land()` returns
`Err(NotCloseable)` and BOTH `repo` (main) and `wt` (worktree) `git log --oneline
--all` are byte-identical before/after, and both working trees are clean.

Gates: `frob check --ticket T-0763` chunked (`--only lint/static/gates-fast/
gates-security/gates-native`) all clean, 0 new errors. A full untouched-set
`frob test --base main` run also surfaced unrelated pre-existing failures
(doctor.py scaffold-conformance state, strata export goldens, native sys
audit health) traced to this worktree's stale scaffold/native state, not to
this change -- `git diff main --diff-filter=D --stat` is empty (after
merging main to pick up T-0695, which landed after this worktree branched)
and every test this ticket's own scope touches passes.

### Changed
```
 src/frob/tickets/_land.py | 58 +++++++++++++++++++++++++++------
 tests/test_ticket_land.py | 82 ++++++++++++++++++++++++++++++++++++++++++++++-
 tickets.md                | 46 ++++++++++++++++++++++++--
 3 files changed, 172 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestUnboundAcceptancePreflightBeforeMerge::test_unbound_acceptance_refused_pre_merge_no_commits_created` (pytest node id, verified passing when recorded)
