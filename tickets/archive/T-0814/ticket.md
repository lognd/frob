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
scope:
- src/frob/gates/__init__.py
- src/frob/dup/_pipeline.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_is_symref_gates
- tests/test_gates.py::TestCoverageGate::test_cov006_third_file_reachable_skips_unresolved_callee_sentinel
- tests/test_gates.py::TestDupPipelineClosureConsumers::test_is_symref_dup
- tests/test_gates.py::TestDupPipelineClosureConsumers::test_callee_name_map_skips_unresolved_callee_sentinel
designated_repro_test: null
acceptance:
- text: GIVEN a call-graph closure containing a sentinel or non path::qualname entry
    WHEN _cov006_third_file_reachable and sibling closure consumers process it THEN
    they skip or handle it without raising; a regression test feeds a sentinel entry
    through each consumer
  evidence:
  - tests/test_gates.py::TestCoverageGate::test_is_symref_gates
  - tests/test_gates.py::TestCoverageGate::test_cov006_third_file_reachable_skips_unresolved_callee_sentinel
  - tests/test_gates.py::TestDupPipelineClosureConsumers::test_is_symref_dup
  - tests/test_gates.py::TestDupPipelineClosureConsumers::test_callee_name_map_skips_unresolved_callee_sentinel
threat: null
component: null
---
T-0809 reviewer condition (b): _cov006_third_file_reachable (gates/__init__.py ~3361) does split('::',1)[1] on every closure entry and IndexErrors on any non-symref (discovered when mark_unresolved=True injected UNRESOLVED_CALLEE); same shape assumption at 3 gates call sites + dup/_pipeline. Any future graph extension crashes them. Harden all closure consumers.