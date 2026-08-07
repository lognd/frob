---
id: T-0618
title: 'arch: LSP checks (ARCH1xx) -- override contract violations'
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
- src/frob/arch/_solid.py
- src/frob/arch/_models.py
- docs/modules/arch.md
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestOverrideRaisesNotImplemented::test_concrete_override_raising_not_implemented_flagged
- tests/unit/test_arch.py::TestOverrideRaisesNotImplemented::test_base_itself_raising_not_implemented_is_not_flagged
- tests/unit/test_arch.py::TestOverrideSignatureVariance::test_narrower_required_params_flagged
- tests/unit/test_arch.py::TestOverrideSignatureVariance::test_wider_return_type_flagged
- tests/unit/test_arch.py::TestOverrideSignatureVariance::test_same_shape_signature_not_flagged
- tests/unit/test_arch.py::TestOverrideStrengthenedPrecondition::test_added_guard_raise_on_shared_param_flagged
- tests/unit/test_arch.py::TestOverrideStrengthenedPrecondition::test_guard_raise_present_in_base_too_not_flagged
- tests/unit/test_arch.py::TestOverrideWeakenedPostcondition::test_bare_return_where_base_always_returns_value_flagged
- tests/unit/test_arch.py::TestOverrideWeakenedPostcondition::test_override_also_always_returning_value_not_flagged
- tests/unit/test_arch.py::TestNoOpOverride::test_empty_body_override_of_value_returning_base_flagged
- tests/unit/test_arch.py::TestNoOpOverride::test_override_with_real_body_not_flagged
- tests/unit/test_arch.py::TestRunLspChecks::test_combines_multiple_checks
designated_repro_test: null
threat: null
component: null
---
Override checks against a base/interface method: (1) raises NotImplementedError in a supposedly-concrete override; (2) incompatible signature (narrower accepted params, or wider/different return than base -- variance violation); (3) strengthened precondition (override adds an assert/raise the base lacks on the same param); (4) weakened postcondition; (5) no-op override of a value-returning base method (bare pass/return None where base returns a value). Needs override-resolution over the normalized model (base<->override linkage). Acceptance: one fixture per sub-check; docs updated.