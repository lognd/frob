---
id: T-4402
title: 'graph cache rebuild fails on Windows: os.replace onto open sqlite handle'
state: done
kind: bug
origin: human
created: '2026-09-10'
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
evidence:
- tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals::test_win32_rebuild_closes_the_callers_stale_connection_first
designated_repro_test: tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals::test_win32_rebuild_closes_the_callers_stale_connection_first
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

frob:waive BUG002 reason="check-repro's git-diff base-ref approach cannot
reconstruct a pre-fix-only commit for this test: it was added in the
same worktree branch as the fix, and no ancestor of this ticket's HEAD
contains the test without the fix (T-2025's own documented squash
limitation, docs/modules/tickets.md#check-repro-post-land-limitation-t-
2025). Designated repro was forced (--designate-repro-force). Real
verification was still done, out of band: via winrun (Windows mirror),
the exact test content, run against this ticket's pre-fix production
code (src/frob/graph/cache.py at commit 4e63a4b73 (T-4402 start transition, before any T-4402 change)), fails
with the real Windows PermissionError ([WinError 5] Access is denied)
this ticket's CI run 34546329688 hit; run against the fixed code, it
passes -- see the ticket's Done report for the exact commands."