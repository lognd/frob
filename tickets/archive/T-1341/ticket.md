---
id: T-1341
title: 'Tier-A auto-fix handler: write the paired suppression in canonical order,
  idempotently'
state: done
kind: feature
origin: human
created: '2026-07-31'
priority: high
parent: T-1339
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- tests/test_gates_fix_engine.py
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: 'COV002/SCOPE001 fallout: TIER_A_HANDLERS drift-lock assertion in tests/test_gates.py
    must enumerate SUPPRESS001 alongside the sibling batch handlers; a broken enumeration
    test on main is worse than a one-line scope extension for the coupled assertion
    T-1341 already had to update.'
  actor: logan
  at: '2026-08-01'
evidence:
- tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression
- tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_idempotent_second_fix_pass_is_a_no_op
- tests/test_gates_fix_engine.py::TestSuppress001NoOpSuppressionRefusal::test_no_op_suppression_never_added_under_tests_glob
- tests/test_gates_fix_engine.py::TestSuppress001FMT001Precedence::test_frob_directive_bearing_line_is_left_untouched
designated_repro_test: null
acceptance:
- text: given a SUPPRESS001 finding, when frob check --fix runs, then the paired suppression
    is appended using the reporting checker's own rule code and the line then passes
    both checkers
  evidence:
  - tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression
- text: given frob check --fix runs twice, when the second run completes, then no
    suppression comment was duplicated or reordered
  evidence:
  - tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_idempotent_second_fix_pass_is_a_no_op
threat: null
component: gates
---
Phase 2 of T-1339, depends on the SUPPRESS001 detector. Add a Tier-A deterministic handler to frob.gates._fix_engine alongside the existing frob:tests/frob:doc/INV006 handlers, so it is picked up by apply_tier_a_fixes and therefore absorbed automatically by frob ticket land (same path frob fmt takes).

Requirements: canonical deterministic comment order on the rewritten line (existing dual-dialect lines in this repo use 'type: ignore[...]  # noqa: ...  # ty: ignore[...]' -- confirm against the 20 already-paired lines and match them rather than inventing an order). Idempotent: both-present is a no-op. Never widen a coded suppression to a bare one. Preserve any trailing explanatory comment. Tier-A means deterministic and verifiable -- if the reporting diagnostic does not carry a rule code, do NOT guess, leave the finding for a human.