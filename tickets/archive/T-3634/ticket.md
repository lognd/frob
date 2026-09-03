---
id: T-3634
title: 'Cache atomicity round 3: disk I/O error retry on stale WAL connection'
state: done
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
body_changes:
- mode: append
  reason: 'BUG002: nondeterministic CI-only race, cannot be made to fail at main deterministically'
  actor: logan
  at: '2026-09-01'
  old_length: 1553
  new_length: 2397
evidence:
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta
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

frob:waive BUG002 reason="this is a darwin-only, timing-dependent WAL/os.replace race (disk I/O error) that this repo's own CI history shows does not reliably reproduce locally -- both T-3623 and T-3632, this ticket's own direct predecessors, passed their bound evidence 5x locally and still hit a NEW failure mode on the next CI run; the acceptance criterion documented in the ticket body is explicitly CI-verified, not locally-reproduced. The bound test cannot fail at main because the race window it exercises is a probabilistic timing race, not a deterministic code path; a mutation-killing unit test would require injecting a fault at the exact os.replace/WAL-read boundary, which this repo has no harness for. Round 4 remains possible if CI recurs with yet another OperationalError shape not covered by _is_stale_or_corrupt_connection."