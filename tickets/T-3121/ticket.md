---
id: T-3121
title: Flip the squash-apply stage onto a disposable worktree and publish by CAS
state: in-progress
kind: feature
origin: human
created: '2026-08-27'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_land_compose.py
- docs/modules/tickets-landing.md
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-3121''s hazard list requires a non-fatal resync field on LandReport (the

    post-CAS resync can fail without failing the land, and the caller must be

    able to see that). LandReport is defined in src/frob/tickets/_models.py, so

    the field addition cannot be made inside the declared scope.

    '
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
acceptance:
- text: Given a real land, when the squash-apply stage runs, then a concurrent `git
    --no-optional-locks -C <root> status --porcelain` poll observes no intermediate
    dirty state before the final atomic publish
  evidence: []
- text: Given two lands racing the same base tip, when the second reaches publish,
    then it gets the existing DirtyMain-class refusal, not a corrupted ref and not
    a silent overwrite
  evidence: []
- text: Given a sibling holding an uncommitted edit to a path the land also changed,
    when the post-publish resync refuses, then land() still returns Ok and the failure
    is reported loudly with the published sha and the operator recovery command
  evidence: []
- text: Given the existing land suites for BUG002/LAND-PROOF/T-3050/T-3061, when they
    run unmodified, then they still pass with zero edits to their assertions
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FOLLOW-ON to T-3089, which landed the RETARGETING half: `_land_squash_apply`
now takes a `stage: Path` naming the checkout the whole six-stage
squash-apply transaction runs in (merge + per-path conflict resolution,
ledger splice, REL001 bump, gate-rule sync, T-0463 completeness assertion,
T-1514 Tier-A sweep, landing commit). It defaults to `root`, so today's
behavior is unchanged byte for byte. All six stages move together; see
docs/modules/tickets-landing.md#frobtickets_land_squash----the-squash-apply
-stage-target-t-3089 for which roles deliberately stay on `root`
(ledger_lock and the T-1036 live base texts, the absorption evidence, the
T-1920 branch-drift guard).

This ticket flips the switch in `_land_locked` (src/frob/tickets/_land.py):

1. Wrap the `_land_squash_apply` call in
   `compose_squash_in_disposable_worktree(root, pre_land_tip, branch_name)`
   (T-3107) and pass the yielded `SquashStage.worktree` as `stage`. The
   primitive already runs the REAL `git merge --squash`, so
   `_squash_and_splice_ledger[_v2]` must SKIP its own merge when a stage
   was composed for it -- decide whether that is a flag on the splice
   helpers or whether the compose moves inside them, but do not let the
   merge run twice.
2. Replace `_commit_squash_apply`'s in-tree `git commit` with
   `fold_worktree_into_commit(root, stage, pre_land_tip, message)` (T-3107)
   followed by `publish_ref_cas(root, "refs/heads/<main>", new_sha,
   pre_land_tip)` (T-3088). A CAS failure means main moved since
   `pre_land_tip` and must surface as the SAME DirtyMain-class refusal
   `land()` already raises for a concurrently-moved tip -- no new error
   class for an old condition. `fold_worktree_into_commit` refuses while
   any path is unmerged, which is what keeps conflict markers out of a
   landing commit; keep that check ahead of the staging.
3. Immediately after a successful publish, still holding the land lock,
   call `resync_root_to_published_tip(root, pre_land_tip, new_sha)`
   (T-3114). Its failure semantics are SETTLED and recorded in T-3089's
   body: post-publish the commit is public and correct, so an Err is NOT a
   land failure -- `land()` still returns Ok(LandReport). Log at ERROR with
   ticket, published sha and the operator recovery command, surface it as a
   non-fatal field on `LandReport`, never revert, and attempt it EXACTLY
   once (a retry races the same sibling).
4. `_land_commit_details`/`_record_land_commit`/`_post_publish_native_rebuild`
   run against `root` AFTER the publish+resync, not against the stage.
5. Rewrite the unwind paths that still assume the transaction lives in
   root. Pre-publish there is nothing in root to unwind: dropping the
   disposable worktree IS the unwind. `_verified_reset_root(stage, ...)`
   against a detached disposable checkout is already correct and cheap, but
   audit every path for one that resets ROOT on a pre-publish failure --
   that is now wrong.

EVERY EXISTING GUARD STAYS WIRED UNCHANGED: BUG002 repro ordering,
LAND-PROOF verification, T-3050's non-QUEUED orphan refusal, T-3061's
pre-land lint gate, and the per-path conflict semantics
`_auto_resolve_out_of_scope_conflicts` carries (T-0479 out-of-scope
ours-resolution, T-1002 union zones, T-1434 elementwise-max on
frob-coverage.lock.json, T-1637 sibling carry-forward, loud SquashConflict
for in-scope). A simpler merge deletes all of that.

KNOWN TRADEOFF to weigh and record, not to silently accept: the ledger
splice still reads root's WORKING-TREE tickets.md as its base (T-1036's
lost-update fix). A concurrent `frob ticket new`/`evidence` writer that
dirtied root's tickets.md is therefore carried into the composed commit
while root still holds it uncommitted, which is exactly the shape
`read-tree -m -u` refuses atomically. Measure how often that fires under a
live fleet before concluding it is acceptable.
