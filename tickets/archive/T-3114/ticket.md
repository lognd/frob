---
id: T-3114
title: Add resync_root_to_published_tip primitive for the post-CAS root resync
state: done
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
- src/frob/tickets/_land_compose.py
- tests/unit/test_land_compose.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_compose.py
  reason: the two required fixtures for resync_root_to_published_tip live in this
    file; SCOPE001 requires the ticket to declare it
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_land_compose.py
  reason: the two required fixtures for resync_root_to_published_tip live in this
    file; SCOPE001 requires the ticket to declare it
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_land_compose.py
  reason: the two required fixtures for resync_root_to_published_tip live in this
    file; SCOPE001 requires the ticket to declare it
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_land_compose.py
  reason: the two required fixtures for resync_root_to_published_tip live in this
    file; SCOPE001 requires the ticket to declare it
  actor: logan
  at: '2026-08-27'
evidence:
- tests/unit/test_land_compose.py::TestResyncRootToPublishedTip::test_unrelated_dirty_path_resyncs_and_is_preserved
- tests/unit/test_land_compose.py::TestResyncRootToPublishedTip::test_dirty_path_the_land_also_changed_blocks_atomically
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 926e97e8bff1fed502a3596b5a5ae7045eb45976
---
DECOMPOSITION CHILD of T-3089 (series BQ). T-3089's body carries the settled
answer to its own blocking design question; this ticket builds the primitive
that answer names, so that T-3089 is left as pure wiring.

WHAT. Add `resync_root_to_published_tip(root, old_tip, new_tip)` to
src/frob/tickets/_land_compose.py, alongside `publish_ref_cas`,
`compose_squash_in_disposable_worktree` and `fold_worktree_into_commit`.

Mechanism (verified on this machine's git 2.34.1, do not substitute):
`git -C <root> read-tree -m -u <old_tip> <new_tip>` -- a two-tree
twoway_merge. It touches NO ref (root's HEAD is a symref to refs/heads/main
and has therefore ALREADY moved as a side effect of the CAS publish; only
the index and working tree are stale). `reset --keep` would redundantly
re-point the ref it just published; `reset --hard` is forbidden outright by
T-1740, already encoded in `_commit_squash_apply`'s fallback, because it
destroys a sibling agent's uncommitted work in root.

RETURN TYPE. `Result[None, LandComposeError]` with a DISTINCT member for the
refusal (parity with `publish_ref_cas`'s distinct `RefMoved`) -- the caller
must be able to tell "root is dirty and a sibling blocked the resync" apart
from a generic git failure, because the two get different operator advice.

FAILURE SEMANTICS the caller must honor (spelled out in T-3089's body):
post-publish, so it CANNOT unwind. The commit is already public and already
correct; a resync failure is NOT a land failure. Report loudly -- ERROR log
naming ticket, published sha, and the exact one-line operator recovery
command -- and never revert. Exactly one attempt, no retry loop: a retry
races the same sibling that caused the refusal.

FIXTURES (both required, per house rule):
- must-fire: sibling holds an uncommitted edit to a path the land ALSO
  changed -> Err(the distinct refusal member), and the sibling's file content
  is asserted byte-for-byte intact (the refusal is atomic; git 2.34.1 emits
  `error: Entry '<p>' not uptodate. Cannot merge.` and exits 128 without
  applying anything).
- must-stay-quiet: sibling holds an uncommitted edit to an UNRELATED path ->
  Ok(None), the landed changeset IS applied to root's worktree, and the
  sibling's uncommitted edit is asserted still present and still unstaged.

NOT IN SCOPE. No call site. Wiring into the six index-consuming stages of
`_land_squash_apply_finish` stays in T-3089.