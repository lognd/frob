---
id: T-0860
title: 'strata self-conformance + export-golden drift: mutate/deploy capabilities
  undeclared, IAM/k8s/seccomp goldens stale'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/mutate/**
- src/frob/deploy/**
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam
designated_repro_test: null
threat: null
component: null
---
Found while working T-0601 (frob-exports triage, unrelated scope): pytest failures in tests/unit/strata/test_export_golden.py (test_iam, test_k8s, test_seccomp -- IAM/k8s/seccomp export golden files no longer byte-match export_iam/export_k8s_netpol/export_seccomp output for the deploy node) and tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant (SYS100: capability 'env' observed but not declared on node 'mutate', capability 'eval' observed but not declared on node 'deploy'). These are pre-existing on the merged main tip (102688bb) -- neither src/frob/mutate/**, src/frob/deploy/**, design/frob.strata, nor either test file were touched by T-0600 or T-0601's changes, and this drift was discovered only because the targeted verification run for T-0601 happened to include tests/unit/strata/. Needs investigation: either the mutate/deploy code gained an env/eval capability without updating design/frob.strata's declared capabilities, or the golden IAM/k8s/seccomp export fixtures need regenerating against the current design/frob.strata.