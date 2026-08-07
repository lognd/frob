---
id: T-0870
title: stash-guard hook aborts git gc pack-refs in multi-worktree clones (over-broad
  refs/stash refusal)
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/scaffold/**
- tests/unit/test_scaffold_stash_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_scaffold_stash_guard.py::TestStashGuardPackRefs::test_pack_refs_succeeds_with_existing_stash_and_multiple_worktrees
- tests/unit/test_scaffold_stash_guard.py::TestStashGuardPackRefs::test_stash_still_refused_with_multiple_worktrees
designated_repro_test: null
acceptance:
- text: GIVEN a clone with >1 worktree, a pre-existing refs/stash, and the stash-guard
    hook installed WHEN git gc (pack-refs) runs THEN it succeeds
  evidence:
  - tests/unit/test_scaffold_stash_guard.py::TestStashGuardPackRefs::test_pack_refs_succeeds_with_existing_stash_and_multiple_worktrees
- text: GIVEN the same clone WHEN git stash runs THEN the hook still refuses with
    the playbook pointer
  evidence:
  - tests/unit/test_scaffold_stash_guard.py::TestStashGuardPackRefs::test_stash_still_refused_with_multiple_worktrees
threat: null
component: scaffold
---
Observed 2026-07-23 during a normal coordinator commit on main with 14 worktrees registered: git's background auto-gc ran pack-refs, the scaffolded stash-guard reference-transaction hook saw a transaction touching refs/stash and refused it ("refusing 'git stash' -- 14 worktrees exist"), and gc failed ("fatal: failed to run pack-refs / error: task 'gc' failed"). The guard's intent (block `git stash` in multi-worktree clones, playbook 1b) is over-broad: pack-refs REWRITES existing refs (including an existing refs/stash) rather than creating a stash, and aborting it breaks repo maintenance for the whole clone every time gc triggers. Fix in frob.scaffold._managed's stash-guard block: distinguish a stash CREATION/UPDATE (new refs/stash value) from maintenance rewrites (pack-refs presents the same old/new value, or GIT_REF_TRANSACTION context indicates packing) and allow the latter; keep refusing genuine stash pushes. Add a fixture proving `git gc` succeeds under the guard with a pre-existing stash ref and >1 worktree while `git stash` itself still refuses.