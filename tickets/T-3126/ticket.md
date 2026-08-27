---
id: T-3126
title: Land-commit record still dirties root and moves main without CAS after the
  publish
state: in-progress
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_squash.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3121 (which flipped the squash-apply transaction
onto a disposable worktree and made the landing commit public via a
compare-and-swap `git update-ref`).

T-3121 closes the PRE-publish dirty window in root completely -- measured
76.2% of pre-publish status samples dirty before, 0.0% after. It does not
close the POST-publish one, and that window is out of its scope:

`_record_land_commit(root, final_id, land_sha)` runs in `root` after the
publish. It calls `write_ticket` (dirtying root's working tree), then
`git add <ticket path>`, then `git commit` -- so for the length of that
sequence a sibling's `git status` sees a dirty root again, and the commit
advances `refs/heads/main` with NO compare-and-swap protecting it. That
second property is the more interesting one: T-3121 made the LANDING
commit race-safe, but this follow-up commit can still clobber-by-fast-
forward in a way the landing commit no longer can, and it is the only
remaining root mutation on the land path.

`_post_publish_native_rebuild` also runs in root afterwards, but it writes
only gitignored build artifacts, so it does not dirty a porcelain status.

Two things to decide, and they are separable:
1. Should the land_commit record be folded INTO the landing commit rather
   than being a follow-up? `_record_land_commit`'s own docstring explains
   why it cannot be baked into the commit it names (it names that commit's
   sha, which does not exist until the commit is made). With T-3121's
   fold+CAS shape that objection may now be answerable differently -- the
   sha is known before the ref moves.
2. Failing that, the follow-up commit should at minimum be published the
   same way the landing commit now is: compose it out of tree against the
   just-published tip and CAS-publish it, so it neither dirties root nor
   races.

Acceptance: a concurrent `git --no-optional-locks status --porcelain` poll
of root observes ZERO dirty samples across the WHOLE of a land, publish
and land-commit record included -- with a must-fire fixture proving the
poll would have caught a dirty sample if one occurred (a positive control,
not a bare zero).
