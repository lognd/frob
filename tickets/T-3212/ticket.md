---
id: T-3212
title: 'macOS CI: triage SYS107/SYS003 selfconform finding and resolved-root/load_lock
  path clusters (T-2942 remainder)'
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_evidence_enforcement.py
- tests/system/test_cli_ticket.py
- tests/system/test_cli_ticket_promote.py
- src/frob/graph/lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/unit/strata/test_selfconform.py
  reason: T-2676 already tracks the SYS107 self-conform severity-blindness cluster;
    this ticket covers the remaining resolved-root/load_lock clusters only
  actor: logan
  at: '2026-08-28'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split out of T-2942: after fixing the two clusters reachable/reproducible from T-2942's declared scope (FIFO body-file test's hardcoded /proc/self/fd path, test_serial_pools.py's 0.05 timing threshold), three clusters from the original 156-failure macOS run (32920399634, job 98032723003) remain untriaged because they are not reproducible from a Linux host and were not in T-2942's own scope:

1. (4 failures) SYS107/SYS003 findings on _land.py:440 and testsuite binding 615 files -- lives in tests/unit/strata/test_selfconform.py, not test_sys003_calibration.py (verified: the latter is a synthetic in-memory-model test with no macOS-specific path, passes clean on Linux, 7/7). Needs a real macOS run or careful reasoning about whether the 615-file testsuite binding count differs by platform (case-sensitive filesystem glob differences are a plausible cause).

2. (6 failures) 'resolved root /private/var/folders/...' assertions in test_cli_evidence_enforcement.py, test_cli_ticket.py, test_cli_ticket_promote.py -- test_cli_ticket_land.py (which WAS in T-2942's scope) was checked and contains no such assertion, so this cluster's actual location is the other three files, none of which were in scope.

3. (2 failures) 'load_lock: no lock file at /private/var/folders/...' -- plausibly a macOS /var -> /private/var symlink mismatch between where frob.graph.lock's frob.lock is written vs looked up; check every load_lock/write_lock call site resolves consistently (.resolve() on both sides or neither).

Verify each against the FRESH CI evidence (run 33135896391) before assuming the old run's line numbers/counts still apply.