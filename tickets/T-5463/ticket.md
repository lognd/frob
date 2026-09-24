---
id: T-5463
title: 'SYS119 templated-assume drift: design/frob.strata gained a 7th near-duplicate
  cluster'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19). ubuntu and macos
both fail two related node ids on the same root cause:
- tests/gates_suite/test_sys_assume_template.py::TestSelfaudit001TemplatedAssume::test_red_on_todays_design_frob_strata
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations

Both fail on the exact same 7 SELFAUDIT001/SYS119 templated-assume
violations. design/frob.strata has gained a 7th near-duplicate-assume
cluster (weakness:CWE-79 across core, graphlang, testsuite) since the
SYS119 acceptance test was written expecting exactly 6 SF-08
weakness-code clusters (CWE-78, CWE-94, CWE-89, CWE-502, CWE-639,
CWE-918).

Diagnosis: this is the exact copy-paste-assume pattern SELFAUDIT001 exists
to catch, not a false positive -- fix by writing a module-owned CWE-79
assume per node (core, graphlang, testsuite) in design/frob.strata instead
of the templated/copied one, which should make the violation count return
to 6 and both tests pass with no test-side change. If de-templating is not
possible for a real reason, the fallback is updating both tests'
acceptance counts (6 -> 7) together, since they assert the same fact.
