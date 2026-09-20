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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/**
- src/frob/vet/**
- src/frob/graph/**
- docs/modules/strata.md
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: keep frob:enforces directives, move registry-entry-addition history into
    cited ticket
  actor: logan
  at: '2026-09-19'
  old_length: 440
  new_length: 1664
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
anchor: false
anchor_reason: null
land_commit: null
---
Extend the capability graph (T-0328-resolved) to enumerate every module with an observed capability effect, then cross-check against strata node bindings. A capable-but-unbound module is a hard obligation failure -- this closes acceptance-criterion (1) 'un-modeled modules escape all obligations'. Depends on T-0630 wiring real code binding into production entrypoints so the check has real data to run against, not just unit-test fixtures.

<!-- narrative-moved:src/frob/strata/_selfconform.py:334:T-0667 -->
SYS103 edge added at T-0667's coordinator close-out, once the registry
entry existed and SYS103 registered in the live rule set (the follow-up
T-0667's Done report deferred).
T-1113: CHK-GATE-SYS104/105/106 registry entries added alongside the
SYS104 opt-in-to-mandatory flip, mirroring the CHK-GATE-SYS103
precedent above.
T-1451: CHK-GATE-SYS107 registry entry added alongside the via-less-
may-on-a-large-node advisory (_via_less_large_node_violations below),
mirroring the CHK-GATE-SYS105/106 precedent above.
T-0672: SLH-SYS-EVA-* edges bind this function directly to the
structural-linter-adversarial-hardening.md denominator rows T-0668/
T-0669/T-0670 close (docs/design/registry/arch-checks.yaml's
`handled_by:SYS100`/`SYS105`/`SYS106` dispositions). T-1870: the
CHK-GATE-SYS104 registry entry and the SLH-SYS-EVA-03-UNDECLARED-
PUBLIC-SURFACE `frob:enforces` edge that used to sit here are both
removed -- SYS104 (and its writer) are deleted, per an explicit owner
directive that no code path may auto-update declared public-symbol
surface; SLH-SYS-EVA-03 is re-dispositioned `out_of_scope:reasoned-
deferral` in arch-checks.yaml pending T-1629.