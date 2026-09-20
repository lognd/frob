---
id: T-3755
title: 'win32 drain needs the full failing-node-id list: make SUITE-RESULT-FAILED
  cap env-overridable'
state: done
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- tests/unit/test_conftest_stackdump.py
- .github/workflows/ci.yml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/conftest.py
  reason: make the SUITE-RESULT-FAILED node-id cap env-overridable (FROB_TEST_SUITE_RESULT_MAX_NODE_IDS)
    and set it high in the CI Test steps so win32 emits the full failing list for
    the drain
  actor: logan
  at: '2026-09-04'
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: make the SUITE-RESULT-FAILED node-id cap env-overridable (FROB_TEST_SUITE_RESULT_MAX_NODE_IDS)
    and set it high in the CI Test steps so win32 emits the full failing list for
    the drain
  actor: logan
  at: '2026-09-04'
- op: add
  glob: .github/workflows/ci.yml
  reason: make the SUITE-RESULT-FAILED node-id cap env-overridable (FROB_TEST_SUITE_RESULT_MAX_NODE_IDS)
    and set it high in the CI Test steps so win32 emits the full failing list for
    the drain
  actor: logan
  at: '2026-09-04'
evidence:
- tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_node_id_cap_env_override
- tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_caps_failing_node_ids_with_and_n_more
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
