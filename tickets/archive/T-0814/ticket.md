---
id: T-0814
title: 'gates: closure() consumers IndexError on non-symref graph entries (latent
  crash class in _cov006 + siblings)'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/dup/_pipeline.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: moving DOCARCH001 change-narrative out of the test docstring per T-4420
  actor: logan
  at: '2026-09-19'
  old_length: 363
  new_length: 958
- mode: append
  reason: moving DOCARCH001 change-narrative out of the test docstring per T-4420
  actor: logan
  at: '2026-09-19'
  old_length: 958
  new_length: 1804
evidence:
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_is_symref_gates
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov006_third_file_reachable_skips_unresolved_callee_sentinel
- tests/gates_suite/test_waive.py::TestDupPipelineClosureConsumers::test_is_symref_dup
- tests/gates_suite/test_waive.py::TestDupPipelineClosureConsumers::test_callee_name_map_skips_unresolved_callee_sentinel
designated_repro_test: null
acceptance:
- text: GIVEN a call-graph closure containing a sentinel or non path::qualname entry
    WHEN _cov006_third_file_reachable and sibling closure consumers process it THEN
    they skip or handle it without raising; a regression test feeds a sentinel entry
    through each consumer
  evidence:
  - tests/gates_suite/test_coverage.py::TestCoverageGate::test_is_symref_gates
  - tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov006_third_file_reachable_skips_unresolved_callee_sentinel
  - tests/gates_suite/test_waive.py::TestDupPipelineClosureConsumers::test_is_symref_dup
  - tests/gates_suite/test_waive.py::TestDupPipelineClosureConsumers::test_callee_name_map_skips_unresolved_callee_sentinel
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-0809 reviewer condition (b): _cov006_third_file_reachable (gates/__init__.py ~3361) does split('::',1)[1] on every closure entry and IndexErrors on any non-symref (discovered when mark_unresolved=True injected UNRESOLVED_CALLEE); same shape assumption at 3 gates call sites + dup/_pipeline. Any future graph extension crashes them. Harden all closure consumers.

DOCARCH001 cleanup note (T-4420): tests/gates_suite/test_coverage.py::TestCoverageGate.test_cov006_third_file_reachable_skips_unresolved_callee_sentinel's docstring used to say: 'T-0814 (T-0809 reviewer condition b): _cov006_third_file_reachable iterates closure(...)'s output and used to do helper_symref.split("::", 1)[1] unconditionally -- a bare UNRESOLVED_CALLEE sentinel entry (no ::) IndexErrors that. Forcing closure to always return the sentinel proves the function now skips it and returns cleanly instead of raising.' Moved here; the test docstring now states only what it verifies.

DOCARCH001 cleanup note (T-4420): tests/gates_suite/test_waive.py::TestDupPipelineClosureConsumers.test_callee_name_map_skips_unresolved_callee_sentinel's docstring used to say: 'T-0814: _callee_name_map iterates graph.calls.get(caller, ()) and used to do callee_symref.split("::", 1)[1] unconditionally -- a bare UNRESOLVED_CALLEE sentinel entry (no ::) IndexErrors that. A CallGraph carrying the sentinel alongside a real callee must not raise, and the real callee must still resolve -- the sentinel is skipped, not silently swallowing real entries too.' Moved here; the test docstring now states only what it verifies. (Note: this is a second, distinct test citing T-0814 alongside tests/gates_suite/test_coverage.py::TestCoverageGate.test_cov006_third_file_reachable_skips_unresolved_callee_sentinel, also cleaned in this same T-4420 pass.)