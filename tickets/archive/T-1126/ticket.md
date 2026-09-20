---
id: T-1126
title: 'daemon: wire run_coverage_wait through the daemon-owned coverage lease RPC
  (T-1097 follow-up)'
state: done
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_coverage_wait.py
- src/frob/app/_daemon_proxy.py
- tests/test_coverage_wait_shared.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _coverage_wait.py'
  actor: logan
  at: '2026-09-19'
  old_length: 325
  new_length: 1815
evidence:
- tests/test_coverage_wait_shared.py::TestWorktreeLock::test_uses_daemon_lease_when_daemon_up
- tests/test_coverage_wait_shared.py::TestWorktreeLock::test_falls_back_to_file_lock_when_no_daemon
designated_repro_test: null
acceptance:
- text: GIVEN a running daemon WHEN run_coverage_wait needs the coverage writer THEN
    it acquires via the frob_lease_acquire RPC (crash-released per T-1097) instead
    of its own file-lock layers, with the file-lock path kept only as the daemonless
    fallback
  evidence:
  - tests/test_coverage_wait_shared.py::TestWorktreeLock::test_uses_daemon_lease_when_daemon_up
  - tests/test_coverage_wait_shared.py::TestWorktreeLock::test_falls_back_to_file_lock_when_no_daemon
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-0321 epic close disclosed this cut: run_coverage_wait still uses its T-0322/T-1095 file-lock + shared-state layers directly; T-1097 shipped the daemon lease primitive (ResourceLeaseManager, frob_lease_acquire/release, connection-liveness release). Converge the two so coverage arbitration has ONE owner when a daemon is up.

T-4718 sweep (condensed from src/frob/testing/_coverage_wait.py:394-423,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

# T-1516: `command=None` (the default) auto-wires the refresh through the
# in-process native path -- see the T-1516 note above `_run_and_settle_
# shared` for what that means and why.
#
# T-1095: before falling through to the per-worktree lock/run below, this
# checks the CROSS-worktree layer first -- `tree_digest` computed from the
# same snapshot, a shared cache keyed by that digest under
# `shared_state_dir`. A cache hit (another worktree with byte-for-byte
# identical tracked source already settled this digest) adopts that
# result (`_adopt_shared_result`) and returns immediately, with ZERO
# subprocess spawned in THIS worktree -- acceptance [0]. A cache miss
# acquires the shared per-digest lock (serializing every worktree sharing
# this digest onto one real run, re-checking the cache once more after
# acquiring it in case a racing worktree just finished), runs the refresh
# exactly as before, and records the settled result for every other
# worktree sharing this digest to find. Two worktrees whose tracked source
# DIFFERS resolve to different digests -- different lock paths, different
# cache entries -- so they never contend or share a result with each
# other at all (acceptance [1]).
#
# T-1126: the OUTER lock is `_worktree_lock` (daemon lease when reachable,
# else `_coverage_lock`).