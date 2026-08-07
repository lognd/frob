---
id: T-0746
title: 'protocol verification gate: state-requirement + invalid-transition errors
  with recorded language-excuse discharges'
state: done
kind: security
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0745
parent: T-0739
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/arch/**
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestProtocolVerificationGate::test_state_never_established_is_an_error
- tests/test_gates.py::TestProtocolVerificationGate::test_state_established_by_a_reachable_transition_is_not_flagged
- tests/test_gates.py::TestProtocolVerificationGate::test_state_equal_to_initial_is_not_flagged
- tests/test_gates.py::TestProtocolVerificationGate::test_poisoned_summary_at_a_requires_symbol_is_an_error
- tests/test_gates.py::TestProtocolVerificationGate::test_invalid_transition_precondition_never_established_is_an_error
- tests/test_gates.py::TestProtocolVerificationGate::test_valid_transition_chain_is_not_flagged
- tests/test_gates.py::TestProtocolVerificationGate::test_python_with_block_discharges_the_requirement
- tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_drop_impl_discharges
- tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_mem_forget_revokes_the_drop_discharge
- tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_manually_drop_revokes_the_discharge
- tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_no_drop_impl_is_not_discharged
- tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_cpp_raii_destructor_discharges
- tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_cpp_no_destructor_is_not_discharged
- tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_python_with_block_discharges
- tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_python_no_with_block_is_not_discharged
- tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_typescript_using_discharges
- tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_typescript_try_finally_discharges
- tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_typescript_bare_call_is_not_discharged
- tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_gc_finalizer_never_discharges
designated_repro_test: null
acceptance:
- text: GIVEN a C fixture where net_requires-annotated functions are reachable without
    net_init WHEN the gate runs THEN an ERROR names the unestablished state and the
    call path; GIVEN the same shape in Rust with a Drop impl THEN a recorded Drop
    discharge, and with mem::forget observed THEN the excuse is revoked and the ERROR
    returns
  evidence:
  - tests/test_gates.py::TestProtocolVerificationGate::test_state_never_established_is_an_error
  - tests/test_gates.py::TestProtocolVerificationGate::test_state_established_by_a_reachable_transition_is_not_flagged
  - tests/test_gates.py::TestProtocolVerificationGate::test_state_equal_to_initial_is_not_flagged
  - tests/test_gates.py::TestProtocolVerificationGate::test_poisoned_summary_at_a_requires_symbol_is_an_error
  - tests/test_gates.py::TestProtocolVerificationGate::test_invalid_transition_precondition_never_established_is_an_error
  - tests/test_gates.py::TestProtocolVerificationGate::test_valid_transition_chain_is_not_flagged
  - tests/test_gates.py::TestProtocolVerificationGate::test_python_with_block_discharges_the_requirement
  - tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_drop_impl_discharges
  - tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_mem_forget_revokes_the_drop_discharge
  - tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_manually_drop_revokes_the_discharge
  - tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_no_drop_impl_is_not_discharged
  - tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_cpp_raii_destructor_discharges
  - tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_cpp_no_destructor_is_not_discharged
  - tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_python_with_block_discharges
  - tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_python_no_with_block_is_not_discharged
  - tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_typescript_using_discharges
  - tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_typescript_try_finally_discharges
  - tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_typescript_bare_call_is_not_discharged
  - tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_gc_finalizer_never_discharges
threat: null
component: null
---
Child 3 of T-0739. Verification: for every call site of a requires-state function, the caller-context established states (from summaries + entrypoint initial states) must include the required state -- violation is a GATE-TIER ERROR (not advisory; user mandate: enforceable, never fail-silent). A transition function reachable in a state where the transition is undefined = ERROR. The *_init-never-called and *_deinit-orphaned cases fall out: an inferred init protocol whose init is never reachable from any entrypoint while state-requiring functions are = ERROR naming both. LANGUAGE EXCUSES as recorded discharges (T-0383 caught_by doctrine): Rust pairing discharges to Drop UNLESS mem::forget/ManuallyDrop observed on the type (revokes); C++ discharges to RAII only when the init result is observed held by a destructor-bearing class; Python discharges lexically to with-blocks; TS to using/try-finally; GC finalizers NEVER discharge. Every excuse names its mechanism in the finding output; an excuse whose mechanism cannot be observed in code is an ERROR, not a discharge. Unknown/poisoned summaries at a checked call site = ERROR (waivable with reason).