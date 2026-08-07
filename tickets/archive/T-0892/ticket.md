---
id: T-0892
title: 'arch: fold TypeDesignCategory into ArchCategory once _models.py lease is free
  (T-0621 follow-up)'
state: done
kind: feature
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/_typedesign.py
- src/frob/arch/_models.py
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
T-0621 (arch: type-driven design checks) implemented its four checks
(illegal-states-representable, primitive-obsession, parse-dont-validate,
boolean-flag-param) against a LOCAL TypeDesignCategory/TypeDesignSuggestion
pair in src/frob/arch/_typedesign.py rather than the shared
frob.arch._models.ArchCategory/ArchSuggestion, because at implementation
time T-0620 (a sibling ticket in the same ARCH1xx cluster) held an active
scope lease on src/frob/arch/_models.py and `frob ticket scope --add`
refused with ScopeLeaseConflict.

Once T-0620 is closed/landed and the lease is free: fold the four
TypeDesignCategory string values into ArchCategory, migrate
TypeDesignSuggestion's four producer functions in _typedesign.py to build
frob.arch._models.ArchSuggestion instead of the local model, and delete
TypeDesignCategory/TypeDesignSuggestion. Purely mechanical -- the four
check functions' logic does not change, only which model they construct.