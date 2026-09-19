---
id: T-4582
title: csharp test_discovery capability has no behavioral fixture builder (registered
  IMPLEMENTED without one)
state: done
kind: bug
origin: human
created: '2026-09-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_lang_conformance.py
- tests/test_lang_conformance_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_lang_conformance.py
  reason: add csharp test_discovery fixture builder
  actor: logan
  at: '2026-09-18'
- op: add
  glob: tests/test_lang_conformance_gate.py
  reason: evidence test
  actor: logan
  at: '2026-09-18'
evidence:
- tests/test_lang_conformance_gate.py::TestCSharpCapabilityConformance::test_csharp_registered_capabilities_pass
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_csharp_test_discovery_is_behaviorally_checked
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_csharp_test_discovery_passes_on_a_real_discoverable_fixture
designated_repro_test: null
acceptance:
- text: 'bound([''tests/test_lang_conformance_gate.py::TestCSharpCapabilityConformance::test_csharp_registered_capabilities_pass'',
    ''tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_csharp_test_discovery_is_behaviorally_checked'',
    ''tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_csharp_test_discovery_passes_on_a_real_discoverable_fixture'']):
    csharp/test_discovery has a real behavioral fixture builder (_check_test_discovery_csharp)
    registered in _TEST_DISCOVERY_BUILDERS and _BEHAVIORAL_CAPABILITY_LANGUAGES, and
    test_csharp_registered_capabilities_pass passes against the live registry'
  evidence:
  - tests/test_lang_conformance_gate.py::TestCSharpCapabilityConformance::test_csharp_registered_capabilities_pass
  - tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_csharp_test_discovery_is_behaviorally_checked
  - tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_csharp_test_discovery_passes_on_a_real_discoverable_fixture
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
