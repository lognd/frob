---
id: T-2837
title: 'SYS100: testsuite node missing env.read via-grant for tests/unit/test_check.py
  (T-2806 regression)'
state: queued
kind: bug
origin: human
created: '2026-08-21'
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
Found while working T-2729 (LARGE001 split of _selfconform.py). tests/unit/strata/test_selfconform.py::TestRealGateGreen/TestCoverageTotality fail a full-repo self-conformance scan with an unwaived SYS100 finding: capability env.read observed at tests/unit/test_check.py:763 but not declared for node testsuite. T-2806 (land f51368e29, Stamp the parse-artifact cache env before build_graph) added an os.environ.get(PARSE_ARTIFACT_CACHE_ENV) read to tests/unit/test_check.py without adding that file to design/frob.strata testsuite env.read via-list (line ~1414). Confirmed unrelated to T-2729 own file split: reproduces on main after merging main into the T-2729 worktree, before any T-2729 code change touches this path. Fix: add tests/unit/test_check.py to the testsuite node env.read may-via list.