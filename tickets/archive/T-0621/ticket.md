---
id: T-0621
title: 'arch: type-driven design checks (ARCH1xx) -- illegal states, primitive obsession,
  parse-dont-validate, boolean flag param'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0330
tier: ticket
sprint: null
scope:
- src/frob/arch/_typedesign.py
- docs/modules/arch.md
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestIllegalStatesRepresentable::test_bool_field_cross_field_guard_flagged
- tests/unit/test_arch.py::TestIllegalStatesRepresentable::test_bool_field_alone_not_flagged
- tests/unit/test_arch.py::TestPrimitiveObsession::test_three_plus_raw_params_flagged
- tests/unit/test_arch.py::TestPrimitiveObsession::test_two_raw_params_not_flagged
- tests/unit/test_arch.py::TestParseDontValidate::test_validates_then_returns_same_type_flagged
- tests/unit/test_arch.py::TestParseDontValidate::test_validates_then_returns_refined_type_not_flagged
- tests/unit/test_arch.py::TestBooleanFlagParam::test_public_function_branching_on_bool_param_flagged
- tests/unit/test_arch.py::TestBooleanFlagParam::test_private_function_not_flagged
- tests/unit/test_arch.py::TestRunTypeDesignChecks::test_combines_all_four_checks
designated_repro_test: null
threat: null
component: null
---
make-illegal-states-unrepresentable: a bool flag field/param whose valid combinations are validated at runtime rather than modeled as an enum/newtype (heuristic: bool field + a validator/assert referencing it + another field it constrains). primitive-obsession: 3+ raw str/int params on one function representing what looks like one domain concept (repeated co-occurrence across call sites). parse-dont-validate: a function that validates its input (raise/assert on shape) then returns the SAME unrefined input type instead of a refined one. boolean/flag parameter: public function with a bool param that switches behavior (branches internally on it) -- split-function candidate. Acceptance: fixture per sub-check; docs updated.