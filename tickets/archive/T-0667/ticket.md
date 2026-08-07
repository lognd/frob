---
id: T-0667
title: 'strata: SYS-COV coverage-totality check - every capable module binds to a
  modeled node'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0630
parent: T-0341
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/vet/**
- src/frob/graph/**
- docs/modules/strata.md
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_bound_file_discharges_sys103
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_capability_free_file_does_not_fire_sys103
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_fires_outside_src_frob_layout
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_sys103_waivable_as_bare_rule
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
designated_repro_test: null
acceptance:
- text: Given a module with an observed capability effect and no strata node binding,
    when checked, then SYS-COV fires
  evidence:
  - tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103
- text: Given every module bound to a node, when checked, then SYS-COV is silent
  evidence:
  - tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_bound_file_discharges_sys103
threat: null
component: null
---
Extend the capability graph (T-0328-resolved) to enumerate every module with an observed capability effect, then cross-check against strata node bindings. A capable-but-unbound module is a hard obligation failure -- this closes acceptance-criterion (1) 'un-modeled modules escape all obligations'. Depends on T-0630 wiring real code binding into production entrypoints so the check has real data to run against, not just unit-test fixtures.