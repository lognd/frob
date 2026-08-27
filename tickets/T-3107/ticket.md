---
id: T-3107
title: Out-of-tree three-way squash compose via a disposable worktree
state: done
kind: feature
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
- src/frob/tickets/_land_compose.py
- tests/unit/test_land_compose.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets-landing.md
  reason: the new public compose primitives need frob:doc edges (COV001) and LandComposeError's
    new variant needs its affects-closure doc re-acked (AFFECT001); both land in the
    existing _land_compose section of this file
  actor: logan
  at: '2026-08-27'
evidence:
- tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_clean_squash_reports_no_conflicts
- tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_conflicting_squash_reports_the_conflicted_paths
- tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_root_worktree_untouched_by_clean_squash
- tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_root_worktree_untouched_by_conflicted_squash
- tests/unit/test_land_compose.py::TestFoldWorktreeIntoCommit::test_folded_commit_contains_both_sides
- tests/unit/test_land_compose.py::TestFoldWorktreeIntoCommit::test_fold_refuses_while_paths_are_unmerged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 1ee8d593fdfb7cd8f8a830ecace8de628bde1d64
---
T-3089 re-scope child 1. T-3089 as written is UNDER-SCOPED and has been
failed with the finding recorded; this is the first real increment out of
its decomposition.

FINDING (verified against the code, not inferred):

1. `compose_tree_out_of_tree` (T-3088, _land_compose.py) is DIFF-AND-APPLY:
   `git diff base patch_source` piped through `git apply --cached` against a
   scratch GIT_INDEX_FILE. It has exactly two outcomes -- applies, or
   `ComposeFailed`. It cannot classify a conflicted path, cannot take one
   side per path, and has no notion of a merge base.

2. `_squash_and_splice_ledger` (_land_squash.py:252) is a THREE-WAY MERGE:
   `git merge --squash --no-commit`, then `_check_squash_conflicted` ->
   `_auto_resolve_out_of_scope_conflicts` (_land_git_ops.py:1501), which
   reads `_conflicted_files(cwd)`, resolves registered union zones by a
   union-merge strategy, applies the T-1434 elementwise-max merge to
   frob-coverage.lock.json, `git checkout --ours` + stages every remaining
   OUT-OF-SCOPE conflicted path (T-0479), and leaves IN-SCOPE conflicts as a
   loud `SquashConflict` refusal. Substituting diff-and-apply silently
   deletes all of that: every out-of-scope conflict becomes a blanket
   ComposeFailed, and T-0479/T-1002/T-1434/T-1637 stop existing.

3. The under-scoping goes further than the merge semantics. SIX downstream
   stages in `_land_squash_apply_finish` consume root's WORKING TREE and
   INDEX, not a tree object: `_splice_and_stage` writes tickets.md and
   `git add`s it (_land_git_ops.py:1050), `_apply_release_bump`,
   `_apply_gate_rule_sync`, `_assert_land_complete` via `_staged_files`
   (`git diff --cached`), `_apply_pre_commit_sweep_or_unwind` (Tier-A
   auto-fix MUTATES content), and `_commit_squash_apply`. Changing only the
   squash mechanism leaves every one of them reading an index the compose
   never populates -- i.e. a land that commits nothing while writing
   `state: done`, the exact failure this machinery already produced once.

4. ENVIRONMENTAL CONSTRAINT that decides the design: this machine runs git
   2.34.1. `git merge-tree --write-tree` (a real out-of-tree three-way merge
   producing a tree oid) requires git 2.38+. 2.34's `merge-tree` is the OLD
   form: it prints a textual merge preview to stdout and writes NO tree
   object and NO index. So "extend the primitive to do a real three-way
   merge out-of-tree" is not available via plumbing at all.

CONSEQUENCE: the only way to get a genuine three-way squash merge, with
conflict detection and the existing per-path resolution machinery intact,
off the shared root, is T-3095's own technique -- a DISPOSABLE `git
worktree` checked out at `pre_land_tip`, where `git merge --squash` runs
normally against that worktree's private index and working tree, then
`write-tree`/`commit-tree`/`publish_ref_cas`. That also reuses a landed
piece instead of inventing a fourth composition path, and it is what makes
T-3102's Tier-A auto-fix (which must mutate real files on disk) possible at
all.

WANTED (this ticket, primitive only -- no wiring into the live land path):
`compose_squash_in_disposable_worktree(repo, base_commit, branch_name)` in
src/frob/tickets/_land_compose.py: cut a disposable `git worktree add
--detach` at `base_commit`, run `git merge --squash --no-commit
<branch_name>` inside it, and hand the caller both the disposable worktree
path and the conflicted-path set, so the caller can run the EXISTING
`_auto_resolve_out_of_scope_conflicts` against that disposable worktree
verbatim and then fold it into a commit object. `repo`'s own working tree,
index and HEAD must be untouched throughout. Wiring is the next child's
scope.

HARD-WON DETAIL inherited from T-3095: check out at `pre_land_tip`, NEVER at
a composed commit -- checking out the composed commit breaks
`_apply_release_bump`'s `_verified_reset_root` unwind invariant.

ACCEPTANCE
- must-fire: a branch whose change genuinely conflicts with base yields the
  conflicted path set, not a blanket failure.
- must-stay-quiet: a clean, disjoint branch composes a commit whose tree
  contains both sides' content.
- root-untouched: `git status --porcelain` on `repo` is byte-identical
  before and after, in BOTH the clean and the conflicted case.