---
id: T-3700
title: 'cache: close sibling connect/read raw-error escape round 7'
state: in-progress
kind: bug
origin: human
created: '2026-09-02'
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
- tests/unit/test_graph_build_lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/graph/cache.py tests/unit/test_graph_cache.py tests/unit/test_graph_build_lock.py
  reason: split space-joined single glob into three separate scope globs (was recorded
    as one element by ticket new --scope)
  actor: logan
  at: '2026-09-02'
- op: add
  glob: src/frob/graph/cache.py
  reason: split space-joined single glob into three separate scope globs (was recorded
    as one element by ticket new --scope)
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/unit/test_graph_cache.py
  reason: split space-joined single glob into three separate scope globs (was recorded
    as one element by ticket new --scope)
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/unit/test_graph_build_lock.py
  reason: split space-joined single glob into three separate scope globs (was recorded
    as one element by ticket new --scope)
  actor: logan
  at: '2026-09-02'
body_changes:
- mode: append
  reason: 'waive BUG002: nondeterministic load-dependent race, cannot deterministically
    fail at main'
  actor: logan
  at: '2026-09-02'
  old_length: 822
  new_length: 1487
evidence:
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Round 7 of the cache two-process saga (after T-3607, T-3623, T-3632, T-3634, T-3644, T-3654, T-3669). Run 33633092156 ubuntu: test_two_processes_connecting_concurrently_never_see_no_such_table_meta still surfaces disk I/O error and no such table meta from the sibling connect+read loop under heavy CI load. Two escape windows: (1) _check_fingerprint_with_recovery second _check_fingerprint is unguarded one-shot, and _with_lock_retry does not catch stale/corrupt shapes, so a replace racing it escapes connect(); (2) the meta read right after connect (get_root/get_file_meta/_get_file_hash) is raw conn.execute not routed through _run_with_stale_reconnect. Fix: bounded reopen+retry loop in fingerprint recovery; route post-connect meta reads through the stale-reconnect helper; strengthen the two-process regression test.

frob:waive BUG002 reason="The defect is a nondeterministic raw-error escape (disk I/O error / no such table: meta) that manifests only under heavy PARALLEL CI load (run 33633092156, ubuntu); it is a timing window between a sibling's os.replace and a connect/meta-read, not a deterministic failure. The regression test strengthens the two-process race and asserts zero raw-error escapes, but at main a single non-loaded run passes (the window rarely opens), so no test can be bound that deterministically FAILS at the parent commit. CI is the true verifier for the race. Same spirit as prior rounds T-3634/T-3669, whose race regressions were also load-dependent."