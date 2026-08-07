---
id: T-0739
title: 'typestate protocol enforcement: init/deinit, declared state machines, cleanup-on-all-paths
  (parent)'
state: done
kind: security
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0866
- T-0867
- T-0868
- T-0869
- T-0747
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- src/frob/graph/**
- docs/design/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_declared_protocol_round_trips
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_function_summary_is_its_own_declarations
- tests/test_gates.py::TestProtocolVerificationGate::test_state_never_established_is_an_error
- tests/test_gates.py::TestCleanupObligationGate::test_early_return_before_release_call_is_an_error
designated_repro_test: null
acceptance:
- text: GIVEN the children closed WHEN frob check runs on fixtures for each fragment
    THEN each child gate/advisory fires per its own acceptance
  evidence:
  - tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_declared_protocol_round_trips
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_function_summary_is_its_own_declarations
  - tests/test_gates.py::TestProtocolVerificationGate::test_state_never_established_is_an_error
  - tests/test_gates.py::TestCleanupObligationGate::test_early_return_before_release_call_is_an_error
threat: null
component: null
---
User mandate 2026-07-22: statically enforce system state protocols -- the *_init-never-called / *_deinit-never-called class, and generally functions valid only in particular states (TCP-handshake-style machines), plus cleanup-on-all-paths. Frame: TYPESTATE over the call graph, restricted to two decidable fragments: (a) module/subsystem protocols (the object is a singleton subsystem -- reachability + summaries suffice, no alias analysis); (b) declared object protocols checked at summary granularity. DELIBERATE DECISIONS: declared protocols with name-pattern-inferred init/deinit convenience (inference ONLY for the common pair, never for general machines); per-function summary fixpoint engine shared with the T-0686 may-raise engine (one engine, three clients: exceptions, capabilities, protocols -- no-duplication); language excuses are recorded DISCHARGES naming their mechanism (Rust Drop unless mem::forget observed; C++ RAII only when init result held by destructor-bearing object; Python with-blocks, GC finalizers NEVER count; TS using/try-finally), per T-0383 caught_by doctrine. LIMITS declared: no aliased per-object heap typestate (Rust owns that); concurrent establishment races belong to T-0693 family; dynamic dispatch = Unknown fail-closed (T-0339). Children: declaration surface, summary engine, state-requirement verification + excuses, cleanup obligations. Umbrella closes when children close.