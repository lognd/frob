---
id: T-0360
title: 'arch: disposition abstraction-opportunity findings on SRC (dispatch/validator
  families)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- src/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestDispatchFamilySuppression::test_dispatch_family_no_abstraction_opportunity
- tests/unit/test_arch.py::TestDispatchFamilySuppression::test_accidental_same_signature_still_flagged
- tests/unit/test_arch.py::TestDispatchFamilySuppression::test_init_reexport_does_not_suppress
- tests/unit/test_arch.py::TestDispatchFamilySuppression::test_test_file_co_mention_does_not_suppress
designated_repro_test: null
threat: null
component: null
---
T-0204 family 2 (~89 warnings). Many are DELIBERATE sibling families (e.g. N validators (KernelModel) -> Result[None, StrataError] dispatched from one site; N _runner handlers (Path, AppConfig) -> None). Disposition: EITHER teach the detector to recognize an intentional dispatch/validator family (functions with identical signature all registered/called from one dispatch site) as NOT an opportunity, OR per-family reasoned frob:waive with a written why. NO blanket mute -- arch linting must stay nearly impossible to evade. Acceptance: every abstraction-opportunity finding on src/ is either fixed, detector-recognized as an intentional family, or carries a written per-family waiver reason; honest summary line.