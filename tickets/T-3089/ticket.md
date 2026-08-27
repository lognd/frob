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
