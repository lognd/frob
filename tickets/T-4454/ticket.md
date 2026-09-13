---
id: T-4454
title: 'Regression: _recreate leaves cache.db absent, read-only sibling dies with
  ''unable to open database file'' (macOS T-3607 test)'
state: done
kind: bug
origin: agent
created: '2026-09-12'
priority: critical
parent: T-4410
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
evidence:
- tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_path_never_absent_during_recreate
- tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_quarantined_sidecars_are_renamed_not_unlinked
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_sibling_reader_survives_concurrent_recreate
  new_node: ''
  reason: already PASSES at parent (T-3607's own race is not reliably reproducible
    on this Linux runner), so it is confirmatory-only for --check-repro/BUG002; the
    deterministic test_path_never_absent_during_recreate is the repro-proof evidence
    instead, still cited via frob:tests in code for the 20/20 acceptance criterion
  actor: logan
  at: '2026-09-13'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REGRESSION introduced today (macOS leg of CI run 34734529382, head 32ec4afda, which includes T-4412 de9636271 and T-4411 69b2d6ad4, both in src/frob/graph/cache.py; the previous head 59c43cb12 passed this test). tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_sibling_reader_survives_concurrent_recreate: the sibling reader process died with returncode=1. Its traceback (captured stderr): `conn = graph_cache.connect_readonly(path)` -> cache.py:2358 `_with_lock_retry(lambda: sqlite3.connect(uri, uri=True, timeout=30.0), ...)` -> cache.py:802 `return op()` -> `sqlite3.OperationalError: unable to open database file`. So while this process runs `_recreate(_open(path), path)` in a loop (rename the old db/-wal/-shm aside as a quarantined sidecar, then create a fresh db at path), the reader's read-only URI connect lands in the window where NO file exists at path; "unable to open database file" is not in `_with_lock_retry`'s transient set, so it re-raises immediately and the reader exits 1. T-3607 is exactly the race this test guards. Either (a) T-4412's `_read_schema_version`/connect change now re-raises what used to be swallowed-and-retried, or (b) T-4411's `_replace_with_retry`/seeding changed `_recreate`'s ordering so the path is briefly absent; bisect by running the test in a tight loop (raise the reader duration argument from 2.0 to 10.0 locally and loop 20x) at 59c43cb12, de9636271 and 69b2d6ad4 -- on Linux the window may be too small to hit, so ALSO reason from the code: read `_recreate` and `connect_readonly` at each commit. FIX (both halves): (1) `_recreate` must never leave the path absent: build the fresh db at a temp name and `os.replace` it over the old path (the quarantined copy is made from the old inode before the swap, e.g. hard-link or rename-then-replace ordering that keeps a file at path at every instant); (2) `connect_readonly`/`_with_lock_retry` treats `unable to open database file` as transient for the same bounded budget when the caller is a read-only sibling, and names the path and holder on exhaustion. ACCEPTANCE: (a) the test passes 20/20 in a local loop with the reader duration raised to 10s; (b) a new unit test asserts a file exists at path at every observable point of `_recreate` (patch os.replace/rename to record the sequence); (c) macOS leg green on this node id on the next push. Sprint v0.531.0 (CI green blocker). Related: T-3607, T-4159, T-4411, T-4412.