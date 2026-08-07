---
id: T-0967
title: test_frob_self_model.py::test_every_claim_proves fails (pre-existing, unrelated
  to T-0961/T-0963)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/system/test_frob_self_model.py
- src/frob/strata/**
- tests/unit/strata/test_export_golden.py
- tests/golden/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_export_golden.py
  reason: 'same T-0864 natives-node drift class: k8s/seccomp/iam golden exports (src/frob/strata/_export.py,
    in-scope) never regenerated after natives node landed, all 3 goldens stale identically
    to the self-model test''s counts'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/golden/**
  reason: 'same T-0864 natives-node drift class: k8s/seccomp/iam golden exports (src/frob/strata/_export.py,
    in-scope) never regenerated after natives node landed, all 3 goldens stale identically
    to the self-model test''s counts'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam
designated_repro_test: null
threat: null
component: null
---
Found while working T-0961/T-0963 (gates/__init__.py and docs/design/registry/check-coverage.yaml drift fixes). tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves fails independently of both those changes -- confirmed failing identically before and after T-0961's diff, and still failing after T-0963's check-coverage.yaml reconciliation (which touched only the registry file, not strata/claims code). Current failure mode: evaluated 27 claim(s): {'proved': 3, 'evidenced': 0, 'assumed': 24, 'refuted': 0} -- most claims sit at 'assumed' rather than 'proved'/'evidenced'. Needs its own triage of why frob's self-model claims aren't proving; out of scope for both T-0961 (src/frob/gates/__init__.py only) and T-0963 (docs/design/registry/check-coverage.yaml only).