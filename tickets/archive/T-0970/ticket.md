---
id: T-0970
title: 'Burn-down: ARCH001 to zero unwaived + decide on other ARCH categories, promote
  (101 findings)'
state: done
kind: bug
origin: auditor
created: '2026-07-27'
priority: medium
parent: T-0969
tier: ticket
sprint: null
scope:
- src/**
- docs/audits/gates-quality.md
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestLayeringViolations::test_disallowed_cross_layer_edge_flagged
- tests/unit/test_arch.py::TestLayeringViolations::test_allowed_cross_layer_edge_not_flagged
- tests/unit/test_arch.py::TestLayeringViolations::test_dynamic_import_in_layered_file_flagged
- tests/unit/test_arch.py::TestNoDiConstructionSmell::test_inline_construction_outside_init_flagged
- tests/unit/test_arch.py::TestNoDiConstructionSmell::test_construction_inside_init_not_flagged
- tests/unit/test_arch.py::TestNoDiConstructionSmell::test_construction_inside_factory_function_not_flagged
- tests/unit/test_arch.py::TestOverBroadExcept::test_bare_except_flagged
- tests/unit/test_arch.py::TestOverBroadExcept::test_specific_except_not_flagged
- tests/unit/test_arch.py::TestOverBroadExcept::test_reraise_with_different_type_loses_context_flagged
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_mode_calls_stamp_and_returns
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_gate_error_exits_1
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_recursive_cluster_converges_to_hand_computed_fixpoint
designated_repro_test: null
threat: null
component: null
---
gates-quality audit (T-0399) finding 4: only ARCH001 (long-function) is a
real gate Violation; god-class/deep-nesting/high-coupling/large-file/
abstraction-opportunity are computed then discarded (never gated), and
god-class is trivially gameable (only sees top-level classes/direct
methods). Live measured count on main (chunked `gates-native`,
2026-07-27): 101 unwaived ARCH001 warnings (13 already carry a reasoned
frob:waive). Owner-gate: ARCH001 in [gates.severity] (no entry today).

Plan: (a) burn down the 101 ARCH001 findings -- split genuinely long
functions, or add a reasoned `frob:waive ARCH001 reason="..."` for ones
that are long by inherent shape (dispatch tables, generated-style code);
(b) make the deliberate "fresh design decision" the audit calls for on
whether god-class/deep-nesting become real gated Violations too (currently
computed and silently dropped) -- if yes, fix the god-class nested/
function-local-class blind spot (finding 4's evasions) before gating it,
otherwise document the decision to leave them advisory-only in
docs/audits/gates-quality.md. Once ARCH001 is at or near zero unwaived,
flip [gates.severity] ARCH001 = "error" in frob.toml.