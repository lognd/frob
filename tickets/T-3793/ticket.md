---
id: T-3793
title: 'conftest: env-gated failure-longrepr dump to surface win32 CI tracebacks (doctor
  diagnosis)'
state: done
kind: feature
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
- .github/workflows/ci.yml
- tests/unit/test_conftest_suite_result_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: bind evidence for T-3793 conftest FROB_TEST_DUMP_FAILURE_REPR tests
  actor: logan
  at: '2026-09-04'
  old_length: 297
  new_length: 562
evidence:
- tests/unit/test_conftest_suite_result_status.py::TestSuiteResultFailureReprDump::test_repr_dump_absent_when_env_var_unset
- tests/unit/test_conftest_suite_result_status.py::TestSuiteResultFailureReprDump::test_repr_dump_present_when_env_var_set
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
PROBLEM: win32 CI leg emits SUITE-RESULT-FAILED names but no tracebacks because FROB_TEST_HARD_EXIT=1 os._exit()s before pytest's FAILURES section flushes. Fix: env-gated (FROB_TEST_DUMP_FAILURE_REPR) longrepr dump in the SUITE-RESULT reporter, on before hard-exit. Set only in win32 CI Test step.

frob:tests tests/unit/test_conftest_suite_result_status.py::TestSuiteResultFailureReprDump.test_repr_dump_absent_when_env_var_unset
frob:tests tests/unit/test_conftest_suite_result_status.py::TestSuiteResultFailureReprDump.test_repr_dump_present_when_env_var_set