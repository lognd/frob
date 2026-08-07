## Done report

Added a PRE-merge covers_scope preflight simulation (`_validate_scope_covered_preflight`, called from `_land_precheck`) so `frob ticket land` now refuses a landing whose evidence does not cover its scope BEFORE `_land_merge_stage` ever runs `git merge` -- closing the residual fail-after-merge class T-0763 left open for D-05's `covers_scope` callable (the unbound-acceptance/kind/evidence-present preconditions already moved pre-merge in T-0763; covers_scope was the one D-05 check still deferred to post-merge).

The CLI's existing `_land_covers_scope_fn(worktree)` closure (frob.app.ticket_runner, which can import frob.gates) is now invoked twice by `land()`: once pre-merge (the new preflight, against the worktree's still-unmerged tree) and once post-merge (unchanged, the authoritative re-check against the tree that actually lands). No new parameter was needed -- `_land_precheck`/`land()` already threaded a `covers_scope` callable through for the post-merge check; this ticket just calls it one extra time, earlier, and refuses (LandError.NotCloseable) on a `False` answer with git log unchanged on both repo and worktree.

Two new tests added mirroring T-0763's TestUnboundAcceptancePreflightBeforeMerge shape: one asserting a covers_scope=False refusal leaves both git logs byte-identical (no merge/finalize/squash commit), one confirming covers_scope=True still lands normally.

### Changed
```
 tickets.md | 41 +++++++++++++++++++++++++++++++++++++----
 1 file changed, 37 insertions(+), 4 deletions(-)
```

### Evidence
(no evidence recorded)
