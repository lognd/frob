---
id: T-0440
title: 'strata model debt: deploy/serve/mutate swept into coarse utility-hub node,
  not modeled as distinct capabilities with own effects/threat surface'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
- docs/strata/
- tests/system/test_frob_self_model.py
- tests/unit/strata/test_effects.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'T-0440 tests/** is chronically over-broad per doable''s flag. Narrowing
    to

    the specific strata self-model + capability-conformance test files this

    node-split ticket actually touches: tests/system/test_frob_self_model.py

    (node/flow/claim counts + frob:tests directives for new flows) and

    tests/unit/strata/test_effects.py (capability-conformance coverage for

    the new deploy/serve/mutate nodes), rather than holding a lease across

    the entire tests/ tree.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/system/test_frob_self_model.py
  reason: 'T-0440 tests/** is chronically over-broad per doable''s flag. Narrowing
    to

    the specific strata self-model + capability-conformance test files this

    node-split ticket actually touches: tests/system/test_frob_self_model.py

    (node/flow/claim counts + frob:tests directives for new flows) and

    tests/unit/strata/test_effects.py (capability-conformance coverage for

    the new deploy/serve/mutate nodes), rather than holding a lease across

    the entire tests/ tree.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: 'T-0440 tests/** is chronically over-broad per doable''s flag. Narrowing
    to

    the specific strata self-model + capability-conformance test files this

    node-split ticket actually touches: tests/system/test_frob_self_model.py

    (node/flow/claim counts + frob:tests directives for new flows) and

    tests/unit/strata/test_effects.py (capability-conformance coverage for

    the new deploy/serve/mutate nodes), rather than holding a lease across

    the entire tests/ tree.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
- tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_deploy_declares_every_real_effect_it_exercises
- tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_mutate_declares_every_real_effect_it_exercises
- tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects
designated_repro_test: null
threat: null
component: null
---
