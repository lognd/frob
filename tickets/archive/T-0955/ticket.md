---
id: T-0955
title: 'strata export golden: frob_export_seccomp/iam/k8s drifted re: natives node'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/strata/test_export_golden.py
- docs/strata/**
- tests/system/test_frob_self_model.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/system/test_frob_self_model.py
  reason: 'same root cause: frob''s own strata design gained a node (natives) node/flow/claim
    count that this drift-lock test''s hardcoded assertions (and the export goldens)
    were never updated for'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/system/test_frob_self_model.py
  reason: already added
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
designated_repro_test: null
threat: null
component: null
---
Found while working T-0700 (unrelated to grammar/access-mode changes -- confirmed via `git status`, no golden/export files touched by that ticket). `tests/unit/strata/test_export_golden.py::TestExportGolden` (test_k8s, test_seccomp, test_iam) fails on a fresh worktree built from current main: the frob self-modeled design's exported seccomp/IAM/netpol JSON now includes a "natives" node's syscalls/statements that the checked-in golden fixtures under the golden dir do not yet reflect. Likely a golden-fixture regen missed after a recent "natives" node/capability addition to frob's own strata design. Regenerate the golden fixtures (or fix the export drift if the new output is wrong) and re-verify test_export_golden passes clean.