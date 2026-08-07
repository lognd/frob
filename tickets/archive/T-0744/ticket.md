---
id: T-0744
title: 'protocol declarations: frob:protocol/transition/requires + init-deinit name-pattern
  inference'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: high
parent: T-0739
tier: ticket
sprint: null
scope:
- src/frob/graph/dsl.py
- src/frob/graph/_models.py
- docs/modules/gates.md
- tests/unit/graph/test_dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_declared_protocol_round_trips
- tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_protocol_missing_states_is_malformed
- tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_protocol_initial_not_in_states_is_malformed
- tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_protocol_bad_cleanup_is_malformed
- tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_transition_missing_attrs_is_malformed
- tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_requires_missing_state_is_malformed
- tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_unbound_protocol_is_a_loud_error_not_a_skip
- tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_bound_protocol_is_not_flagged_unbound
- tests/unit/graph/test_dsl.py::TestInitDeinitInference::test_init_deinit_pair_infers_a_protocol
- tests/unit/graph/test_dsl.py::TestInitDeinitInference::test_open_close_pair_also_infers
- tests/unit/graph/test_dsl.py::TestInitDeinitInference::test_unpaired_init_infers_nothing
designated_repro_test: null
acceptance:
- text: GIVEN a frob:protocol with transitions and requires bindings WHEN parsed THEN
    the machine round-trips; GIVEN a malformed declaration or an unbound protocol
    THEN a loud ERROR, never a skip
  evidence:
  - tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_declared_protocol_round_trips
  - tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_protocol_missing_states_is_malformed
  - tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_protocol_initial_not_in_states_is_malformed
  - tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_protocol_bad_cleanup_is_malformed
  - tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_transition_missing_attrs_is_malformed
  - tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_requires_missing_state_is_malformed
  - tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_unbound_protocol_is_a_loud_error_not_a_skip
  - tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_bound_protocol_is_not_flagged_unbound
  - tests/unit/graph/test_dsl.py::TestInitDeinitInference::test_init_deinit_pair_infers_a_protocol
  - tests/unit/graph/test_dsl.py::TestInitDeinitInference::test_open_close_pair_also_infers
  - tests/unit/graph/test_dsl.py::TestInitDeinitInference::test_unpaired_init_infers_nothing
threat: null
component: null
---
Child 1 of T-0739. Declaration surface: frob:protocol NAME states=... initial=... (registry-style block or directive), frob:transition proto=NAME from=S to=T on transition functions, frob:requires proto=NAME state=S on state-requiring functions, plus the zero-declaration convenience: name-pattern inference binding X_init/X_deinit (and configurable pairs like open/close, acquire/release) to an implicit 3-state protocol -- inference ONLY for declared name-pair patterns, never for general machines. ENFORCEABILITY (user mandate): a declared protocol consumed by no checker run is itself a DRIFT-class ERROR (the catalogued-is-not-enforced doctrine applied to protocols); parse errors in protocol declarations are ERRORS, never skipped; the declaration registry lists every protocol with its binding counts so an unbound protocol (zero transition/requires bindings) fails loudly.