---
id: T-3429
title: Declare testsuite exec/fs.write/env.read capabilities for tests/system/test_coverage_sigterm.py
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
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
found while working T-3420: the new tests/system/test_coverage_sigterm.py fixture (subprocess spawn, tmp_path writes, os.environ reads for the T-3420 SIGTERM-deadlock repro) trips gate:SELFAUDIT001 (exec/fs.write/env.read observed but not declared on the testsuite node) because it is not listed in design/frob.strata's testsuite node 'may exec/fs.write/env.read via ...' lists. Could not fix directly: design/frob.strata is under a LIVE cross-worktree scope lease held by T-3416 (a different, pre-existing SELFAUDIT001 gap) at the time T-3420 landed. Add tests/system/test_coverage_sigterm.py to the three via-lists (may "exec", may "fs.write", may "env.read") on the testsuite node once T-3416 releases the lease.