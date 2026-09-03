---
id: T-3607
title: 'cache rebuild unlinks live WAL sidecars: sibling reader SIGBUS in load_parsed_artifact'
state: done
kind: bug
origin: human
created: '2026-08-31'
priority: critical
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
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: T-3607's fix adds a new subprocess.Popen (exec) and os.utime/write_bytes
    (fs.write) capability site to tests/unit/test_graph_cache.py's positive-control
    test, needing this file's testsuite node capability grants updated (SELFAUDIT001)
  actor: logan
  at: '2026-08-31'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SELFAUDIT001/SYS111 ratchet ceiling bump for the two new testsuite capability
    sites T-3607's positive-control test adds
  actor: logan
  at: '2026-08-31'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SELFAUDIT001/SYS111 ratchet ceiling bump for the two new testsuite capability
    sites T-3607's positive-control test adds
  actor: logan
  at: '2026-08-31'
evidence:
- tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_sibling_reader_survives_concurrent_recreate
- tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_quarantined_sidecars_are_renamed_not_unlinked
- tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_sweep_removes_only_old_quarantined_sidecars
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33451274911 ubuntu: xdist worker died with "Fatal Python error: Bus
error" (SIGBUS) at 52% suite progress. Current thread:

  src/frob/graph/cache.py:858 load_parsed_artifact  (sqlite SELECT)
  src/frob/lang/__init__.py:946 _load_cached_artifact_payload
  src/frob/lang/__init__.py:891 _parse_file_with_artifact_cache
  src/frob/check/_memo.py:192 _wrapper
  src/frob/lang/__init__.py:1080 parse_file
  src/frob/gates/_todo_fmt.py:224 _todo001_bare -> coverage_gate

Mechanism (verified in source, 2026-08-31): cache.connect's rebuild path
(cache.py:410-412) does `path.unlink()` on the db AND its -wal AND -shm
sidecars. SQLite WAL mode ALWAYS memory-maps the -shm wal-index in every
connection. A process that decides the db is unreadable (line 315
"unreadable db ... rebuilding" -- seen firing in CI logs this week) or
schema-stale (line 340) unlinks/recreates those files while a SIBLING
xdist worker holds the old -shm mapped; the reader's next wal-index
access hits a truncated/replaced mapping => SIGBUS, killing the whole
worker process (not an exception -- a fatal signal).

Fix direction (implementer verifies):
1. Never unlink a live WAL db in place. Rebuild to a temp path and
   atomically rename over the db ONLY under an exclusive flock that
   readers also take in shared mode when (re)opening -- or better,
   quarantine-rename the bad db aside (rename is safe for the OLD
   mapping; unlink+recreate of -shm is what kills) and let each process
   reopen lazily.
2. Consider `PRAGMA locking_mode`/journal options or a rebuild
   generation-counter file so siblings detect and reopen instead of
   crashing.
3. A unit test that provokes the race deterministically (two processes,
   one rebuilds while the other reads in a loop) belongs with the fix;
   without a positive control the fix proves nothing (fleet doctrine).

Severity: this randomly kills any POSIX CI run (this run: took the
ubuntu leg down; xdist then deadlocked -- see the companion ticket).