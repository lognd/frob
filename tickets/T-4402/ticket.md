---
id: T-4402
title: 'graph cache rebuild fails on Windows: os.replace onto open sqlite handle'
state: queued
kind: bug
origin: human
created: '2026-09-10'
priority: medium
parent: T-3505
tier: ticket
sprint: v0.531.0
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
triage_changes:
- field: parent
  old_value: null
  new_value: T-3505
  reason: windows drain epic T-3505 covers this leaf
  actor: logan
  at: '2026-09-11'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34546329688, Windows leg only.

Node id: tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals::test_run_with_stale_reconnect_rebuilds_and_completes_on_corruption

Traceback tail (verbatim):
src\frob\graph\cache.py:308: in _replace_with_retry
    os.replace(tmp_path, path)
E   PermissionError: [WinError 5] Access is denied: ...cache.db.new-8524-d406455b -> ...cache.db

Landed today by T-4159; a Windows regression from that land. On win32,
os.replace(tmp, dst) fails with WinError 5/32 when dst still has an open
file handle (the corrupt sqlite connection this same code path is trying
to replace out from under). POSIX allows renaming over an open file;
Windows does not. _replace_with_retry already retries, but apparently not
long/often enough, or does not close the stale connection first on this
platform. Fix: ensure the corrupt connection is explicitly closed before
_recreate/_replace_with_retry runs (sys.platform-gated if the close must
be win32-only to avoid changing POSIX-path robustness), or extend the
existing retry loop specifically for win32 sharing-violation errno with a
declared reason.