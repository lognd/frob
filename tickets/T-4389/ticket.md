---
id: T-4389
title: 'macOS-only flake: sibling connect race surfaces raw sqlite error in schema-incomplete-db
  test'
state: queued
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/cache.py
- tests/unit/test_graph_cache.py
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
CI run 34415921529, macOS leg only: tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta failed with: sibling connect()+get_root() loop surfaced a raw sqlite error: cache.connect: fingerprint None -> 'frob==0.530.1.dev1|strata-...' (message truncated in the CI capture available to me). This test exercises the same _run_with_stale_reconnect/_recover_fingerprint_connection concurrent-recreate-vs-connect race documented at T-3623/T-3700 in the test's own docstring, but the CI failure text names a fingerprint-mismatch code path (cache.connect: fingerprint None -> ...), not the no-such-table/disk-I/O-error shapes those tickets hardened against -- so this may be a NEW race window on macOS's slower fsync/replace timing rather than a regression of the existing hardening. Checked T-4159 (in-progress at time of filing, scope src/frob/graph/cache.py, worktree .claude/worktrees/t-4159): its diff adds genuine-corruption self-heal (_is_genuine_corruption_shape/_rebuild_because_corrupt) gated on 'database disk image is malformed'/'database is corrupted' shapes only -- it does not touch fingerprint-mismatch handling in _recover_fingerprint_connection's ordinary path, so it is unlikely to be the cause or the fix. Could not reproduce: 1 straight run + 5 sequential stress runs of the exact nodeid all passed on Linux (uv run pytest <nodeid> -x -q, and again with -p no:xdist), consistent with this being a macOS-timing-specific window (slower directory/inode publish after os.replace per the test's own comment on why it needs the double-replace-per-iteration workload to reproduce even on Linux CI). Needs macOS reproduction or a code-level audit of _recover_fingerprint_connection's ordering against a concurrent _recreate for a window where a fresh connection observes the OLD path's fingerprint before the new schema/rows are visible.