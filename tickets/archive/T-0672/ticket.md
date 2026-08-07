---
id: T-0672
title: 'strata conformance totality: N:M meta-test binding structural-linter-adversarial-hardening.md
  denominator to the five conformance checks (T-0341 close condition)'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0667
- T-0668
- T-0669
- T-0670
- T-0671
- T-0391
parent: T-0341
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- docs/design/registry/arch-checks.yaml
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_every_denominator_id_is_dispositioned
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_every_denominator_id_has_a_real_registry_entry
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_registry_has_no_extra_slh_entries_beyond_denominator
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_arch_checks_gate_reports_zero_unaccounted_slh_entries
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator::test_each_conformance_row_handled_by_its_real_check
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator::test_bound_rules_are_real_known_gate_rules
designated_repro_test: null
acceptance:
- text: Given the structural-linter-adversarial-hardening.md denominator, when the
    meta-test runs, then every SLH-* entry has a disposition (addressed-by-check |
    reasoned-deferral)
  evidence:
  - tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_every_denominator_id_is_dispositioned
- text: Given a new hardening-doc entry with no disposition, when the meta-test runs,
    then it fails the build
  evidence:
  - tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_arch_checks_gate_reports_zero_unaccounted_slh_entries
threat: null
component: null
---
Epic close condition. Binds the structural-linter-adversarial-hardening.md denominator (5 named principles + 9 arch-evasion + 9 strata-evasion rows, registry ids SLH-RULE-*/SLH-ARCH-EVA-*/SLH-SYS-EVA-*, per RECONCILIATION.md finding (a)) to the five conformance checks built above, following the T-0343 drift-lock framework. Depends on all five checks plus T-0391 (arch-checks registry-domain reconciliation, which owns the SLH-* disposition slice).