---
id: T-0394
title: 'advisories: deep-nesting refactor (2 findings)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
- tests/unit/test_arch.py::TestLockOrderingHazards::test_unresolvable_lock_identity_is_advisory
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_same_write_under_with_lock_does_not_fire
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_write_reachable_via_callee_of_dispatched_function_fires
- tests/unit/test_arch.py::TestPythonAdapter::test_adapt_arch_python_fixture_shape
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_imports
- tests/test_gates.py::TestCoverageGate::test_cov006_still_fires_when_no_public_wrapper_reaches_the_target
- tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_test_reaches_via_two_hop_wrapper_chain
- tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_wrapper_called_via_import_alias
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_process_env_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_process_env_subscript_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_struct_ssn_field_fires
- tests/unit/perf/test_effect_summaries.py::TestEffectGraphSummaryUnknownDegradation::test_fully_resolvable_call_path_has_no_unknown_member
- tests/unit/test_cycle.py::test_long_chain_no_recursion_error
- tests/unit/test_arch.py::TestCollectDispatchRefs::test_call_callee_identifier_counted
- tests/unit/test_arch.py::TestCollectDispatchRefs::test_call_positional_argument_identifier_counted
- tests/unit/test_arch.py::TestCollectDispatchRefs::test_call_keyword_argument_identifier_counted
- tests/unit/test_arch.py::TestCollectDispatchRefs::test_call_keyword_argument_non_identifier_not_counted
- tests/unit/test_arch.py::TestCollectDispatchRefs::test_call_string_argument_not_counted
- tests/unit/test_arch.py::TestPythonAdapter::test_adapt_imports
designated_repro_test: null
threat: null
component: null
---
Address the 2 frob-arch deep-nesting advisories: refactor to reduce nesting depth, or add an explicit reason-note if the nesting is justified. Acceptance: both findings resolved (fixed or reason-noted).