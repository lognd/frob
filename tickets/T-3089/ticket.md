---
id: T-3089
title: Wire out-of-tree compose+CAS publish into the squash-apply land stage
state: queued
kind: feature
origin: human
created: '2026-08-27'
priority: high
blocked_by:
- T-3088
- T-3095
- T-3107
parent: T-3053
tier: story
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_land_compose.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'series BM re-scope: the wire-up as planned loses three-way conflict semantics
    and leaves six index-consuming stages unfed; git 2.34.1 has no merge-tree --write-tree'
  actor: logan
  at: '2026-08-27'
  old_length: 2574
  new_length: 4298
designated_repro_test: null
acceptance:
- text: Given a concurrent git status poll during a real land, when the squash-apply
    stage runs, then no intermediate dirty state is observable before the final atomic
    publish
  evidence: []
- text: Given two lands racing the same base tip, when the second reaches publish,
    then it gets the existing DirtyMain-class refusal, not a corrupted ref
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DECOMPOSITION CHILD 2 of T-3053 (parent epic). BLOCKED BY child 1
(_land_compose primitive must exist first).

Wire `compose_tree_out_of_tree` + `publish_ref_cas` (child 1) into the ONE
narrowest real stage that currently dirties root's shared working tree in a
way siblings can observe mid-land: `_squash_and_splice_ledger` /
`_land_squash_apply` in src/frob/tickets/_land_squash.py, which today runs
`git merge --squash --no-commit` directly against root then leaves it
staged-but-uncommitted while later stages (ledger splice, evidence checks,
REL001 bump) run -- exactly the window T-3066's land was observed staging
into the shared tree.

Replace that stage's mechanism only: compose the squash-merge result as a
tree object out-of-tree (against a scratch index seeded from root's current
HEAD, with the worktree branch's diff applied via `git read-tree`/`git
apply --cached` or equivalent plumbing -- no working-tree checkout), build
the commit object, then `publish_ref_cas` it onto main's branch ref in one
atomic step. If the CAS fails (main moved since land captured pre_land_tip),
refuse with the SAME `DirtyMain`-class error `land()` already raises for a
concurrently-moved tip -- do not invent a new error class for an old
condition.

Every existing guard stays wired unchanged: BUG002 repro ordering,
LAND-PROOF verification, the T-3050 non-QUEUED orphan refusal, the T-3061
pre-land lint gate, ledger splice conflict handling. This ticket changes
WHERE the tree is composed, not what content ends up in it or which checks
run over it.

ACCEPTANCE
- During a `frob ticket land --dry-run` (and a real land), `git -C <root>
  status --porcelain` observed from a SEPARATE process at any point during
  the run shows nothing beyond what was true before the land started, until
  the final atomic publish. Must-fire fixture: a concurrent `git status`
  poll during a land, asserting no intermediate dirty state is ever visible
  (this is the DirtyMain repro T-3066 hit -- reproduce it failing at the
  parent commit, per BUG002 test-first discipline, before the fix).
- A land whose main tip moved between preflight and publish gets the
  existing DirtyMain-class refusal, not a corrupted ref and not a silent
  overwrite of the sibling's commit. Must-fire fixture: two lands racing the
  same base tip.
- All pre-existing land test suites for BUG002/LAND-PROOF/T-3050/T-3061
  still pass unmodified -- must-stay-quiet fixture is the existing suite
  green with zero edits to its assertions.
- Measure land wall-clock before/after under comparable load; report it.


RE-SCOPE NOTICE (2026-08-27, series BM). The plan above is WRONG and must
not be executed as written. Three verified reasons, full detail in T-3107's
body:

1. `compose_tree_out_of_tree` (T-3088) is diff-and-apply against a scratch
   index; `_squash_and_splice_ledger` is a three-way merge whose conflict
   handling (`_check_squash_conflicted` ->
   `_auto_resolve_out_of_scope_conflicts`) carries T-0479 out-of-scope
   ours-resolution, T-1002 union zones, the T-1434 coverage-lock merge and
   T-1637's sibling carry-forward. Substituting one for the other silently
   deletes all of it. "Replace that stage's mechanism only" is not a
   substitution that exists.

2. Six downstream stages in `_land_squash_apply_finish` read root's WORKING
   TREE and INDEX (`_splice_and_stage`, `_apply_release_bump`,
   `_apply_gate_rule_sync`, `_assert_land_complete`/`_staged_files`,
   `_apply_pre_commit_sweep_or_unwind`, `_commit_squash_apply`). Composing
   only the squash out-of-tree leaves every one of them reading an index
   nothing populated -- a land that commits nothing while writing
   `state: done`.

3. This machine runs git 2.34.1. `git merge-tree --write-tree` needs 2.38+.
   There is NO plumbing path to an out-of-tree three-way merge here.

CORRECTED APPROACH: use T-3095's disposable-`git worktree` technique --
check out at `pre_land_tip` (never at the composed commit; that breaks
`_apply_release_bump`'s `_verified_reset_root` unwind invariant), run the
real `git merge --squash` there, reuse `_auto_resolve_out_of_scope_conflicts`
verbatim against that worktree, then write-tree/commit-tree/`publish_ref_cas`.
T-3107 builds that primitive; this ticket is now the WIRING of it and is
blocked on T-3107.
