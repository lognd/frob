---
id: T-3634
title: 'Cache atomicity round 3: disk I/O error retry on stale WAL connection'
state: queued
kind: bug
origin: human
created: '2026-09-01'
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
Run 33480116817 macOS: the two-process regression test
(TestRecreateNeverExposesASchemaIncompleteDb::
test_two_processes_connecting_concurrently_never_see_no_such_table_meta)
failed again, with a new error class: sibling loop observed
ERRORS:OperationalError('disk I/O error') (plus two routed-through-
rebuild WARNINGs, the designed graceful path).

History: round 1 (T-3623) closed the meta window; round 2 (T-3632)
made rebuilds atomic via temp-build + os.replace plus double-checked
locking. Round 3: on darwin, os.replace-ing the db file out from
under a LIVE WAL connection makes that sibling's next query raise
sqlite3.OperationalError('disk I/O error') (WAL sidecars/file handle
no longer match the inode it has open). Ubuntu tolerated this run;
darwin semantics differ.

Fix direction: the sibling's connect()/query path must treat
'disk I/O error' (and 'database is corrupted'-class codes) as a
REBUILD-RETRY signal exactly like 'no such table: meta' -- close the
stale connection, reopen at the canonical path (which now holds the
winner's fresh complete db), and continue; bounded retries, loud
WARNING per retry, never surface the raw OperationalError to the
caller. Extend cache.connect's unreadable-db handler's error-string
matching; also audit load_parsed_artifact/store paths for the same
handling (any query can hit it, not just connect).

Acceptance: the existing two-process test 5x consecutive locally;
note in the Done report that CI (both POSIX legs) is the true
verifier -- prior rounds passed locally 5x and still failed on CI.