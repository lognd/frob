---
id: T-3088
title: 'Land compose: out-of-tree tree/commit-object plumbing + CAS ref publish primitive'
state: done
kind: feature
origin: human
created: '2026-08-27'
priority: high
parent: T-3053
tier: story
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
  glob: tests/unit/test_land_compose.py
  reason: scope this ticket's own test file and doc anchor added alongside the primitive
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: scope this ticket's own test file and doc anchor added alongside the primitive
  actor: logan
  at: '2026-08-27'
evidence:
- tests/unit/test_land_compose.py::TestComposeTreeOutOfTree::test_worktree_untouched_by_compose
- tests/unit/test_land_compose.py::TestComposeTreeOutOfTree::test_composed_commit_contains_the_patch
- tests/unit/test_land_compose.py::TestComposeTreeOutOfTree::test_compose_failure_returns_err
- tests/unit/test_land_compose.py::TestPublishRefCas::test_sequential_publishes_succeed
- tests/unit/test_land_compose.py::TestPublishRefCas::test_racing_publish_second_gets_ref_moved
designated_repro_test: null
acceptance:
- text: Given a scratch repo, when compose_tree_out_of_tree builds a commit, then
    the checked-out working tree is never touched
  evidence:
  - tests/unit/test_land_compose.py::TestComposeTreeOutOfTree::test_worktree_untouched_by_compose
  - tests/unit/test_land_compose.py::TestComposeTreeOutOfTree::test_composed_commit_contains_the_patch
  - tests/unit/test_land_compose.py::TestComposeTreeOutOfTree::test_compose_failure_returns_err
- text: Given two racing publish_ref_cas calls with the same expected_old_sha, when
    the second runs after the first succeeds, then it returns Err(RefMoved) and the
    ref is not corrupted
  evidence:
  - tests/unit/test_land_compose.py::TestPublishRefCas::test_sequential_publishes_succeed
  - tests/unit/test_land_compose.py::TestPublishRefCas::test_racing_publish_second_gets_ref_moved
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DECOMPOSITION CHILD 1 of T-3053 (parent epic).

CONTEXT. T-3053 as filed carries no body, no plan and no scope -- it names
only a target shape ("compose out-of-tree and publish via update-ref CAS")
for the land pipeline. Direct measurement of the current pipeline
(src/frob/tickets/_land*.py, ~14.5k lines across 10 modules) shows every
stage operates by mutating the ROOT'S OWN CHECKED-OUT WORKING TREE directly:
_land_squash.py runs `git merge --squash --no-commit` against `root`, later
stages `git reset --hard` to `pre_land_tip`, read/write tickets.md and
CHANGELOG.md as plain files in that tree, and the final commit is an
unconditional `git commit` that "advances whatever branch ref HEAD currently
names" (see _assert_still_on_expected_branch's own docstring). This is why a
concurrent land observes a dirty root mid-land (T-3066 incident cited in the
parent brief) -- there is no way to compose the prospective commit without
publishing intermediate state into the one shared tree.

Rewriting this into a true out-of-tree compose (build the new tree via git
plumbing -- update-index/write-tree/commit-tree against a private index and
GIT_WORK_TREE, or a throwaway worktree -- then publish with a single
compare-and-swap `git update-ref refs/heads/main <new-sha> <old-sha>`) is a
full redesign of the commit-construction stage AND every downstream stage
that currently assumes root's working tree already reflects the pending
change (ledger splice diffing, evidence verification, REL001 version bump,
uv.lock/native rebuild, the post-commit LAND-PROOF check). It cannot be done
as one safe increment against the most contended code in the repo without
first sequencing the change.

THIS CHILD'S SCOPE: design and land ONLY the plumbing primitive, with zero
behavioral change to the real land path yet.

Add a new pure-git helper module `frob.tickets._land_compose` providing:
  - `compose_tree_out_of_tree(repo, base_commit, patch_source) -> Result[sha, LandError]`
    that builds a git tree object representing base_commit plus the given
    changes using `git update-index`/`git write-tree`/`git commit-tree`
    against a scratch index file (GIT_INDEX_FILE env var) and does NOT touch
    the checked-out working tree or HEAD at all.
  - `publish_ref_cas(repo, ref, expected_old_sha, new_sha) -> Result[None, LandError]`
    wrapping `git update-ref <ref> <new_sha> <expected_old_sha>`, whose
    failure mode (ref moved concurrently) is a distinct LandError variant
    (`RefMoved`) so callers can distinguish "someone landed first" from a
    generic git failure.

Do NOT wire these into `land()` yet -- that is child 2. This ticket's
acceptance is the primitive existing, unit-tested in isolation (a scratch
bare repo, not the live root), and proven safe under concurrency:

ACCEPTANCE
- `compose_tree_out_of_tree` builds a tree/commit against a scratch index
  without ever invoking `git checkout`, `git reset`, or touching the
  actual worktree files -- fixture asserts the working tree's mtime/content
  is untouched by the call.
- `publish_ref_cas` succeeds when expected_old_sha matches the ref's current
  value, and returns `Err(RefMoved)` -- not a silent no-op, not a corrupt
  ref -- when it does not. Must-fire fixture: two publishes racing the same
  expected_old_sha, second one gets RefMoved.
- Must-stay-quiet fixture: sequential (non-racing) compose+publish pairs
  succeed every time.