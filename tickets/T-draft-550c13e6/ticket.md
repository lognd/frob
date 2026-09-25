---
id: T-draft-550c13e6
title: 'Windows self-gate: cache.db lock-wait gives up with ''holder detection unsupported
  on this platform'''
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
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
Found while draining CI run 36086669322 (dev 2d0da515df), windows-latest
job only. self-gate's "frob check (self-gate)" step failed with:

  ERROR: cache: store_file_data(src/frob/perf/_hotpath_smells.py) still
  locked after 30s, giving up (no process found still holding
  D:\a\frob\frob\.frob\cache.db open (it may have released the lock
  already, or holder detection is unsupported on this platform))
  ERROR: build_graph: cache lock never released: database is locked --
  no process found still holding D:\a\frob\frob\.frob\cache.db open (it
  may have released the lock already, or holder detection is
  unsupported on this platform)

This run's self-gate could not produce a clean error/finding count at
all (an infra failure, not a measured gate result) -- unlike run
35951365410's windows self-gate (2514 errors, caused by the `import
fcntl` collection crash T-5482 already fixed and landed), this run's
self-gate result should be read as UNMEASURED, not compared numerically
against that count.

The error message's own parenthetical ("holder detection is unsupported
on this platform") suggests this cache-lock code path already knows its
own Windows detection is incomplete -- worth checking
frob.graph.cache/whatever owns store_file_data's lock-wait logic for a
Windows-specific holder-liveness gap (same class of issue T-5482's
fcntl fix and the earlier windows-is-verifiable-locally memory note's
own "os.kill sends CTRL_C on win32" caution already flagged elsewhere in
this codebase).
