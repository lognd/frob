---
id: T-1095
title: 'daemon: cross-worktree single-flight coverage/collection keyed by source digest'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
blocked_by:
- T-1092
parent: T-0321
tier: story
sprint: null
scope:
- src/frob/testing/**
- src/frob/serve/**
- docs/modules/testing.md
- docs/modules/serve.md
- tickets.md
- tests/test_coverage_wait_shared.py
- tests/test_app.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_app.py
  reason: run_coverage_wait now also calls git_common_dir (a subprocess spawn) on
    every invocation for the T-1095 shared-state-dir resolution; two pre-existing
    tests here monkeypatch subprocess.run with a strict (cmd,cwd,check) signature
    that only anticipated the coverage command itself, so they now TypeError on the
    new git rev-parse spawn -- widen the fakes to pass through non-matching commands
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_coverage_wait_shared.py::TestTreeDigest::test_identical_hashes_produce_identical_digest
- tests/test_coverage_wait_shared.py::TestTreeDigest::test_differing_hashes_produce_differing_digest
- tests/test_coverage_wait_shared.py::TestSharedStateDir::test_two_worktrees_of_same_clone_share_one_dir
- tests/test_coverage_wait_shared.py::TestSharedStateDir::test_no_git_falls_back_to_worktree_local
- tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight::test_identical_digest_worktrees_share_one_run
- tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight::test_differing_digest_worktrees_each_run_independently
designated_repro_test: null
acceptance:
- text: GIVEN two worktrees checked out to commits whose tracked source content hashes
    identically WHEN both concurrently request coverage via run_coverage_wait THEN
    only one real coverage subprocess runs across BOTH worktrees and the second gets
    the shared fresh-or-failed result instead of independently re-running the suite
  evidence:
  - tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight::test_identical_digest_worktrees_share_one_run
- text: GIVEN two worktrees whose source content differs WHEN both request coverage
    concurrently THEN each runs its own independent coverage pass (no cross-contamination
    of results across differing digests)
  evidence:
  - tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight::test_differing_digest_worktrees_each_run_independently
threat: null
component: null
---
Child (b) of T-0321. T-0322 shipped run_coverage_wait with a PER-WORKTREE single-flight lock (.frob/coverage.lock, a path inside that worktree's own .frob/ -- confirmed 2026-07-28 via src/frob/testing/_coverage_wait.py) and a staleness check against that worktree's own coverage stamp. It does not share across worktrees: N agents on N git worktrees of the same commit (the common parallel-dispatch shape, per docs/guides/agent-playbook.md) each still pay their own full coverage run because each has its own .frob/coverage.lock and .frob/ cache. Move the single-flight lock and the content-addressed result cache to a location keyed by TREE DIGEST (source content hash, not worktree path) rather than worktree-local path -- e.g. a shared cache under the daemon's project-root-independent state dir (or the T-1092 daemon arbitrating across worktrees it can see via .claude/worktrees enumeration, matching T-0733's existing lease-enumeration pattern). A worktree with identical source content to one that already has a fresh coverage result gets that result immediately with zero subprocess spawned.